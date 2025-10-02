:: ================================================================= 
:: Startup Check Script for Worker 
:: Призначення: Автоматично запускається при вході в систему. Чекає 
:: на з'єднання з інтернетом, після чого запускає скрипт-монітор 
:: `watcher.bat` у прихованому режимі і завершує роботу. 
:: ================================================================= 

@echo off 

set "APP_DIR=%~dp0" 
set "WATCHER_SCRIPT=%APP_DIR%watcher.bat" 
set "VBS_LAUNCHER=%APP_DIR%run_hidden.vbs" 
set "WORKER_EXE=worker.exe" 

:check_internet 
echo [%TIME%] Checking for internet connection... 
ping -n 1 8.8.8.8 | find "TTL=" > nul 
if "%ERRORLEVEL%"=="0" ( 
echo [%TIME%] Internet connection is active. 
goto :check_worker_running 
) else ( 
echo [%TIME%] No internet. Retrying in 60 seconds... 
timeout /t 60 /nobreak > nul 
goto :check_internet 
)

:check_worker_running 
:: Перевіряємо, чи працює сам worker.exe. 
tasklist /NH /FI "IMAGENAME eq %WORKER_EXE%" | find /I "%WORKER_EXE%" > nul 
if "%ERRORLEVEL%"=="0" ( 
    echo [%TIME%] Worker process is already running. Exiting startup script. 
    exit 
) 

echo [%TIME%] Worker is not running. Starting the hidden watcher... 
:: Запускаємо watcher.bat через VBScript для гарантовано прихованого вікна 
wscript.exe //B "%VBS_LAUNCHER%" "%WATCHER_SCRIPT%" 

echo [%TIME%] Hidden watcher launched. Startup script finished. 
exit