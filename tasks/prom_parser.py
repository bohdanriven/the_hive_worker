import re
import time
import tempfile
import psutil
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
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


# Функція знаходить перше число в тексті
def _extract_number(text: str) -> int | None:
    if not text:
        return None
    match = re.search(r"(\d+)", str(text))
    return int(match.group(1)) if match else None


def safe_cleanup_processes():
    """Безпечно завершує залишкові процеси від попередніх запусків Selenium."""
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            proc_name = proc.info["name"]
            if proc_name == "chromedriver.exe":
                proc.kill()
            elif (
                proc_name == "chrome.exe"
                and proc.info["cmdline"]
                and any(
                    "--remote-debugging-port" in arg for arg in proc.info["cmdline"]
                )
            ):
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass


def create_browser():
    """Створює екземпляр Chrome з налаштуваннями для тихої та ефективної роботи."""
    options = webdriver.ChromeOptions()

    # Налаштування для обходу анти-бот систем
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    options.add_argument(f"--user-agent={user_agent}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Налаштування оптимізації
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    profile_path = tempfile.mkdtemp()
    options.add_argument(f"--user-data-dir={profile_path}")

    # Налаштування для "тихого" режиму
    options.add_argument("--log-level=3")  # Показувати в логах тільки фатальні помилки
    options.add_experimental_option(
        "excludeSwitches", ["enable-logging"]
    )  # Вимкнути логування DevTools

    # Налаштування запуску
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")

    try:
        # Перенаправляємо вивід логів самого chromedriver.exe в "нікуди"
        service = ChromeService(
            executable_path=ChromeDriverManager().install(), log_output=os.devnull
        )
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
    except Exception as e:
        raise RuntimeError(f"Не вдалося створити екземпляр Chrome драйвера: {e}")

    driver.set_page_load_timeout(300)
    return driver


def parse_product_data(products_to_scrape: list) -> str:
    """Основна функція для парсингу списку товарів."""
    scraped_data = []
    try:
        driver = create_browser()
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

            try:
                # Переходимо на сторінку товару
                driver.get(product_url)

                # Шукаємо елемент для видаленого товару, і якщо такий є, ставимо статус 4
                try:
                    driver.find_element(By.CSS_SELECTOR, DELETED_WARNING_PANEL_SELECTOR)
                    daily_data["status_id"] = 4
                    scraped_data.append(daily_data)
                    time.sleep(1)
                    continue
                except NoSuchElementException:
                    pass

                # Чекаємо 5 секунд на завантаження сторінки, якщо вона не завантажилася, перевіряємо чи сторінка 404
                try:
                    wait = WebDriverWait(driver, 5)
                    status_element = wait.until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, STATUS_SELECTOR)
                        )
                    )
                    # Парсимо статус
                    status_text = status_element.text
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

                # Шукаємо елементи інформації про товар
                try:
                    main_info_block = driver.find_element(
                        By.CSS_SELECTOR, MAIN_INFO_BLOCK_SELECTOR
                    )
                    # Парсимо ціну
                    try:
                        price_element = main_info_block.find_element(
                            By.CSS_SELECTOR, PRICE_SELECTOR
                        )
                        daily_data["price"] = float(
                            price_element.get_attribute("data-qaprice")
                        )
                    except (NoSuchElementException, TypeError, ValueError):
                        pass

                    # Парсимо кількість замовлень
                    try:
                        orders_text = main_info_block.find_element(
                            By.CSS_SELECTOR, ORDER_COUNTER_SELECTOR
                        ).text
                        daily_data["order_quantity"] = _extract_number(orders_text)
                    except NoSuchElementException:
                        pass
                except NoSuchElementException:
                    pass

                # Парсимо рейтинг
                try:
                    rating_element = driver.find_element(
                        By.CSS_SELECTOR, RATING_SELECTOR
                    )
                    daily_data["rating"] = float(
                        rating_element.get_attribute("data-qarating")
                    )
                except (NoSuchElementException, TypeError, ValueError):
                    pass

            except Exception:
                # Ігноруємо помилки на рівні одного URL, щоб не зупиняти весь парсинг
                pass

            if daily_data.get("status_id") is None:
                daily_data["status_id"] = 5

            scraped_data.append(daily_data)
            time.sleep(1)

        return {"status": "success", "data": scraped_data}

    except Exception as e:
        return {"status": "failure", "message": f"Критична помилка: {str(e)}"}
    finally:
        # Закриваємо браузер
        if driver:
            driver.quit()
