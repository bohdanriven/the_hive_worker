import time
import uuid

def prom_parser_task(url: str, retries: int = 3):
    """
    Приклад функції парсера. Імітує роботу 10 секунд і повертає
    список з 10 тестових товарів.
    """
    print(f"[TASK:prom_parser] Починаю імітацію парсингу {url}...")
    time.sleep(10)  # Імітація довгої роботи

    # Створюємо тестові дані
    test_items = []
    for i in range(1, 11):
        item = {
            "id": str(uuid.uuid4()),
            "name": f"Тестовий Товар #{i}",
            "price": 1000 + (i * 50),
            "currency": "UAH",
            "url": f"{url}/product/{i}"
        }
        test_items.append(item)

    print(f"[TASK:prom_parser] ✅ Імітація завершена, знайдено {len(test_items)} товарів.")

    # Повертаємо результат у форматі, який очікує серверний обробник
    return {
        "status": "parsed",
        "source_url": url,
        "items_found": len(test_items),
        "items": test_items
    }