@echo off
setlocal

:: =================================================================
:: Updater Script for Worker (v2 - Robust)
:: Призначення: Надійно замінює старий .exe файл на новий і перезапускає його.
:: =================================================================

echo [UPDATER] Starting update process...

:: Отримуємо шляхи до файлів з аргументів командного рядка.
set "OLD_EXE_PATH=%~1"
set "NEW_EXE_PATH=%~2"
set "OLD_EXE_FILENAME=%~nx1"

if not defined OLD_EXE_PATH (
    echo [UPDATER_ERROR] Old EXE path not provided. Exiting.
    exit /b 1
)
if not defined NEW_EXE_PATH (
    echo [UPDATER_ERROR] New EXE path not provided. Exiting.
    exit /b 1
)

echo [UPDATER] Waiting for process %OLD_EXE_FILENAME% to terminate...
:wait_loop
:: Перевіряємо, чи є процес з такою назвою в списку активних задач
tasklist /FI "IMAGENAME eq %OLD_EXE_FILENAME%" 2>NUL | find /I /N "%OLD_EXE_FILENAME%">NUL
:: Якщо команда find знайшла процес (ERRORLEVEL 0), чекаємо 1 секунду і повторюємо
if "%ERRORLEVEL%"=="0" (
    echo [UPDATER] Process is still running, waiting 1 second...
    timeout /t 1 /nobreak > nul
    goto wait_loop
)
echo [UPDATER] Process has terminated.

:: Коли процес гарантовано завершено, намагаємося видалити файл.
echo [UPDATER] Deleting old worker: %OLD_EXE_PATH%
del "%OLD_EXE_PATH%"
if exist "%OLD_EXE_PATH%" (
    echo [UPDATER_ERROR] FAILED to delete the file. Check permissions or antivirus locking.
    exit /b 1
)
echo [UPDATER] Old worker deleted successfully.

:: Перейменовуємо новий файл на місце старого.
echo [UPDATER] Renaming %NEW_EXE_PATH% to %OLD_EXE_FILENAME%
ren "%NEW_EXE_PATH%" "%OLD_EXE_FILENAME%"

:: Запускаємо оновлений воркер.
echo [UPDATER] Starting updated worker...
start "" /D "%~dp1" "%OLD_EXE_PATH%"

echo [UPDATER] Update complete. Exiting.
endlocal