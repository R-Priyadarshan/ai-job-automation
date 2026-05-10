"""
============================================================
daily_prompt.py — Daily Permission Prompt
------------------------------------------------------------
PURPOSE:
    Runs every day at 8am via Windows Task Scheduler.
    Shows a popup asking permission before running the pipeline.

    YES → runs full pipeline (scrape + AI + send cold emails)
    NO  → skips today, logs the skip

HOW IT WORKS:
    Windows Task Scheduler triggers this script at 8am daily.
    This script shows a Windows dialog box.
    User clicks Yes or No.
    If Yes, runs main.py --auto-apply in a visible terminal.

SETUP:
    Run setup_task.bat as Administrator to register the task.
============================================================
"""

import sys
import subprocess
import ctypes
from pathlib import Path
from datetime import datetime
from loguru import logger

# Project root
ROOT = Path(__file__).parent

# Setup logging
ROOT.joinpath('logs').mkdir(exist_ok=True)
logger.add(
    str(ROOT / 'logs' / 'scheduler.log'),
    rotation='1 week',
    retention='4 weeks',
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
)


def show_permission_dialog() -> bool:
    """
    Shows a Windows popup dialog asking for permission to run.

    Returns:
        True if user clicked Yes, False if No or closed.
    """
    # Windows MessageBox constants
    MB_YESNO          = 0x04   # Yes + No buttons
    MB_ICONQUESTION   = 0x20   # Question mark icon
    MB_SYSTEMMODAL    = 0x1000 # Always on top
    IDYES             = 6      # Return value for Yes

    today = datetime.now().strftime('%A, %d %B %Y')

    message = (
        f"AI Job Hunter — Daily Run\n"
        f"{today}\n\n"
        f"Ready to:\n"
        f"  • Scrape new jobs from 4 sources\n"
        f"  • Score them with AI (ATS matching)\n"
        f"  • Generate tailored resumes + cover letters\n"
        f"  • Send cold internship emails\n\n"
        f"Run today's job application pipeline?"
    )

    title = "AI Job Hunter — Permission Required"

    result = ctypes.windll.user32.MessageBoxW(
        0,
        message,
        title,
        MB_YESNO | MB_ICONQUESTION | MB_SYSTEMMODAL,
    )

    return result == IDYES


def run_pipeline():
    """Runs the full auto-apply pipeline in a visible terminal window."""
    logger.info("User granted permission — starting pipeline")

    # Use 'start' to open a new visible CMD window
    # so user can see progress
    cmd = (
        f'start "AI Job Hunter - Running..." cmd /k '
        f'"cd /d {ROOT} && python main.py --auto-apply && echo. && '
        f'echo Pipeline complete! Press any key to close. && pause"'
    )

    subprocess.Popen(cmd, shell=True, cwd=str(ROOT))
    logger.info("Pipeline launched in new terminal window")


def main():
    logger.info("=" * 50)
    logger.info(f"Daily prompt triggered at {datetime.now()}")

    granted = show_permission_dialog()

    if granted:
        logger.info("Permission GRANTED by user")
        run_pipeline()
    else:
        logger.info("Permission DENIED by user — skipping today")
        # Show a brief confirmation that it was skipped
        ctypes.windll.user32.MessageBoxW(
            0,
            "Skipped for today.\nSee you tomorrow at 8:00 AM!",
            "AI Job Hunter — Skipped",
            0x40 | 0x1000,  # MB_ICONINFORMATION | MB_SYSTEMMODAL
        )


if __name__ == "__main__":
    main()
