@echo off
:: ============================================================
:: run.bat — Windows One-Click Launcher
:: AI Job Application Automation System
:: ============================================================
:: Double-click this file to start the dashboard!
:: Make sure you have Python and Ollama installed first.
:: ============================================================

title AI Job Hunter — Dashboard Launcher

echo.
echo  ===================================================
echo   🤖  AI Job Application Automation System
echo   100%% Local ^| Zero Cost ^| Powered by Ollama
echo  ===================================================
echo.

:: Change to the project directory
cd /d "%~dp0"

:: Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.9+
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo [INFO] No venv found. Using system Python.
    echo [TIP]  Create one with: python -m venv venv
)

:: Check if dependencies are installed
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing dependencies (first run only)...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
)

:: Check Ollama
ollama --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Ollama not found in PATH.
    echo [TIP]     Download from: https://ollama.com
    echo [TIP]     The scraper will work but AI features need Ollama.
    echo.
) else (
    echo [INFO] Ollama detected. Starting Ollama server...
    start /B ollama serve
    timeout /t 2 /nobreak >nul
)

:: Launch options menu
echo What would you like to do?
echo.
echo  [1] Launch Dashboard (Streamlit Web UI)
echo  [2] Run Full Pipeline (Scrape + AI Analysis + Apply)
echo  [3] Run Scrapers Only
echo  [4] Run AI Analysis Only
echo  [5] Start Daily Scheduler (runs every 24h)
echo  [6] Exit
echo.

set /p choice="Enter choice (1-6): "

if "%choice%"=="1" goto dashboard
if "%choice%"=="2" goto full_pipeline
if "%choice%"=="3" goto scrape_only
if "%choice%"=="4" goto analyze_only
if "%choice%"=="5" goto scheduler
if "%choice%"=="6" goto end

:dashboard
echo.
echo [INFO] Starting Dashboard at http://localhost:8501 ...
echo [INFO] Press Ctrl+C to stop.
echo.
start "" "http://localhost:8501"
streamlit run dashboard\app.py
goto end

:full_pipeline
echo.
echo [INFO] Running full pipeline...
python main.py
goto end

:scrape_only
echo.
echo [INFO] Running scrapers...
python main.py --scrape-only
goto end

:analyze_only
echo.
echo [INFO] Running AI analysis...
python main.py --analyze-only
goto end

:scheduler
echo.
echo [INFO] Starting daily scheduler (runs every 24h)...
echo [INFO] Press Ctrl+C to stop.
python scheduler.py
goto end

:end
echo.
echo [INFO] Done. Press any key to exit.
pause >nul
