# Версія воркера. Оновлюйте це значення перед кожним новим релізом.
WORKER_VERSION = "1.0.0"
# URL сервера, до якого підключається воркер
SERVER_URL = "http://127.0.0.1:3010/api"

# Час очікування в секундах, якщо немає завдань
NO_TASK_SLEEP = 60
# Час очікування в секундах при помилці з'єднання
TIME_ERROR_SLEEP = 60


# --- РЕЄСТР ЗАВДАНЬ ---
from tasks.prom_parser import prom_parser_task

TASK_REGISTRY = {
    "prom_pars": prom_parser_task,
}