@echo off
title AI Job Hunter — Remove Scheduled Task

echo Removing AIJobHunter_DailyPrompt from Task Scheduler...
schtasks /delete /tn "AIJobHunter_DailyPrompt" /f

if errorlevel 1 (
    echo [INFO] Task was not found or already removed.
) else (
    echo [OK] Task removed successfully.
)

echo.
pause
