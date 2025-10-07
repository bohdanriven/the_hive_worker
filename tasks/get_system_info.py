import platform
import socket
import time
import json

def get_system_info_task() -> str:
    """
    Збирає базову інформацію про систему...
    Повертає результат у вигляді JSON-РЯДКА.
    """
    time.sleep(60)

    try:
        info = {
            "computer_name": socket.gethostname(),
            "os": f"{platform.system()} {platform.release()}",
            "os_version": platform.version(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        }

        # Готуємо успішну відповідь у вигляді словника
        success_result = {"status": "success", "data": info}
        return json.dumps(success_result, indent=4, ensure_ascii=False)

    except Exception as e:
        # Формуємо відповідь про помилку у вигляді словника
        error_result = {
            "status": "error",
            "message": f"Помилка при зборі інформації про систему: {str(e)}",
        }
        return json.dumps(error_result, indent=4, ensure_ascii=False)