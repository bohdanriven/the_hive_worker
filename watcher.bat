:: =================================================================
:: Watcher Script for Worker
:: Призначення: Працює у фоновому режимі у вічному циклі.
:: Періодично перевіряє, чи запущено процес `worker.exe`,
:: і перезапускає його у тихому режимі, якщо він неактивний.
:: =================================================================

@echo off
set "WORKER_EXE=worker.exe"
:: Визначаємо шлях до папки, де лежить цей .bat файл
set "WORKER_PATH=%~dp0"

:main_loop
echo [%TIME%] Checking if %WORKER_EXE% is running...

:: Перевіряємо, чи є процес у списку завдань
tasklist /NH /FI "IMAGENAME eq %WORKER_EXE%" | find /I "%WORKER_EXE%" > nul

:: find повертає ERRORLEVEL 0, якщо знайшов, і 1, якщо не знайшов.
if "%ERRORLEVEL%"=="1" (
    echo [%TIME%] Worker is not running. Starting it now...
    :: Використовуємо динамічно визначений шлях
    start "" /D "%WORKER_PATH%" "%WORKER_PATH%%WORKER_EXE%"
) else (
    echo [%TIME%] Worker is already running.
)

:: Чекаємо 30 хвилин (1800 секунд) до наступної перевірки
echo [%TIME%] Waiting for 30 minutes...
timeout /t 1800 /nobreak > nul
goto main_loop