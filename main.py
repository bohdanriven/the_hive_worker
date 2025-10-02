import requests
import time
import uuid
import subprocess
import os
import sys
import zipfile
import shutil

from config import (
    WORKER_VERSION,
    SERVER_URL,
    NO_TASK_SLEEP,
    TIME_ERROR_SLEEP,
    TASK_REGISTRY,
    UPDATE_FAIL_SLEEP,
)


def get_or_create_worker_id(config_file="worker.conf"):
    """
    Перевіряє наявність ID у файлі конфігурації.
    Якщо файл існує - читає ID з нього.
    Якщо ні - генерує новий ID і зберігає у файл.
    """
    # Визначаємо шлях до файлу поруч з .exe
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_path, config_file)

    try:
        # Спроба прочитати існуючий ID
        with open(config_path, "r") as f:
            worker_id = f.read().strip()
            if worker_id:
                return worker_id
    except FileNotFoundError:
        # Якщо файл не знайдено, генеруємо новий ID
        new_worker_id = (
            f"worker_{uuid.uuid4().hex[:8]}"  # Зробимо ID трохи довшим для унікальності
        )

        # Зберігаємо новий ID у файл
        with open(config_path, "w") as f:
            f.write(new_worker_id)

        return new_worker_id


def execute_regular_task(task_name: str, params: dict) -> tuple[bool, any]:
    """Функція викликає функцію з реєстру завдань і повертає результат."""
    try:
        if task_name not in TASK_REGISTRY:
            raise ValueError(f"Завдання '{task_name}' не знайдено в реєстрі.")
        result = TASK_REGISTRY[task_name](**params)
        return True, result
    except Exception as e:
        print(f"[ERROR] Помилка під час виконання завдання '{task_name}': {e}")
        return False, {"error": str(e)}


def handle_update(params: dict) -> bool:
    """
    Обробляє завдання на оновлення, завантажуючи та розпаковуючи архів
    в поточній папці воркера, щоб уникнути конфліктів з антивірусом.
    """
    # Визначаємо шлях до папки, де запущено .exe файл
    exe_dir = os.path.dirname(sys.executable)

    # Визначаємо шляхи для архіву та папки розпаковки всередині директорії воркера
    zip_path = os.path.join(exe_dir, "update.zip")
    extract_dir = os.path.join(exe_dir, "update_temp")

    try:
        url = params.get("url")
        if not url:
            raise ValueError("URL для оновлення не надано.")

        print(f"[UPDATE] Завантажую архів в {zip_path}...")
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        if not os.path.exists(extract_dir):
            os.makedirs(extract_dir)

        print(f"[UPDATE] Розпаковую архів в {extract_dir}...")
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        new_worker_path = os.path.join(extract_dir, "worker.exe")
        if not os.path.exists(new_worker_path):
            raise FileNotFoundError("worker.exe не знайдено в архіві.")

        current_exe = sys.executable
        update_exe_dest = current_exe.replace(".exe", "_update.exe")
        updater_bat = os.path.join(exe_dir, "updater.bat")

        if not os.path.exists(updater_bat):
            raise FileNotFoundError(f"Скрипт оновлення {updater_bat} не знайдено!")

        shutil.move(new_worker_path, update_exe_dest)

        print("[UPDATE] Запускаю лаунчер оновлень і завершую роботу...")
        subprocess.Popen(
            [updater_bat, current_exe, update_exe_dest],
            # creationflags=subprocess.DETACHED_PROCESS,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        sys.exit(0)
    except Exception as e:
        print(f"[UPDATE_ERROR] Не вдалося виконати оновлення: {e}")
        return False
    finally:
        # Прибираємо за собою тимчасові файли (архів та папку)
        print("[UPDATE] Очищення тимчасових файлів...")
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir, ignore_errors=True)


def main_loop():
    """Головний цикл роботи воркера."""
    # Очищення сміття (старого воркера)
    current_exe = sys.executable
    old_update_file = current_exe.replace(".exe", "_update.exe")
    if os.path.exists(old_update_file):
        try:
            os.remove(old_update_file)
        except OSError as e:
            print(f"[CLEANUP_ERROR] Не вдалося видалити старий файл: {e}")

    WORKER_ID = get_or_create_worker_id()
    HEADERS = {"X-Worker-ID": WORKER_ID, "X-Worker-Version": WORKER_VERSION}

    session = requests.Session()
    session.headers.update(HEADERS)

    print(f"--- Worker {WORKER_ID} | Version {WORKER_VERSION} | Started ---")
    print(f"Connecting to server: {SERVER_URL}")

    while True:
        try:
            response = session.get(f"{SERVER_URL}/get_task", timeout=10)
            response.raise_for_status()
            task = response.json()

            if task.get("status") == "no_tasks":
                time.sleep(NO_TASK_SLEEP)
                continue

            task_type = task.get("task_type")
            params = task.get("params", {})
            print(f"--> Отримано завдання '{task_type}' (ID: {task.get('id')})")

            if task_type == "update_worker":
                update_successful = handle_update(params)

                if not update_successful:
                    print(
                        f"[MAIN] Помилка оновлення. Таймаут на {UPDATE_FAIL_SLEEP} секунд..."
                    )
                    time.sleep(UPDATE_FAIL_SLEEP)

                continue

            is_successful, result_data = execute_regular_task(task_type, params)
            status = "success" if is_successful else "failure"

            result_payload = {
                "task_id": task["id"],
                "worker_id": WORKER_ID,
                "status": status,
                "result": result_data,
            }
            session.post(
                f"{SERVER_URL}/submit_result", json=result_payload, timeout=60
            ).raise_for_status()
            print(f"Результат завдання '{task_type}' надіслано зі статусом: {status}")

        except requests.exceptions.RequestException as e:
            print(
                f"[ERROR] Помилка з'єднання з сервером: {e}. Повторна спроба через {TIME_ERROR_SLEEP}с..."
            )
            time.sleep(TIME_ERROR_SLEEP)
        except Exception as e:
            print(
                f"[CRITICAL_ERROR] Неочікувана помилка в головному циклі: {e}. Перезапуск через {TIME_ERROR_SLEEP}с..."
            )
            time.sleep(TIME_ERROR_SLEEP)


if __name__ == "__main__":
    main_loop()
