"""
Anomaly Detector
================
Detects statistical anomalies in GA4 daily metrics using:
  1. Z-score against a 7-day rolling mean/std
  2. Percentage deviation from 7-day rolling average

Both methods can flag an anomaly. The combined result is deduplicated.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class Anomaly:
    """Represents a single detected anomaly."""
    date: str               # The anomaly date (YYYY-MM-DD)
    metric: str             # e.g. "sessions", "conversions"
    current_value: float    # Value on the anomaly date
    expected_value: float   # 7-day rolling average (baseline)
    pct_change: float       # % deviation from expected
    direction: str          # "drop" or "spike"
    zscore: float           # Z-score magnitude
    severity: str           # "critical" | "warning" | "info"
    hypothesis: str = ""    # Filled in by HypothesisGenerator
    suggested_action: str = ""


# ─── Metrics to monitor ──────────────────────────────────────────────────────
MONITORED_METRICS = [
    "sessions",
    "conversions",
    "bounce_rate",
    "new_users",
    "avg_session_duration",
]

# Severity thresholds (% absolute deviation)
SEVERITY_MAP = [
    (40.0, "critical"),
    (25.0, "warning"),
    (0.0,  "info"),
]


class AnomalyDetector:
    """
    Uses rolling statistics on the past 7 days to flag today's metrics
    as anomalous if they deviate significantly.

    :param zscore_threshold: Flag if |z| >= this value (default 2.0)
    :param pct_deviation_threshold: Flag if |pct_change| >= this % (default 20.0)
    """

    def __init__(
        self,
        zscore_threshold: float = 2.0,
        pct_deviation_threshold: float = 20.0,
        rolling_window: int = 7
    ):
        self.zscore_threshold = zscore_threshold
        self.pct_deviation_threshold = pct_deviation_threshold
        self.rolling_window = rolling_window

    def detect(self, df: pd.DataFrame) -> List[Anomaly]:
        """
        Run detection on the full DataFrame.
        Only analyzes the MOST RECENT day (yesterday's data).

        :param df: DataFrame with 'date' column + metric columns
        :return: List of Anomaly objects
        """
        if df.empty or len(df) < self.rolling_window + 1:
            logger.warning("Not enough data for anomaly detection (need 8+ days).")
            return []

        df = df.sort_values("date").reset_index(drop=True)
        today_row = df.iloc[-1]         # Most recent day
        baseline_df = df.iloc[-(self.rolling_window + 1):-1]  # Prior 7 days

        anomalies = []

        for metric in MONITORED_METRICS:
            if metric not in df.columns:
                logger.warning(f"Metric '{metric}' not in DataFrame, skipping.")
                continue

            current_val = today_row[metric]
            baseline_vals = baseline_df[metric].dropna()

            if len(baseline_vals) < 3:
                continue

            mean = baseline_vals.mean()
            std  = baseline_vals.std()
            expected = mean

            # ── Z-score ──────────────────────────────────────────────────────
            zscore = (current_val - mean) / std if std > 0 else 0.0

            # ── Percentage deviation ──────────────────────────────────────────
            pct_change = ((current_val - expected) / expected * 100) if expected != 0 else 0.0

            # ── Flag? ─────────────────────────────────────────────────────────
            z_triggered   = abs(zscore) >= self.zscore_threshold
            pct_triggered = abs(pct_change) >= self.pct_deviation_threshold

            if z_triggered or pct_triggered:
                direction = "drop" if pct_change < 0 else "spike"
                severity  = self._get_severity(abs(pct_change))

                anomaly = Anomaly(
                    date=today_row["date"].strftime("%Y-%m-%d"),
                    metric=metric,
                    current_value=round(current_val, 2),
                    expected_value=round(expected, 2),
                    pct_change=round(pct_change, 1),
                    direction=direction,
                    zscore=round(zscore, 2),
                    severity=severity,
                )
                anomalies.append(anomaly)
                logger.info(
                    f"  Anomaly: {metric} | {direction} | {pct_change:+.1f}% | "
                    f"z={zscore:.2f} | severity={severity}"
                )

        return anomalies

    def _get_severity(self, abs_pct: float) -> str:
        for threshold, label in SEVERITY_MAP:
            if abs_pct >= threshold:
                return label
        return "info"
