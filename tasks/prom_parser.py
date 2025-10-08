import re
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager

# --- Селектори ---
MAIN_INFO_BLOCK_SELECTOR = "div[data-qaid='main_product_info']"
PRICE_SELECTOR = "div[data-qaid='product_price']"
STATUS_SELECTOR = "span[data-qaid='product_presence']"
ORDER_COUNTER_SELECTOR = "span[data-qaid='order_counter']"
RATING_SELECTOR = "div[data-qaid='product_rating']"
PAGE_NOT_FOUND_SELECTOR = "span[data-qaid='page_not_found_title']"
DELETED_WARNING_PANEL_SELECTOR = "div[data-qaid='warning_panel']"

# --- Статуси ---
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
    """Витягує перше число з тексту."""
    if not text:
        return None
    match = re.search(r"(\d+)", str(text))
    return int(match.group(1)) if match else None


def _create_browser():
    """Створює та налаштовує екземпляр браузера Firefox в headless-режимі."""
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    options.add_argument("--width=1920")
    options.add_argument("--height=1080")

    # Налаштування для маскування від антибот-систем
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference("useAutomationExtension", False)

    try:
        service = FirefoxService(executable_path=GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=options)
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
    except Exception as e:
        raise RuntimeError(f"Не вдалося створити екземпляр Firefox драйвера: {e}")

    driver.set_page_load_timeout(300)
    return driver


def parse_product_data(products_to_scrape: list) -> str:
    """
    Основна функція парсингу.
    Приймає список товарів, обробляє їх і повертає результат у форматі JSON.
    """
    scraped_data = []
    driver = None
    try:
        driver = _create_browser()

        for product in products_to_scrape:
            product_id = product.get("product_id")
            product_url = product.get("url")
            if not all([product_id, product_url]):
                continue

            daily_data = {
                "product_id": product_id,
                "status_id": None,
                "price": None,
                "order_quantity": None,
                "rating": None,
            }

            for attempt in range(2):  # Цикл з 2 спробами
                try:
                    driver.get(product_url)
                    # --- Логіка збору даних ---
                    try:
                        driver.find_element(
                            By.CSS_SELECTOR, DELETED_WARNING_PANEL_SELECTOR
                        )
                        daily_data["status_id"] = 4
                        break
                    except NoSuchElementException:
                        pass
                    try:
                        wait = WebDriverWait(driver, 5)
                        status_text = wait.until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, STATUS_SELECTOR)
                            )
                        ).text
                        for text_key, status_id in STATUS_MAP.items():
                            if text_key in status_text:
                                daily_data["status_id"] = status_id
                                break
                    except TimeoutException:
                        try:
                            driver.find_element(
                                By.CSS_SELECTOR, PAGE_NOT_FOUND_SELECTOR
                            )
                            daily_data["status_id"] = 0
                        except NoSuchElementException:
                            pass
                    try:
                        main_block = driver.find_element(
                            By.CSS_SELECTOR, MAIN_INFO_BLOCK_SELECTOR
                        )
                        try:
                            price_attr = main_block.find_element(
                                By.CSS_SELECTOR, PRICE_SELECTOR
                            ).get_attribute("data-qaprice")
                            daily_data["price"] = float(price_attr)
                        except (NoSuchElementException, TypeError, ValueError):
                            pass
                        try:
                            orders_text = main_block.find_element(
                                By.CSS_SELECTOR, ORDER_COUNTER_SELECTOR
                            ).text
                            daily_data["order_quantity"] = _extract_number(orders_text)
                        except NoSuchElementException:
                            pass
                    except NoSuchElementException:
                        pass
                    try:
                        rating_attr = driver.find_element(
                            By.CSS_SELECTOR, RATING_SELECTOR
                        ).get_attribute("data-qarating")
                        daily_data["rating"] = float(rating_attr)
                    except (NoSuchElementException, TypeError, ValueError):
                        pass

                    break  # Вихід з циклу спроб у разі успіху
                except Exception:
                    if (
                        attempt == 0
                    ):  # Якщо перша спроба невдала, перезапускаємо браузер
                        if driver:
                            driver.quit()
                        driver = _create_browser()

            if daily_data.get("status_id") is None:
                daily_data["status_id"] = 5  # Статус "Не вдалося визначити"

            scraped_data.append(daily_data)
            time.sleep(1)

        return json.dumps(
            {"status": "success", "data": scraped_data}, ensure_ascii=False
        )
    except Exception as e:
        return json.dumps(
            {"status": "error", "message": f"Критична помилка: {str(e)}"},
            ensure_ascii=False,
        )
    finally:
        if driver:
            driver.quit()
