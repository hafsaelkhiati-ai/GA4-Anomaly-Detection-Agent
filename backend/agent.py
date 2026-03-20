"""
GA4 Anomaly Detection Agent - Main Orchestrator
================================================
Runs daily (via cron or manual trigger) to:
1. Pull GA4 data via Google Analytics API
2. Detect anomalies using Z-score / rolling average
3. Generate hypotheses via OpenAI GPT-4o
4. Send alerts via Slack and Email
"""

import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Import our modules
from ga4_client import GA4Client
from anomaly_detector import AnomalyDetector
from hypothesis_generator import HypothesisGenerator
from slack_notifier import SlackNotifier
from email_notifier import EmailNotifier
from report_builder import ReportBuilder

# ─── Load environment variables from .env ───────────────────────────────────
load_dotenv()

# ─── Logging Setup ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/agent.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_agent():
    """
    Main agent entry point. 
    Orchestrates the full detection + alerting pipeline.
    """
    logger.info("=" * 60)
    logger.info(f"GA4 Anomaly Agent started at {datetime.now().isoformat()}")
    logger.info("=" * 60)

    # ── Step 1: Pull GA4 Data ────────────────────────────────────────────────
    logger.info("Step 1: Fetching GA4 data...")
    ga4 = GA4Client(
        property_id=os.getenv("GA4_PROPERTY_ID"),          # 👈 ADD YOUR GA4 PROPERTY ID in .env
        credentials_path=os.getenv("GA4_CREDENTIALS_PATH") # 👈 ADD PATH TO service-account.json
    )
    metrics_df = ga4.fetch_daily_metrics(lookback_days=35)
    channel_df = ga4.fetch_channel_breakdown(lookback_days=7)
    logger.info(f"Fetched {len(metrics_df)} days of data.")

    # ── Step 2: Detect Anomalies ─────────────────────────────────────────────
    logger.info("Step 2: Running anomaly detection...")
    detector = AnomalyDetector(
        zscore_threshold=float(os.getenv("ZSCORE_THRESHOLD", "2.0")),
        pct_deviation_threshold=float(os.getenv("PCT_DEVIATION_THRESHOLD", "20.0"))
    )
    anomalies = detector.detect(metrics_df)
    logger.info(f"Detected {len(anomalies)} anomalies.")

    if not anomalies:
        logger.info("No anomalies today. Sending green digest.")
        # Still send a daily 'all clear' digest
        _send_all_clear(metrics_df)
        return

    # ── Step 3: Generate Hypotheses via GPT-4o ───────────────────────────────
    logger.info("Step 3: Generating root-cause hypotheses via GPT-4o...")
    gpt = HypothesisGenerator(
        openai_api_key=os.getenv("OPENAI_API_KEY")         # 👈 ADD YOUR OPENAI API KEY in .env
    )
    enriched_anomalies = gpt.enrich(anomalies, channel_df)
    logger.info("Hypotheses generated.")

    # ── Step 4: Build Report ─────────────────────────────────────────────────
    logger.info("Step 4: Building alert report...")
    builder = ReportBuilder()
    slack_blocks = builder.build_slack_blocks(enriched_anomalies, metrics_df)
    email_html   = builder.build_email_html(enriched_anomalies, metrics_df)

    # ── Step 5: Send Slack Alert ──────────────────────────────────────────────
    logger.info("Step 5: Sending Slack alert...")
    slack = SlackNotifier(
        bot_token=os.getenv("SLACK_BOT_TOKEN"),            # 👈 ADD YOUR SLACK BOT TOKEN in .env
        channel=os.getenv("SLACK_CHANNEL", "#ga4-alerts")  # 👈 SET YOUR SLACK CHANNEL in .env
    )
    slack.send(slack_blocks)

    # ── Step 6: Send Email Digest ─────────────────────────────────────────────
    logger.info("Step 6: Sending email digest...")
    mailer = EmailNotifier(
        smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_user=os.getenv("SMTP_USER"),                  # 👈 ADD YOUR GMAIL ADDRESS in .env
        smtp_password=os.getenv("SMTP_PASSWORD"),          # 👈 ADD YOUR GMAIL APP PASSWORD in .env
        from_email=os.getenv("SMTP_USER"),
        to_emails=os.getenv("ALERT_EMAILS", "").split(",") # 👈 ADD RECIPIENT EMAILS in .env
    )
    mailer.send(
        subject=f"⚠️ GA4 Anomaly Alert — {datetime.now().strftime('%b %d, %Y')}",
        html_body=email_html
    )

    logger.info("✅ Agent run complete.")


def _send_all_clear(metrics_df):
    """Send a green 'all clear' daily digest when no anomalies are found."""
    builder = ReportBuilder()
    slack = SlackNotifier(
        bot_token=os.getenv("SLACK_BOT_TOKEN"),
        channel=os.getenv("SLACK_CHANNEL", "#ga4-alerts")
    )
    blocks = builder.build_all_clear_blocks(metrics_df)
    slack.send(blocks)


if __name__ == "__main__":
    run_agent()
