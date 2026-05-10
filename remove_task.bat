@echo off
title AI Job Hunter — Remove All Automation

echo Removing scheduled task...
schtasks /delete /tn "AIJobHunter_DailyPrompt" /f 2>nul
if errorlevel 1 (echo [INFO] Task not found.) else (echo [OK] Daily prompt task removed.)

echo Removing Ollama autostart from registry...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "OllamaServe" /f 2>nul
if errorlevel 1 (echo [INFO] Registry entry not found.) else (echo [OK] Ollama autostart removed.)

echo.
echo All automation removed.
pause
