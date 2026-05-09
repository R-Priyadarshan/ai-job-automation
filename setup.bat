@echo off
:: ============================================================
:: setup.bat — Windows One-Command Setup Script
:: AI Job Application Automation System
:: ============================================================
:: HOW TO RUN:
::   Right-click and "Run as Administrator" OR
::   Double-click this file
:: ============================================================

title AI Job System — Setup

echo.
echo  ===================================================
echo   AI Job Application Automation System — Setup
echo   100%% Free . Local AI . Zero Cost
echo  ===================================================
echo.

:: Change to project directory
cd /d "%~dp0"

:: ---- STEP 1: Check Python ----
echo [1/7] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo [INFO]  Download Python 3.9+ from: https://www.python.org/downloads/
    echo [INFO]  Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version') do echo [OK] %%v found
echo.

:: ---- STEP 2: Create Virtual Environment ----
echo [2/7] Creating Python virtual environment...
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Virtual environment already exists. Skipping.
) else (
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created at: .\venv\
)
echo.

:: Activate venv
call venv\Scripts\activate.bat
echo [OK] Virtual environment activated.
echo.

:: ---- STEP 3: Upgrade pip ----
echo [3/7] Upgrading pip...
python -m pip install --upgrade pip --quiet
echo [OK] pip upgraded.
echo.

:: ---- STEP 4: Install Requirements ----
echo [4/7] Installing Python packages (this takes 3-5 minutes)...
echo [INFO] Installing from requirements.txt...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Some packages failed to install.
    echo [TIP]   Try running again or install manually: pip install -r requirements.txt
    pause
    exit /b 1
)
echo [OK] All Python packages installed.
echo.

:: ---- STEP 5: Download NLP Models ----
echo [5/7] Downloading NLP language models...
python -m spacy download en_core_web_sm
python -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('stopwords', quiet=True); nltk.download('averaged_perceptron_tagger', quiet=True); print('[OK] NLTK data downloaded')"
echo.

:: ---- STEP 6: Create Directory Structure ----
echo [6/7] Creating directory structure...
if not exist "data\pdfs"          mkdir "data\pdfs"
if not exist "data\resumes"       mkdir "data\resumes"
if not exist "data\cover_letters" mkdir "data\cover_letters"
if not exist "data\sample"        mkdir "data\sample"
if not exist "logs"               mkdir "logs"
echo [OK] Directories created.
echo.

:: ---- STEP 7: Check Ollama ----
echo [7/7] Checking Ollama...
ollama --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Ollama not found!
    echo [ACTION]  Download from: https://ollama.com/download
    echo [INFO]    After installing Ollama, run:
    echo              ollama pull qwen2.5
    echo.
) else (
    echo [OK] Ollama is installed.
    echo [INFO] Pulling qwen2.5 model (this may take 5-15 mins, ~4.7GB)...
    ollama pull qwen2.5
    echo [OK] Ollama model ready.
)
echo.

:: ---- Validation Tests ----
echo Running quick validation tests...
echo.
python -c "
import sys
sys.path.insert(0, '.')

tests = []

try:
    from src.utils.config_loader import load_config
    tests.append(('[OK] Config loader', True))
except Exception as e:
    tests.append((f'[FAIL] Config loader: {e}', False))

try:
    from src.database.db_manager import DatabaseManager
    db = DatabaseManager('data/test_setup.db')
    db.close()
    import os; os.remove('data/test_setup.db')
    tests.append(('[OK] Database manager', True))
except Exception as e:
    tests.append((f'[FAIL] Database: {e}', False))

try:
    import streamlit
    tests.append(('[OK] Streamlit dashboard', True))
except Exception as e:
    tests.append((f'[FAIL] Streamlit: {e}', False))

try:
    from reportlab.pdfgen import canvas
    tests.append(('[OK] PDF generator (ReportLab)', True))
except Exception as e:
    tests.append((f'[FAIL] ReportLab: {e}', False))

try:
    import sklearn, nltk, spacy
    tests.append(('[OK] NLP libraries (sklearn/nltk/spacy)', True))
except Exception as e:
    tests.append((f'[FAIL] NLP: {e}', False))

print()
for msg, ok in tests:
    print(msg)

passed = sum(1 for _, ok in tests if ok)
print(f'\nPassed: {passed}/{len(tests)} checks')
"

:: ---- Success Message ----
echo.
echo  ===================================================
echo   SETUP COMPLETE!
echo  ===================================================
echo.
echo  NEXT STEPS:
echo.
echo  1. Edit your profile in config.yaml:
echo        name, email, linkedin, github, resume_path
echo.
echo  2. Add your resume text to:
echo        data\sample\sample_resume.txt
echo.
echo  3. Make sure Ollama is running:
echo        ollama serve
echo        ollama pull qwen2.5
echo.
echo  4. Double-click run.bat to launch!
echo.
echo  Dashboard URL: http://localhost:8501
echo  ===================================================
echo.
pause
