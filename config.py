# Версія воркера. Оновлюйте це значення перед кожним новим релізом.
WORKER_VERSION = "1.0.2"
# URL сервера, до якого підключається воркер
SERVER_URL = "http://45.66.10.118:3010/api"

# Час очікування в секундах, якщо немає завдань
NO_TASK_SLEEP = 60
# Час очікування в секундах при помилці з'єднання
TIME_ERROR_SLEEP = 60
# Час очікування в секундах при помилці оновлення
UPDATE_FAIL_SLEEP = 1800


# --- РЕЄСТР ЗАВДАНЬ ---
from tasks.prom_parser import parse_product_data
from tasks.get_system_info import get_system_info_task

TASK_REGISTRY = {
    "prom_pars": parse_product_data,
    "get_system_info": get_system_info_task,
}
