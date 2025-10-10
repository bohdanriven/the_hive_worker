# Версія воркера. Оновлюйте це значення перед кожним новим релізом.
WORKER_VERSION = "1.0.7"
# URL сервера, до якого підключається воркер
SERVER_URL = "http://45.66.10.118:3010/api"

# Час очікування в секундах, якщо немає завдань
NO_TASK_SLEEP = 180
# Час очікування в секундах при помилці з'єднання
TIME_ERROR_SLEEP = 180
# Час очікування в секундах при помилці завдання
TASK_ERROR_SLEEP = 1800
# Час очікування в секундах при помилці оновлення
UPDATE_ERROR_SLEEP = 1800


# --- РЕЄСТР ЗАВДАНЬ ---
from tasks.prom_parser import parse_product_data

TASK_REGISTRY = {
    "prom_pars": parse_product_data,
}
