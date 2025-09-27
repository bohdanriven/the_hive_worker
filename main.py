import requests
import time
import uuid
import subprocess
import os
import sys
import zipfile
import shutil
import tempfile

# --- ІМПОРТУЄМО НАШІ ЗАВДАННЯ З ПАПКИ TASKS ---
from tasks.prom_parser import prom_parser_task
from tasks.system_info import system_info_task

# --- Конфігурація ---
SERVER_URL = "http://127.0.0.1:3010"
NO_TASK_SLEEP = 60  # Час очікування, якщо немає завдань (секунди)
TIME_ERROR_SLEEP = 60  # Час очікування при помилці з'єднання (секунди)

# --- РЕЄСТР ЗАВДАНЬ ---
TASK_REGISTRY = {
    "prom_pars": prom_parser_task,
    "get_sys_info": system_info_task,
}


def get_worker_version():
    """Функція читає версію з файлу version.txt."""
    try:
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        version_file = os.path.join(base_path, "version.txt")
        with open(version_file, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "0.0.0"


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


def handle_update(params: dict):
    """Обробляє завдання на оновлення, завантажуючи та розпаковуючи .zip архів."""
    temp_dir = None
    try:
        url = params.get("url")
        if not url:
            raise ValueError("URL для оновлення не надано.")

        temp_dir = tempfile.mkdtemp(prefix="worker_update_")
        zip_path = os.path.join(temp_dir, "update.zip")
        print(f"[UPDATE] Завантажую архів в {zip_path}...")

        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"[UPDATE] Розпаковую архів...")
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        new_worker_path = os.path.join(temp_dir, "worker.exe")
        if not os.path.exists(new_worker_path):
            raise FileNotFoundError("worker.exe не знайдено в архіві.")

        current_exe = sys.executable
        base_dir = os.path.dirname(current_exe)
        update_exe_dest = current_exe.replace(".exe", "_update.exe")
        updater_bat = os.path.join(base_dir, "updater.bat")

        if not os.path.exists(updater_bat):
            raise FileNotFoundError(f"Скрипт оновлення {updater_bat} не знайдено!")

        shutil.move(new_worker_path, update_exe_dest)

        print("[UPDATE] Запускаю лаунчер оновлень і завершую роботу...")
        subprocess.Popen(
            [updater_bat, current_exe, update_exe_dest],
            creationflags=subprocess.DETACHED_PROCESS,
        )
        sys.exit(0)
    except Exception as e:
        print(f"[UPDATE_ERROR] Не вдалося виконати оновлення: {e}")
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


# --- Головний цикл ---
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

    WORKER_ID = f"worker_{uuid.uuid4().hex[:6]}"
    WORKER_VERSION = get_worker_version()
    HEADERS = {"X-Worker-ID": WORKER_ID, "X-Worker-Version": WORKER_VERSION}

    print(f"--- Worker {WORKER_ID} | Version {WORKER_VERSION} | Started ---")
    print(f"Connecting to server: {SERVER_URL}")

    while True:
        try:
            response = requests.get(
                f"{SERVER_URL}/get_task", headers=HEADERS, timeout=10
            )
            response.raise_for_status()
            task = response.json()

            if task.get("status") == "no_tasks":
                time.sleep(NO_TASK_SLEEP)
                continue

            task_type = task.get("task_type")
            params = task.get("params", {})
            print(f"--> Отримано завдання '{task_type}' (ID: {task.get('id')})")

            if task_type == "update_worker":
                handle_update(params)
                continue

            is_successful, result_data = execute_regular_task(task_type, params)
            status = "success" if is_successful else "failure"

            result_payload = {
                "task_id": task["id"],
                "worker_id": WORKER_ID,
                "status": status,
                "result": result_data,
            }
            requests.post(
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
