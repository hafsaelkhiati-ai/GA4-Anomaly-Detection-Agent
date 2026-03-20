"""
Email Notifier
==============
Sends HTML email digests via SMTP (Gmail or any SMTP provider).

Gmail Setup:
1. Enable 2-Factor Authentication on your Google account
2. Go to Google Account → Security → App Passwords
3. Create an App Password for "Mail" → copy the 16-char password
4. Add to .env:
   SMTP_USER=youremail@gmail.com
   SMTP_PASSWORD=xxxx xxxx xxxx xxxx  (the app password, no spaces)
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587

For other providers (e.g. SendGrid, Mailgun):
- Update SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD accordingly
"""

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

logger = logging.getLogger(__name__)


class EmailNotifier:
    """
    Sends HTML emails via SMTP.

    :param smtp_host: e.g. "smtp.gmail.com"
    :param smtp_port: e.g. 587 (TLS)
    :param smtp_user: Your sending email address
    :param smtp_password: Gmail App Password or SMTP password (from .env)
    :param from_email: From address
    :param to_emails: List of recipient email addresses
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_email: str,
        to_emails: List[str]
    ):
        if not smtp_user:
            raise ValueError("SMTP_USER not set. Add it to your .env file.")
        if not smtp_password:
            raise ValueError("SMTP_PASSWORD not set. Add your Gmail App Password to .env.")
        if not to_emails or to_emails == [""]:
            raise ValueError("ALERT_EMAILS not set. Add recipient emails to .env.")

        # 👈 All credentials come from .env — never hardcode here
        self.smtp_host     = smtp_host
        self.smtp_port     = smtp_port
        self.smtp_user     = smtp_user
        self.smtp_password = smtp_password
        self.from_email    = from_email
        self.to_emails     = [e.strip() for e in to_emails if e.strip()]

    def send(self, subject: str, html_body: str) -> bool:
        """
        Send an HTML email.

        :param subject: Email subject line
        :param html_body: Full HTML content
        :return: True on success
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = self.from_email
        msg["To"]      = ", ".join(self.to_emails)

        msg.attach(MIMEText(html_body, "html"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, self.to_emails, msg.as_string())

            logger.info(f"Email sent to: {self.to_emails}")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error(
                "SMTP Authentication failed. Check SMTP_USER and SMTP_PASSWORD in .env.\n"
                "For Gmail: make sure you're using an App Password, not your regular password."
            )
            return False
        except Exception as e:
            logger.error(f"Email send error: {e}")
            return False
