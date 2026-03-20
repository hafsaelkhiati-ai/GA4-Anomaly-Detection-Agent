"""
Slack Notifier
==============
Posts formatted anomaly alerts to a Slack channel using the Slack Web API.

Setup:
1. Go to https://api.slack.com/apps → Create New App → From Scratch
2. Add OAuth Scopes: chat:write, chat:write.public
3. Install to Workspace → copy "Bot User OAuth Token"
4. Add SLACK_BOT_TOKEN=xoxb-... to your .env file
5. Invite the bot to your channel: /invite @YourBotName
"""

import logging
from typing import List
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)

# Emoji map for severity
SEVERITY_EMOJI = {
    "critical": "🚨",
    "warning":  "⚠️",
    "info":     "ℹ️",
}

DIRECTION_EMOJI = {
    "drop":  "📉",
    "spike": "📈",
}


class SlackNotifier:
    """
    Sends Block Kit formatted messages to Slack.

    :param bot_token: Slack Bot OAuth Token (xoxb-...) from .env SLACK_BOT_TOKEN
    :param channel: Target channel, e.g. "#ga4-alerts" from .env SLACK_CHANNEL
    """

    def __init__(self, bot_token: str, channel: str):
        if not bot_token:
            raise ValueError("SLACK_BOT_TOKEN is not set. Add it to your .env file.")
        # 👈 Token is injected from .env — never hardcode here
        self.client  = WebClient(token=bot_token)
        self.channel = channel

    def send(self, blocks: list, text: str = "GA4 Anomaly Alert") -> bool:
        """
        Send a Block Kit message to Slack.

        :param blocks: List of Block Kit block dicts
        :param text: Fallback text for notifications
        :return: True on success
        """
        try:
            response = self.client.chat_postMessage(
                channel=self.channel,
                text=text,
                blocks=blocks
            )
            logger.info(f"Slack message sent to {self.channel} | ts={response['ts']}")
            return True
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return False
