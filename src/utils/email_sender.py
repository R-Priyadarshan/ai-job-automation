"""
============================================================
src/utils/email_sender.py
------------------------------------------------------------
PURPOSE:
    Sends cold emails via Gmail SMTP.
    Used for internship outreach — attaches resume PDF,
    personalised cover letter, and sends to recruiter/HR.

SETUP (one-time):
    1. Enable 2-Step Verification on your Gmail account
    2. Go to: myaccount.google.com → Security → App Passwords
    3. Create an App Password for "Mail"
    4. Add to .env:
         EMAIL_PASSWORD=your_16_char_app_password
    5. Update config.yaml:
         email:
           sender_email: "your@gmail.com"
           auto_send: true

RATE LIMITING:
    - Max 20 emails per day (Gmail free limit is 500/day,
      but we stay conservative to avoid spam flags)
    - 30-second delay between each email
    - Tracks sent emails in database to avoid duplicates
============================================================
"""

import smtplib
import time
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

# Load .env file for EMAIL_PASSWORD
load_dotenv()


class EmailSender:
    """
    Sends cold outreach emails via Gmail SMTP.
    Attaches resume and cover letter PDFs automatically.
    """

    # Safety limits — stay well under Gmail's daily cap
    MAX_EMAILS_PER_DAY = 20
    DELAY_BETWEEN_EMAILS = 30   # seconds — avoids spam detection

    def __init__(self, config: dict):
        """
        Initialize email sender.

        Args:
            config: Config dict from config.yaml
        """
        self.config = config
        email_cfg = config.get('email', {})

        self.smtp_server  = email_cfg.get('smtp_server', 'smtp.gmail.com')
        self.smtp_port    = email_cfg.get('smtp_port', 587)
        self.sender_email = email_cfg.get('sender_email', '')
        self.auto_send    = email_cfg.get('auto_send', False)

        # Password comes from .env — never hardcoded
        self.password = os.getenv('EMAIL_PASSWORD', '')

        # Track how many emails sent today
        self._sent_today = 0

        if not self.sender_email:
            logger.warning("Email sender_email not set in config.yaml")
        if not self.password:
            logger.warning(
                "EMAIL_PASSWORD not found in .env file. "
                "Email sending will be disabled."
            )

    def is_configured(self) -> bool:
        """Returns True if email is properly configured and ready to send."""
        return bool(self.sender_email and self.password and self.auto_send)

    def send_cold_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        resume_path: str = None,
        cover_letter_path: str = None,
        delay: bool = True,
    ) -> bool:
        """
        Sends a cold outreach email with optional PDF attachments.

        Args:
            to_email:           Recipient email address.
            subject:            Email subject line.
            body:               Email body (plain text or HTML).
            resume_path:        Optional path to resume PDF to attach.
            cover_letter_path:  Optional path to cover letter PDF to attach.
            delay:              Whether to wait DELAY_BETWEEN_EMAILS seconds after sending.

        Returns:
            True if sent successfully, False otherwise.
        """
        if not self.is_configured():
            logger.warning(
                "Email not configured. Set EMAIL_PASSWORD in .env "
                "and auto_send: true in config.yaml"
            )
            return False

        if self._sent_today >= self.MAX_EMAILS_PER_DAY:
            logger.warning(
                f"Daily email limit reached ({self.MAX_EMAILS_PER_DAY}). "
                "Will resume tomorrow."
            )
            return False

        try:
            # Build the email message
            msg = MIMEMultipart()
            msg['From']    = self.sender_email
            msg['To']      = to_email
            msg['Subject'] = subject

            # Attach the email body
            msg.attach(MIMEText(body, 'plain'))

            # Attach resume PDF if provided and exists
            if resume_path and Path(resume_path).exists():
                self._attach_file(msg, resume_path, "Resume.pdf")
                logger.debug(f"Attached resume: {resume_path}")

            # Attach cover letter PDF if provided and exists
            if cover_letter_path and Path(cover_letter_path).exists():
                self._attach_file(msg, cover_letter_path, "Cover_Letter.pdf")
                logger.debug(f"Attached cover letter: {cover_letter_path}")

            # Connect to Gmail SMTP and send
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.ehlo()
                server.starttls()                          # Encrypt connection
                server.login(self.sender_email, self.password)
                server.sendmail(
                    self.sender_email,
                    to_email,
                    msg.as_string()
                )

            self._sent_today += 1
            logger.info(
                f"Email sent to {to_email} "
                f"[{self._sent_today}/{self.MAX_EMAILS_PER_DAY} today]"
            )

            # Polite delay to avoid spam flags
            if delay:
                logger.debug(f"Waiting {self.DELAY_BETWEEN_EMAILS}s before next email...")
                time.sleep(self.DELAY_BETWEEN_EMAILS)

            return True

        except smtplib.SMTPAuthenticationError:
            logger.error(
                "Gmail authentication failed! "
                "Check your App Password in .env (EMAIL_PASSWORD). "
                "Make sure 2FA is enabled and you used an App Password, "
                "not your regular Gmail password."
            )
            return False

        except smtplib.SMTPRecipientsRefused:
            logger.warning(f"Recipient refused: {to_email} — may be invalid address")
            return False

        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending to {to_email}: {e}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error sending email to {to_email}: {e}")
            return False

    def _attach_file(self, msg: MIMEMultipart, file_path: str, filename: str):
        """
        Attaches a file to an email message.

        Args:
            msg:       The email MIMEMultipart object.
            file_path: Path to the file to attach.
            filename:  Display name for the attachment.
        """
        with open(file_path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())

        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename="{filename}"'
        )
        msg.attach(part)

    def test_connection(self) -> bool:
        """
        Tests the SMTP connection without sending an email.
        Useful for verifying credentials before running the pipeline.

        Returns:
            True if connection successful, False otherwise.
        """
        if not self.sender_email or not self.password:
            logger.error("Email credentials not configured")
            return False

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(self.sender_email, self.password)
            logger.info("Email connection test: SUCCESS")
            return True
        except smtplib.SMTPAuthenticationError:
            logger.error("Email connection test FAILED: Invalid credentials")
            return False
        except Exception as e:
            logger.error(f"Email connection test FAILED: {e}")
            return False

    def reset_daily_count(self):
        """Resets the daily sent counter. Call this at midnight."""
        self._sent_today = 0
        logger.debug("Daily email counter reset")
