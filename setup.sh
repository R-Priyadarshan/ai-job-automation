#!/bin/bash
# ============================================================
# setup.sh — One-command Setup Script for Ubuntu/Linux
# ============================================================
# PURPOSE:
#   Installs and configures EVERYTHING needed to run the
#   AI Job Application Automation System on Ubuntu/Linux.
#
# HOW TO RUN:
#   chmod +x setup.sh
#   ./setup.sh
#
# WHAT IT DOES:
#   1. Updates system packages
#   2. Installs Python 3 and pip
#   3. Creates Python virtual environment
#   4. Installs all Python packages from requirements.txt
#   5. Installs Ollama
#   6. Downloads the AI model (qwen2.5)
#   7. Downloads spaCy language model
#   8. Creates necessary directories
#   9. Runs a quick test
# ============================================================

set -e  # Exit immediately if any command fails

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════╗"
echo "║  AI Job Application Automation System — Setup     ║"
echo "║  100% Free • Local AI • Zero Cost                 ║"
echo "╚═══════════════════════════════════════════════════╝"
echo -e "${NC}"

# ---- STEP 1: Update System ----
echo -e "\n${BLUE}[1/9] Updating system packages...${NC}"
sudo apt-get update -qq

# ---- STEP 2: Install Python and System Dependencies ----
echo -e "\n${BLUE}[2/9] Installing Python 3 and dependencies...${NC}"
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    libssl-dev \
    libffi-dev \
    curl \
    wget \
    git \
    chromium-browser \
    chromium-chromedriver  # For Selenium (LinkedIn scraping)

echo -e "${GREEN}✅ System dependencies installed${NC}"

# ---- STEP 3: Create Python Virtual Environment ----
echo -e "\n${BLUE}[3/9] Creating Python virtual environment...${NC}"

# Create venv in project directory
python3 -m venv venv

# Activate the venv
source venv/bin/activate

echo -e "${GREEN}✅ Virtual environment created at: ./venv/${NC}"
echo -e "${YELLOW}   Activate with: source venv/bin/activate${NC}"

# ---- STEP 4: Upgrade pip ----
echo -e "\n${BLUE}[4/9] Upgrading pip...${NC}"
pip install --upgrade pip --quiet

# ---- STEP 5: Install Python Requirements ----
echo -e "\n${BLUE}[5/9] Installing Python packages (this takes 3-5 minutes)...${NC}"
pip install -r requirements.txt --quiet

echo -e "${GREEN}✅ All Python packages installed${NC}"

# ---- STEP 6: Install Ollama ----
echo -e "\n${BLUE}[6/9] Installing Ollama (local AI engine)...${NC}"

if command -v ollama &> /dev/null; then
    echo -e "${YELLOW}⚠️  Ollama already installed. Skipping.${NC}"
else
    # Official Ollama installer script
    curl -fsSL https://ollama.com/install.sh | sh

    echo -e "${GREEN}✅ Ollama installed!${NC}"
fi

# Start Ollama server in background
echo -e "\n${BLUE}Starting Ollama server...${NC}"
ollama serve &
OLLAMA_PID=$!
echo "Ollama PID: $OLLAMA_PID"

# Wait for Ollama to start
echo "Waiting for Ollama to start..."
sleep 5

# ---- STEP 7: Download AI Model ----
echo -e "\n${BLUE}[7/9] Downloading Qwen2.5 AI model (this may take 5-15 minutes)...${NC}"
echo -e "${YELLOW}Model size: ~4.7GB. Ensure you have enough disk space.${NC}"

ollama pull qwen2.5

echo -e "${GREEN}✅ Qwen2.5 model downloaded!${NC}"
echo -e "${YELLOW}   Alternative models you can download:${NC}"
echo -e "${YELLOW}   ollama pull llama3     (Meta, 4.7GB)${NC}"
echo -e "${YELLOW}   ollama pull mistral    (Mistral, 4.1GB)${NC}"
echo -e "${YELLOW}   ollama pull phi3       (Microsoft, 2.3GB — smaller/faster)${NC}"

# ---- STEP 8: Download NLP Models ----
echo -e "\n${BLUE}[8/9] Downloading NLP language models...${NC}"

# Download spaCy English model
python3 -m spacy download en_core_web_sm --quiet

# Download NLTK data
python3 -c "
import nltk
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
print('NLTK data downloaded')
"

echo -e "${GREEN}✅ NLP models downloaded${NC}"

# ---- STEP 9: Create Necessary Directories ----
echo -e "\n${BLUE}[9/9] Creating directory structure...${NC}"

mkdir -p data/pdfs
mkdir -p data/resumes
mkdir -p data/cover_letters
mkdir -p data/sample
mkdir -p logs

echo -e "${GREEN}✅ Directory structure created${NC}"

# ---- FINAL: Run Tests ----
echo -e "\n${BLUE}Running quick validation tests...${NC}"

python3 -c "
import sys
sys.path.insert(0, '.')

# Test imports
try:
    from src.utils.config_loader import load_config
    print('✅ Config loader: OK')
except Exception as e:
    print(f'❌ Config loader: {e}')

try:
    from src.database.db_manager import DatabaseManager
    db = DatabaseManager('data/test.db')
    db.close()
    import os
    os.remove('data/test.db')
    print('✅ Database manager: OK')
except Exception as e:
    print(f'❌ Database: {e}')

try:
    import ollama
    print('✅ Ollama Python client: OK')
except Exception as e:
    print(f'❌ Ollama client: {e}')

try:
    from reportlab.pdfgen import canvas
    print('✅ ReportLab PDF: OK')
except Exception as e:
    print(f'❌ ReportLab: {e}')

try:
    import streamlit
    print('✅ Streamlit: OK')
except Exception as e:
    print(f'❌ Streamlit: {e}')

print()
print('All core tests complete!')
"

# ---- SUCCESS MESSAGE ----
echo -e "\n${GREEN}"
echo "╔═══════════════════════════════════════════════════╗"
echo "║          ✅  SETUP COMPLETE!                       ║"
echo "╚═══════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${YELLOW}NEXT STEPS:${NC}"
echo ""
echo "1. Edit your profile in config.yaml:"
echo "   nano config.yaml"
echo ""
echo "2. Add your resume:"
echo "   cp your_resume.pdf data/sample/sample_resume.txt"
echo "   (or edit: data/sample/sample_resume.txt)"
echo ""
echo "3. Make sure Ollama is running:"
echo "   ollama serve &"
echo ""
echo "4. Run the full pipeline:"
echo "   source venv/bin/activate"
echo "   python main.py"
echo ""
echo "5. Open the dashboard:"
echo "   streamlit run dashboard/app.py"
echo ""
echo "6. Set up daily automation (cron):"
echo "   crontab -e"
echo "   # Add: 0 8 * * * cd $(pwd) && $(pwd)/venv/bin/python main.py >> logs/cron.log 2>&1"
echo ""
echo -e "${BLUE}Dashboard URL: http://localhost:8501${NC}"
echo ""
