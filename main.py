import requests
import time
import uuid
import subprocess
import os
import sys
import zipfile
import shutil
from typing import NoReturn

from config import (
    WORKER_VERSION,
    SERVER_URL,
    NO_TASK_SLEEP,
    TIME_ERROR_SLEEP,
    TASK_ERROR_SLEEP,
    TASK_REGISTRY,
    UPDATE_ERROR_SLEEP,
)


def handle_update(params: dict) -> NoReturn:
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

        # Завантаження архіву на пк
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Розпаковка архіву в тимчасову папку
        if not os.path.exists(extract_dir):
            os.makedirs(extract_dir)
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        # Перевірка чи в архіві є файл worker.exe
        new_worker_path = os.path.join(extract_dir, "worker.exe")
        if not os.path.exists(new_worker_path):
            raise FileNotFoundError("worker.exe не знайдено в архіві.")

        # Перевірка чи в поточній директорії є файл updater.bat
        updater_bat = os.path.join(exe_dir, "updater.bat")
        if not os.path.exists(updater_bat):
            raise FileNotFoundError(f"Скрипт оновлення {updater_bat} не знайдено!")

        # Переміщення worker.exe з архів в поточну директорію з приставкою _update
        current_exe = sys.executable
        update_exe_dest = current_exe.replace(".exe", "_update.exe")
        shutil.move(new_worker_path, update_exe_dest)

        # Запуск скрипту оновлення і закриття поточного процесу
        subprocess.Popen(
            [updater_bat, current_exe, update_exe_dest],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        sys.exit(0)
    except Exception as e:
        raise RuntimeError(f"Помилка під час оновлення воркера: {e}")
    finally:
        # Прибираємо за собою тимчасові файли (архів та папку)
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir, ignore_errors=True)


def execute_regular_task(task_name: str, params: dict) -> list:
    """Функція викликає функцію з реєстру завдань і повертає результат."""
    try:
        if task_name not in TASK_REGISTRY:
            raise ValueError(f"Завдання '{task_name}' не знайдено в реєстрі.")

        # Викликаємо таску, яка має повернути словник Python
        data = TASK_REGISTRY[task_name](**params)

        # Перевіряємо статус всередині об'єкта
        if isinstance(data, dict) and data.get("status") == "success":
            return data.get("data", [])
        else:
            raise RuntimeError(
                f"Завдання '{task_name}' повернуло помилку: {data.get("message", str(data))}"
            )

    except Exception as e:
        raise RuntimeError(f"Критична помилка під час виконання '{task_name}': {e}")


def _get_id_prefix(nickname_path: str, default: str = "worker") -> str:
    """Безпечно читає префікс з файлу, інакше повертає стандартний."""
    try:
        if os.path.exists(nickname_path):
            with open(nickname_path, "r", encoding="utf-8") as f:
                custom_prefix = f.read().strip()
                if custom_prefix:
                    return custom_prefix
    except IOError:
        pass  # У випадку помилки просто повернемо стандартний префікс
    return default


def get_or_create_worker_id(
    config_file="worker.conf", nickname_file="workername.txt"
) -> str:
    """
    Перевіряє наявність ID у файлі конфігурації.
    Якщо файл існує - читає ID з нього.
    Якщо ні - генерує новий ID і зберігає у файл.
    """
    # Визначаємо шлях до файлу поруч з .exe
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_path, config_file)
    nickname_path = os.path.join(base_path, nickname_file)

    # Спроба прочитати існуючий ID
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                worker_id = f.read().strip()
                if worker_id:
                    return worker_id
        except IOError as e:
            pass

    # Якщо файл не знайдено, генеруємо новий ID
    try:
        prefix = _get_id_prefix(nickname_path)
        new_worker_id = f"{prefix}_{uuid.uuid4().hex[:8]}"

        # Виконуємо атомарний запис
        temp_path = config_path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(new_worker_id)

        os.replace(temp_path, config_path)
        return new_worker_id

    except IOError as e:
        raise RuntimeError(f"ID воркера не отримано: {e}")


def _cleanup_old_update():
    """
    Перевіряє наявність старого файлу оновлення (_update.exe)
    і видаляє його, якщо він існує.
    """
    try:
        current_exe = sys.executable
        old_update_file = current_exe.replace(".exe", "_update.exe")

        if os.path.exists(old_update_file):
            os.remove(old_update_file)
    except Exception as e:
        pass


def main_loop():
    """Головний цикл роботи воркера."""
    # Прибираємо за собою стариий файл оновлення
    _cleanup_old_update()

    # Отримуємо ID воркера
    try:
        WORKER_ID = get_or_create_worker_id()
    except Exception as e:
        sys.exit(1)

    # Налаштовуємо підключення до сервера
    HEADERS = {"X-Worker-ID": WORKER_ID, "X-Worker-Version": WORKER_VERSION}
    session = requests.Session()
    session.headers.update(HEADERS)

    print(f"--- Worker {WORKER_ID} | Version {WORKER_VERSION} | Started ---")
    print(f"Connecting to server: {SERVER_URL}")

    while True:
        task = None
        try:
            # Отримуємо завдання від сервера
            response = session.get(f"{SERVER_URL}/get_task", timeout=20)
            response.raise_for_status()
            task = response.json()

            # Якщо задач немає, чекаємо поки з'являться
            if task.get("status") == "no_tasks":
                time.sleep(NO_TASK_SLEEP)
                continue

            # Виконуємо завдання
            task_id = task.get("id")
            task_type = task.get("task_type")
            params = task.get("params", {})
            print(f"--> Отримано завдання '{task_type}' (ID: {task_id})")

            # Обробка завдання в залежності від типу
            if task_type == "update_worker":
                try:
                    handle_update(params)

                except Exception as e:
                    # Якщо сталася помилка, надсилаємо повідомлення про помилку на сервер
                    failure_payload = {
                        "task_id": task_id,
                        "worker_id": WORKER_ID,
                        "status": "failure",
                        "result": {"error": str(e)},
                    }
                    session.post(
                        f"{SERVER_URL}/submit_result", json=failure_payload, timeout=60
                    )
                    # А воркер переходить в сон
                    time.sleep(UPDATE_ERROR_SLEEP)

            else:
                result_data, status = None, "failure"
                try:
                    # Викликаємо функцію для виконання завдання
                    result_data = execute_regular_task(task_type, params)
                    status = "success"

                except Exception as e:
                    # Якщо сталася помилка, формуємо повідомлення про помилку для серверу
                    result_data = {"error": str(e)}
                    status = "failure"

                # Відправляємо результат (успішний або звіт про помилку)
                result_payload = {
                    "task_id": task_id,
                    "worker_id": WORKER_ID,
                    "status": status,
                    "result": result_data,
                }
                session.post(
                    f"{SERVER_URL}/submit_result", json=result_payload, timeout=60
                ).raise_for_status()

                # Якщо завдання провалено, воркер переходить в сон
                if status == "failure":
                    time.sleep(TASK_ERROR_SLEEP)

        # Якщо сталася помилка при зєднанні з сервером, воркер переходить в короткий сон
        except requests.exceptions.RequestException as e:
            time.sleep(TIME_ERROR_SLEEP)
        # Якщо сталася невідома помилка, воркер переходить в короткий сон
        except Exception as e:
            time.sleep(TIME_ERROR_SLEEP)


if __name__ == "__main__":
    main_loop()
