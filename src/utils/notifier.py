"""
============================================================
src/utils/notifier.py
------------------------------------------------------------
PURPOSE:
    Sends Telegram notifications when important events happen:
    - New high-match jobs found
    - Resume/cover letter generated
    - Application submitted

WHY TELEGRAM?
    - 100% free bot API
    - Works on Linux/Mac/Windows
    - No server needed (uses Telegram's servers)
    - Easy to set up (5 minutes)

SETUP STEPS:
    1. Open Telegram and search for @BotFather
    2. Send /newbot and follow instructions
    3. Copy the bot token
    4. Start a chat with your bot
    5. Get your chat_id from: https://api.telegram.org/bot<TOKEN>/getUpdates
    6. Add token and chat_id to config.yaml

DISABLING:
    Set telegram.enabled: false in config.yaml to turn off.
============================================================
"""

import requests                      # HTTP requests
from loguru import logger            # Logging


class TelegramNotifier:
    """
    Sends notifications via Telegram Bot API.
    Zero cost — uses Telegram's free API.
    """

    def __init__(self, config: dict):
        """
        Initialize Telegram notifier.

        Args:
            config: Config dict from config.yaml
        """
        telegram_cfg = config.get('telegram', {})

        # Is Telegram enabled in config?
        self.enabled = telegram_cfg.get('enabled', False)

        # Your bot token from @BotFather
        self.bot_token = telegram_cfg.get('bot_token', '')

        # Your personal chat ID
        self.chat_id = telegram_cfg.get('chat_id', '')

        # Telegram API base URL
        if self.bot_token:
            self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        else:
            self.api_url = ""

        if self.enabled and (not self.bot_token or not self.chat_id):
            logger.warning(
                "Telegram is enabled but bot_token or chat_id is missing. "
                "Notifications will be disabled."
            )
            self.enabled = False

    def send(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Sends a message via Telegram.

        Args:
            message: The message text to send.
            parse_mode: 'HTML' or 'Markdown' for formatting.

        Returns:
            True if sent successfully, False otherwise.
        """
        if not self.enabled:
            logger.debug("Telegram disabled — message not sent")
            return False

        try:
            url = f"{self.api_url}/sendMessage"

            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            }

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                logger.debug("Telegram notification sent.")
                return True
            else:
                logger.warning(
                    f"Telegram send failed: {response.status_code} — {response.text}"
                )
                return False

        except requests.exceptions.ConnectionError:
            logger.warning("Telegram: No internet connection")
            return False
        except Exception as e:
            logger.error(f"Telegram notification error: {e}")
            return False

    def notify_new_jobs(self, jobs: list[dict]):
        """
        Sends notification about newly found high-match jobs.

        Args:
            jobs: List of new job dicts found today.
        """
        if not self.enabled or not jobs:
            return

        count = len(jobs)
        message = f"🤖 <b>Job Hunt Update</b>\n\n"
        message += f"📋 Found <b>{count} new jobs</b> today!\n\n"

        # Show top 5 jobs
        for job in jobs[:5]:
            title = job.get('title', 'Unknown')
            company = job.get('company', 'Unknown')
            source = job.get('source', 'unknown').title()
            url = job.get('url', '')

            message += f"🏢 <b>{title}</b>\n"
            message += f"   Company: {company}\n"
            message += f"   Source: {source}\n"
            if url:
                message += f"   <a href='{url}'>View Job</a>\n"
            message += "\n"

        if count > 5:
            message += f"... and {count - 5} more!\n"

        message += "\n🔍 Open your dashboard to see full analysis."

        self.send(message)

    def notify_high_match(self, job: dict, ats_score: int):
        """
        Sends notification for a high ATS match score.

        Args:
            job: Job dict.
            ats_score: ATS score (0-100).
        """
        if not self.enabled:
            return

        emoji = "🟢" if ats_score >= 80 else "🟡"

        message = (
            f"{emoji} <b>High Match Job Found!</b>\n\n"
            f"📌 <b>{job.get('title', '')}</b>\n"
            f"🏢 {job.get('company', '')}\n"
            f"📊 ATS Score: <b>{ats_score}/100</b>\n"
            f"📍 {job.get('location', 'Remote')}\n"
        )

        if job.get('url'):
            message += f"\n🔗 <a href='{job['url']}'>Apply Now</a>"

        self.send(message)

    def notify_docs_generated(self, job: dict, resume_path: str, cl_path: str):
        """
        Sends notification when documents are generated.

        Args:
            job: Job dict.
            resume_path: Path to generated resume PDF.
            cl_path: Path to generated cover letter PDF.
        """
        if not self.enabled:
            return

        message = (
            f"📄 <b>Documents Generated!</b>\n\n"
            f"Job: {job.get('title')} @ {job.get('company')}\n\n"
            f"✅ Resume: Generated\n"
            f"✅ Cover Letter: Generated\n\n"
            f"📁 Check your data/pdfs/ folder"
        )

        self.send(message)

    def notify_daily_summary(self, stats: dict):
        """
        Sends a daily summary of the system's activities.

        Args:
            stats: Statistics dict from DatabaseManager.get_statistics()
        """
        if not self.enabled:
            return

        message = (
            f"📊 <b>Daily Job Hunt Summary</b>\n\n"
            f"📋 Total Jobs: {stats.get('total_jobs', 0)}\n"
            f"📝 Applications: {stats.get('total_applications', 0)}\n"
            f"⭐ Avg ATS Score: {stats.get('avg_ats_score', 0)}/100\n\n"
            f"🤖 System is running automatically!\n"
            f"📱 Check dashboard for details."
        )

        self.send(message)
