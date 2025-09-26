@echo off
setlocal

:: =================================================================
:: Updater Script for Worker
:: Призначення: Замінює старий .exe файл на новий і перезапускає його.
:: Використання (викликається з Python): updater.bat "шлях\до\старого.exe" "шлях\до\нового.exe"
:: =================================================================

echo [UPDATER] Starting update process...

:: Отримуємо шляхи до файлів з аргументів командного рядка
set "OLD_EXE=%~1"
set "NEW_EXE=%~2"

if not defined OLD_EXE (
echo [UPDATER_ERROR] Old EXE path not provided. Exiting.
exit /b 1
)
if not defined NEW_EXE (
echo [UPDATER_ERROR] New EXE path not provided. Exiting.
exit /b 1
)

:: Чекаємо 3 секунди, щоб дати старому процесу час повністю завершитись.
:: Це найважливіший крок для уникнення помилки "file is in use".
echo [UPDATER] Waiting for the old process to terminate...
timeout /t 3 /nobreak > nul

:: Намагаємося видалити старий .exe файл.
:: Робимо це в циклі на випадок, якщо файл все ще заблокований.
echo [UPDATER] Deleting old worker: %OLD_EXE%
:delete_loop
del "%OLD_EXE%"
if exist "%OLD_EXE%" (
echo [UPDATER] Could not delete, retrying in 1 second...
timeout /t 1 /nobreak > nul
goto delete_loop
)
echo [UPDATER] Old worker deleted successfully.

:: Перейменовуємо новий файл на місце старого.
echo [UPDATER] Renaming %NEW_EXE% to %OLD_EXE%
ren "%NEW_EXE%" "%~nxOLD_EXE%"

:: Запускаємо оновлений воркер.
echo [UPDATER] Starting updated worker...
start "" "%OLD_EXE%"

echo [UPDATER] Update complete. Exiting.

endlocal