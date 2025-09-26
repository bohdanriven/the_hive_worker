import sys

def system_info_task():
    """Приклад простого завдання без параметрів."""
    print("[TASK:system_info] Збираю інформацію про систему...")
    return {
        "platform": sys.platform,
        "python_version": sys.version
    }
