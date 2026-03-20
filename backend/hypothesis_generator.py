"""
Hypothesis Generator
=====================
Uses OpenAI GPT-4o to generate human-readable root-cause hypotheses
and suggested actions for each detected anomaly.

Sends structured context (metric, % change, channel breakdown) and
receives a concise, professional hypothesis.
"""

import json
from typing import List
from openai import OpenAI
from anomaly_detector import Anomaly
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# ─── System prompt for GPT-4o ────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a senior digital marketing analyst specializing in GA4 and performance marketing.
You receive anomaly data from a GA4 monitoring agent and provide:
1. A concise root-cause HYPOTHESIS (1-2 sentences, professional tone)
2. A concrete SUGGESTED ACTION (1 sentence, actionable)

Rules:
- Be specific, not generic ("check your campaigns" is bad; "Paid Search sessions dropped 34% — check Google Ads for budget exhaustion or policy violations" is good)
- If the anomaly is a drop, hypothesize the most likely cause based on the channel data provided
- If it's a spike, note whether it could be a tracking issue or genuine win
- Keep total response under 80 words
- Respond ONLY as JSON: {"hypothesis": "...", "suggested_action": "..."}
"""


class HypothesisGenerator:
    """
    Calls GPT-4o for each anomaly to generate hypotheses.

    :param openai_api_key: Your OpenAI API key (from .env OPENAI_API_KEY)
    """

    def __init__(self, openai_api_key: str):
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set. Add it to your .env file.")
        # 👈 API key is passed from .env — never hardcode it here
        self.client = OpenAI(api_key=openai_api_key)

    def enrich(self, anomalies: List[Anomaly], channel_df: pd.DataFrame) -> List[Anomaly]:
        """
        Enriches each Anomaly with .hypothesis and .suggested_action
        by calling GPT-4o.

        :param anomalies: List of Anomaly objects from AnomalyDetector
        :param channel_df: Channel breakdown DataFrame for context
        :return: Same list with hypothesis fields populated
        """
        # Summarize channel breakdown for context
        channel_summary = self._summarize_channels(channel_df)

        for anomaly in anomalies:
            try:
                prompt = self._build_prompt(anomaly, channel_summary)
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user",   "content": prompt}
                    ],
                    max_tokens=200,
                    temperature=0.3,  # Low temp = consistent, professional output
                    response_format={"type": "json_object"}
                )
                raw = response.choices[0].message.content
                parsed = json.loads(raw)
                anomaly.hypothesis       = parsed.get("hypothesis", "")
                anomaly.suggested_action = parsed.get("suggested_action", "")
                logger.info(f"  Hypothesis for {anomaly.metric}: {anomaly.hypothesis[:60]}...")

            except Exception as e:
                logger.error(f"GPT-4o error for {anomaly.metric}: {e}")
                anomaly.hypothesis = "Unable to generate hypothesis — check logs."
                anomaly.suggested_action = "Manual investigation required."

        return anomalies

    def _build_prompt(self, anomaly: Anomaly, channel_summary: str) -> str:
        direction_word = "dropped" if anomaly.direction == "drop" else "spiked"
        return (
            f"ANOMALY DETECTED:\n"
            f"- Metric: {anomaly.metric}\n"
            f"- Today's value: {anomaly.current_value}\n"
            f"- Expected (7-day avg): {anomaly.expected_value}\n"
            f"- Change: {anomaly.pct_change:+.1f}% ({direction_word})\n"
            f"- Z-score: {anomaly.zscore}\n"
            f"- Severity: {anomaly.severity}\n"
            f"\nCHANNEL BREAKDOWN (last 7 days vs today):\n{channel_summary}\n"
            f"\nProvide a root-cause hypothesis and suggested action in JSON."
        )

    def _summarize_channels(self, channel_df: pd.DataFrame) -> str:
        """Builds a compact text summary of channel sessions for the last 2 days."""
        if channel_df.empty:
            return "No channel data available."

        try:
            latest_dates = channel_df["date"].nlargest(2).unique()
            subset = channel_df[channel_df["date"].isin(latest_dates)]
            pivot = subset.pivot_table(
                index="channel", columns="date", values="sessions", aggfunc="sum"
            ).fillna(0)
            return pivot.to_string()
        except Exception:
            return "Channel data unavailable."
