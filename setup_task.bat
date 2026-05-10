@echo off
:: ============================================================
:: setup_task.bat — Register Daily Permission Prompt
:: Run this ONCE as Administrator to set up the daily task
:: ============================================================
:: Right-click this file → "Run as administrator"
:: ============================================================

title AI Job Hunter — Task Scheduler Setup

echo.
echo  ===================================================
echo   AI Job Hunter — Windows Task Scheduler Setup
echo  ===================================================
echo.

:: Get the full path to this project folder
set PROJECT_DIR=%~dp0
:: Remove trailing backslash
if "%PROJECT_DIR:~-1%"=="\" set PROJECT_DIR=%PROJECT_DIR:~0,-1%

:: Find Python executable
for /f "tokens=*" %%i in ('where python') do set PYTHON_EXE=%%i
if "%PYTHON_EXE%"=="" (
    echo [ERROR] Python not found in PATH!
    pause
    exit /b 1
)

echo [INFO] Project folder: %PROJECT_DIR%
echo [INFO] Python path:    %PYTHON_EXE%
echo.

:: Delete existing task if it exists (clean reinstall)
schtasks /delete /tn "AIJobHunter_DailyPrompt" /f >nul 2>&1

:: Create the scheduled task
:: Runs daily at 08:00 AM
:: Only runs when user is logged in (so the popup is visible)
schtasks /create ^
    /tn "AIJobHunter_DailyPrompt" ^
    /tr "\"%PYTHON_EXE%\" \"%PROJECT_DIR%\daily_prompt.py\"" ^
    /sc DAILY ^
    /st 08:00 ^
    /rl HIGHEST ^
    /f ^
    /it

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to create task.
    echo [TIP]   Make sure you right-clicked and chose "Run as administrator"
    pause
    exit /b 1
)

echo.
echo  ===================================================
echo   SUCCESS! Task registered.
echo  ===================================================
echo.
echo   Every day at 8:00 AM a popup will appear asking
echo   your permission before sending any emails.
echo.
echo   To verify: Open Task Scheduler and look for
echo              "AIJobHunter_DailyPrompt"
echo.
echo   To remove: Run remove_task.bat
echo   To test now: python daily_prompt.py
echo  ===================================================
echo.
pause
