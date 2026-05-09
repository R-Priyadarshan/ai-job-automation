#!/usr/bin/env python3
"""
============================================================
scheduler.py — Python-based Job Scheduler
------------------------------------------------------------
PURPOSE:
    Runs the full pipeline automatically every day.
    Alternative to cron jobs — pure Python approach.

    Use this if you want a simpler setup than cron,
    or if you're on Windows.

HOW TO USE:
    1. Keep this running in background:
       python scheduler.py

    2. Or run with nohup on Linux (survives terminal close):
       nohup python scheduler.py > logs/scheduler.log 2>&1 &

    3. On Windows, run as a background process or use Task Scheduler.

SCHEDULE:
    - Runs main.py every day at the time set in config.yaml
    - By default: 8:00 AM daily

ALTERNATIVE: CRON JOBS (Linux/Ubuntu)
    # Edit your crontab:
    crontab -e

    # Add this line (runs at 8:00 AM every day):
    0 8 * * * cd /path/to/ai_job_automation && /path/to/venv/bin/python main.py >> logs/cron.log 2>&1

    # To see current cron jobs:
    crontab -l

    # To get the full python path:
    which python  (in your virtual environment)
============================================================
"""

import schedule                      # Python scheduling library
import time                          # Sleep between checks
import subprocess                    # Run main.py as subprocess
import sys
from pathlib import Path
from loguru import logger
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))
from src.utils.config_loader import load_config


def run_pipeline():
    """
    Runs the full job application pipeline.
    Called by the scheduler at the configured time.
    """
    logger.info("=" * 50)
    logger.info(f"⏰ Scheduled run started at {datetime.now()}")
    logger.info("=" * 50)

    try:
        # Run main.py as a separate process
        # This is cleaner than calling functions directly
        result = subprocess.run(
            [sys.executable, "main.py"],     # sys.executable = current Python
            cwd=str(Path(__file__).parent),  # Run from project root
            timeout=3600,                     # Max 1 hour
            capture_output=False,            # Show output in terminal/logs
        )

        if result.returncode == 0:
            logger.info("✅ Scheduled run completed successfully!")
        else:
            logger.error(f"❌ Scheduled run failed with code {result.returncode}")

    except subprocess.TimeoutExpired:
        logger.error("⏰ Scheduled run timed out after 1 hour!")
    except Exception as e:
        logger.error(f"Scheduled run error: {e}")


def main():
    """
    Main scheduler loop.
    Sets up the schedule and runs forever.
    """
    # Load config to get the scheduled time
    try:
        config = load_config()
        sched_cfg = config.get('scheduler', {})
        run_hour = sched_cfg.get('run_hour', 8)
        run_minute = sched_cfg.get('run_minute', 0)
    except Exception as e:
        logger.warning(f"Failed to load config: {e}. Using defaults (8:00 AM)")
        run_hour = 8
        run_minute = 0

    # Format time string: "08:00"
    run_time = f"{run_hour:02d}:{run_minute:02d}"

    # Schedule the pipeline to run every day at the configured time
    schedule.every().day.at(run_time).do(run_pipeline)

    logger.info(f"🕐 Scheduler started. Pipeline will run daily at {run_time}")
    logger.info("Press Ctrl+C to stop the scheduler.")
    logger.info("")
    logger.info("Quick Commands:")
    logger.info(f"  python scheduler.py --run-now  # Run immediately")

    # Check for --run-now flag
    if '--run-now' in sys.argv:
        logger.info("Running pipeline immediately...")
        run_pipeline()

    # Main loop — checks every 30 seconds if it's time to run
    while True:
        schedule.run_pending()     # Check if any scheduled jobs are due
        time.sleep(30)             # Wait 30 seconds before checking again


if __name__ == "__main__":
    # Set up logging to file
    Path("logs").mkdir(exist_ok=True)
    logger.add("logs/scheduler.log", rotation="1 week", retention="4 weeks")

    main()
