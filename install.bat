@echo off
setlocal

:: =================================================================
:: Installer Script for Worker
:: Призначення: Додає скрипт перевірки (`startup_check.bat`)
:: в Планувальник завдань Windows для автоматичного запуску.
:: =================================================================

:: Назва завдання, як вона буде відображатися в Планувальнику
set "TASK_NAME=WorkerStartupCheck"
:: Визначаємо повний шлях до скрипта, який потрібно запустити
set "SCRIPT_PATH=%~dp0startup_check.bat"

echo ====================================================
echo  Installer for Worker Service
echo  This script will add a task to Windows Task Scheduler
echo  to run the worker automatically on startup.
echo ====================================================
echo.

:: Перевіряємо права адміністратора
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (
    echo Requesting administrative privileges...
    goto UACPrompt
) else ( goto gotAdmin )

:UACPrompt
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    echo UAC.ShellExecute "%~s0", "runas", "", "elevated" >> "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    exit /B

:gotAdmin
    if exist "%temp%\getadmin.vbs" ( del "%temp%\getadmin.vbs" )
    pushd "%CD%"
    CD /D "%~dp0"

echo Registering the startup task...
echo.
echo    Task Name: %TASK_NAME%
echo    Script to run: %SCRIPT_PATH%
echo.

:: Видаляємо старе завдання з таким же ім'ям, щоб уникнути помилок при повторному запуску
schtasks /delete /tn "%TASK_NAME%" /f > nul 2>&1

:: Створюємо нове завдання в Планувальнику
schtasks /create /sc onlogon /tn "%TASK_NAME%" /tr "\"%SCRIPT_PATH%\"" /rl highest /f

if "%ERRORLEVEL%"=="0" (
    echo.
    echo SUCCESS! The task has been created successfully.
    echo The script will now run automatically when a user logs in.
) else (
    echo.
    echo ERROR! Failed to create the scheduled task.
    echo Please make sure you are running this script as an Administrator.
)

echo.
echo Installation complete. You can close this window.
pause
endlocal