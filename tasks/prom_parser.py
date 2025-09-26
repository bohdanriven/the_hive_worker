import time

def prom_parser_task(url: str, retries: int = 3):
    """
    Приклад функції парсера. Приймає параметри з сервера.
    Повертає словник, який буде відправлено як результат.
    """
    print(f"[TASK:prom_parser] Починаю парсинг {url} з {retries} спробами...")
    time.sleep(5)  # Імітація довгої роботи
    # Успішний результат
    return {"status": "parsed", "url": url, "items_found": 123}
