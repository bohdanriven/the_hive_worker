:: =================================================================
:: Uninstaller for Worker
:: Призначення: Видаляє завдання автозапуску з Планувальника
:: завдань Windows.
:: =================================================================

@echo off
setlocal

set "TASK_NAME=WorkerStartupCheck"

echo ====================================================
echo  Uninstaller for Worker Service
echo  This will remove the auto-start task from Windows.
echo ====================================================
echo.

:: --- Перевірка прав адміністратора ---
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
:: --- Кінець перевірки прав ---

echo Deleting scheduled task: %TASK_NAME%
schtasks /delete /tn "%TASK_NAME%" /f

if "%ERRORLEVEL%"=="0" (
    echo.
    echo SUCCESS! The auto-start task has been removed.
) else (
    echo.
    echo INFO: Task was likely already removed.
)

echo.
echo Uninstallation complete. You can close this window.
pause
endlocal