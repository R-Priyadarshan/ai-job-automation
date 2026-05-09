# 🤖 AI Job Application Automation System

> **100% Local · Zero Cost · Powered by Ollama · Python Only**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![Ollama](https://img.shields.io/badge/AI-Ollama%20Local-green.svg)](https://ollama.com)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-red.svg)](https://streamlit.io)
[![Cost](https://img.shields.io/badge/Cost-Zero-brightgreen.svg)]()

---

## 🚀 Quick Start (Windows)

```
Double-click: run.bat
Choose option 1 → Dashboard opens at http://localhost:8501
```

---

## 📁 Project Structure

```
ai_job_automation/
├── 📄 run.bat              ← Windows one-click launcher
├── 📄 main.py              ← Full pipeline orchestrator
├── 📄 scheduler.py         ← Daily automation scheduler
├── 📄 config.yaml          ← YOUR settings (edit this!)
├── 📄 requirements.txt     ← Python packages
├── 📄 setup.sh             ← Linux/Ubuntu installer
│
├── 📂 dashboard/
│   └── app.py              ← Streamlit web dashboard
│
├── 📂 src/
│   ├── scrapers/           ← Job scrapers (4 sources)
│   │   ├── remoteok_scraper.py
│   │   ├── weworkremotely_scraper.py
│   │   ├── internshala_scraper.py
│   │   ├── linkedin_scraper.py
│   │   └── scraper_manager.py
│   │
│   ├── ai_engine/          ← Local AI (Ollama)
│   │   ├── ollama_client.py        ← Talks to Ollama
│   │   ├── ats_matcher.py          ← Scores resume vs job
│   │   ├── resume_parser.py        ← Reads PDF/DOCX/TXT
│   │   ├── resume_optimizer.py     ← Rewrites resume for job
│   │   └── cover_letter_generator.py ← Writes cover letters
│   │
│   ├── generators/
│   │   └── pdf_generator.py        ← Creates professional PDFs
│   │
│   ├── database/
│   │   └── db_manager.py           ← SQLite storage
│   │
│   └── utils/
│       ├── config_loader.py        ← Loads config.yaml
│       └── notifier.py             ← Telegram alerts
│
└── 📂 data/
    ├── resumes/            ← Put YOUR resume here
    ├── cover_letters/      ← Generated cover letters (Markdown)
    ├── pdfs/               ← Generated PDFs
    └── sample/
        └── sample_resume.txt ← Demo resume
```

---

## ⚙️ Setup (Step by Step)

### Step 1: Install Python
Download Python 3.9+ from https://python.org/downloads/

### Step 2: Install Ollama
Download from https://ollama.com then run:
```bash
ollama pull llama3.2
ollama serve
```

### Step 3: Install Dependencies
```bash
# Open Command Prompt in this folder, then:
pip install -r requirements.txt
```

### Step 4: Configure Your Profile
Edit `config.yaml`:
```yaml
user:
  name: "Your Full Name"
  email: "your.email@gmail.com"
  resume_path: "data/resumes/your_resume.pdf"
  target_roles:
    - "Machine Learning Engineer"
    - "Data Scientist"
```

### Step 5: Add Your Resume
Copy your resume PDF/DOCX/TXT to:
```
data/resumes/your_resume.pdf
```

### Step 6: Launch!
Double-click `run.bat` and choose option 1 for the Dashboard.

---

## 🎯 How It Works

```
┌─────────────┐    ┌──────────────┐    ┌───────────────────┐
│  4 Job Sites│───►│ SQLite DB    │───►│ Ollama AI Engine  │
│  RemoteOK   │    │ (local file) │    │ - ATS Scoring     │
│  WWRemotely │    └──────────────┘    │ - Resume Optimize │
│  Internshala│                        │ - Cover Letters   │
│  LinkedIn   │                        └───────────────────┘
└─────────────┘                                  │
                                                 ▼
                                    ┌────────────────────┐
                                    │  PDF Generator     │
                                    │  Telegram Alerts   │
                                    │  Streamlit Dashboard│
                                    └────────────────────┘
```

---

## 💻 CLI Commands

```bash
# Run full pipeline
python main.py

# Scrape jobs only
python main.py --scrape-only

# AI analysis only
python main.py --analyze-only

# Process specific job
python main.py --job-id 42

# Launch dashboard
streamlit run dashboard/app.py

# Daily scheduler
python scheduler.py
```

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| `ollama: command not found` | Download from ollama.com |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| Dashboard won't open | Run `streamlit run dashboard/app.py` |
| No jobs scraped | Check internet connection |
| AI very slow | Normal for first run; use llama3.2 model |
| PDF not generated | Install `pip install reportlab` |

---

## 📊 Dashboard Features

| Tab | Features |
|-----|----------|
| 📋 Job Listings | Filter/search all scraped jobs, view descriptions, generate docs |
| 📊 Analytics | Charts: sources, ATS scores, skill gaps, timeline |
| 📄 Documents | Download generated resumes and cover letters |
| ✅ Applications | Track application status (Applied/Interview/Offer) |
| ⚙️ Settings | View config, check Ollama status |

---

## 🆓 Zero Cost Breakdown

| Component | Free Alternative |
|-----------|-----------------|
| AI/LLM | Ollama + LLaMA 3.2 (local) |
| Database | SQLite (built into Python) |
| Dashboard | Streamlit (open source) |
| PDF Gen | ReportLab (open source) |
| Job Data | Public RSS/APIs |
| Alerts | Telegram Bot (free tier) |

**Total Monthly Cost: $0.00** 🎉

---

*Built with ❤️ using Python, Ollama, and Streamlit*
