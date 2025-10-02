# pars.py
import re
import json
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- КОНФІГУРАЦІЯ СЕЛЕКТОРІВ ---
MAIN_INFO_BLOCK_SELECTOR = "div[data-qaid='main_product_info']"
PRICE_SELECTOR = "div[data-qaid='product_price']"
STATUS_SELECTOR = "span[data-qaid='product_presence']"
ORDER_COUNTER_SELECTOR = "span[data-qaid='order_counter']"
RATING_SELECTOR = "div[data-qaid='product_rating']"
PAGE_NOT_FOUND_SELECTOR = "span[data-qaid='page_not_found_title']"
DELETED_WARNING_PANEL_SELECTOR = "div[data-qaid='warning_panel']"

# --- СЛОВНИК СТАТУСІВ ---
STATUS_MAP = {
    "Недоступний": 0,
    "Недоступен": 0,
    "В наявності": 1,
    "В наличии": 1,
    "Готово до відправки": 2,
    "Готово к отправке": 2,
    "Під замовлення": 3,
    "Под заказ": 3,
}


def _extract_number(text: str) -> int | None:
    """Допоміжна функція для витягання першого числа з тексту."""
    if not text:
        return None
    match = re.search(r"(\d+)", str(text))
    return int(match.group(1)) if match else None


def parse_product_data(products_to_scrape: list, headless_mode: bool = True) -> str:
    """
    Автономний модуль парсингу.
    Приймає список товарів, обробляє їх і повертає результат у форматі JSON.
    """
    scraped_data = []
    driver = None

    try:
        # --- Налаштування та запуск Selenium (undetected-chromedriver) ---
        options = uc.ChromeOptions()
        options.add_argument("--headless")

        options.add_argument("--window-size=1920,1080")
        options.add_argument("--no-sandbox")

        driver = uc.Chrome(options=options)

        # --- Основний цикл обробки товарів ---
        for product in products_to_scrape:
            product_id = product.get("product_id")
            product_url = product.get("url")

            if not all([product_id, product_url]):
                continue

            driver.get(product_url)

            daily_data = {
                "product_id": product_id,
                "status_id": None,
                "price": None,
                "order_quantity": None,
                "rating": None,
            }

            try:
                driver.find_element(By.CSS_SELECTOR, DELETED_WARNING_PANEL_SELECTOR)
                daily_data["status_id"] = 4
                scraped_data.append(daily_data)
                continue
            except NoSuchElementException:
                pass

            try:
                wait = WebDriverWait(driver, 5)
                status_element = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, STATUS_SELECTOR))
                )
                status_text = status_element.text.lower()
                for text_key, status_id in STATUS_MAP.items():
                    if text_key in status_text:
                        daily_data["status_id"] = status_id
                        break
            except TimeoutException:
                try:
                    driver.find_element(By.CSS_SELECTOR, PAGE_NOT_FOUND_SELECTOR)
                    daily_data["status_id"] = 0
                except NoSuchElementException:
                    pass

            try:
                main_info_block = driver.find_element(
                    By.CSS_SELECTOR, MAIN_INFO_BLOCK_SELECTOR
                )
                try:
                    price_element = main_info_block.find_element(
                        By.CSS_SELECTOR, PRICE_SELECTOR
                    )
                    daily_data["price"] = float(
                        price_element.get_attribute("data-qaprice")
                    )
                except (NoSuchElementException, TypeError, ValueError):
                    pass

                try:
                    orders_text = main_info_block.find_element(
                        By.CSS_SELECTOR, ORDER_COUNTER_SELECTOR
                    ).text
                    daily_data["order_quantity"] = _extract_number(orders_text)
                except NoSuchElementException:
                    pass
            except NoSuchElementException:
                pass

            try:
                rating_element = driver.find_element(By.CSS_SELECTOR, RATING_SELECTOR)
                daily_data["rating"] = float(
                    rating_element.get_attribute("data-qarating")
                )
            except (NoSuchElementException, TypeError, ValueError):
                pass

            if daily_data.get("status_id") is None:
                daily_data["status_id"] = 5

            scraped_data.append(daily_data)
            time.sleep(1)  # Пауза в 1 секунду між запитами

        # Якщо цикл завершився без помилок, готуємо успішну відповідь
        success_result = {"status": "success", "data": scraped_data}
        return json.dumps(success_result, indent=4, ensure_ascii=False)

    except Exception as e:
        # У разі будь-якої критичної помилки, формуємо відповідь про помилку
        error_result = {
            "status": "error",
            "message": f"🔥 Критична помилка під час роботи парсера: {str(e)}",
        }
        return json.dumps(error_result, indent=4, ensure_ascii=False)

    finally:
        # Блок finally виконається в будь-якому випадку для закриття драйвера
        if driver:
            driver.quit()
