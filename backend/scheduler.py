"""
Scheduler
=========
Runs the GA4 anomaly agent on a daily schedule.
Use this when running as a persistent process (e.g. with systemd or screen).

Alternative: Use a cron job instead (recommended for VPS).
See DEPLOYMENT_GUIDE.md for cron setup instructions.

Usage:
    python scheduler.py

The agent will run once immediately, then every day at the configured time.
"""

import schedule
import time
import logging
import os
from dotenv import load_dotenv
from agent import run_agent

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ─── Configure run time ─────────────────────────────────────────────────────
# Default: 07:00 AM daily (agent runs before business hours)
# Change this to whatever time makes sense for your clients' timezone
RUN_TIME = os.getenv("AGENT_RUN_TIME", "07:00")  # 👈 Set AGENT_RUN_TIME in .env to change


def safe_run():
    """Wraps agent.run_agent() with error handling so scheduler doesn't crash."""
    try:
        run_agent()
    except Exception as e:
        logger.error(f"Agent run failed: {e}", exc_info=True)


if __name__ == "__main__":
    logger.info(f"Scheduler starting. Agent will run daily at {RUN_TIME}.")
    
    # Run once immediately on startup
    logger.info("Running agent immediately on startup...")
    safe_run()

    # Schedule daily run
    schedule.every().day.at(RUN_TIME).do(safe_run)
    logger.info(f"Next scheduled run: {schedule.next_run()}")

    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute
