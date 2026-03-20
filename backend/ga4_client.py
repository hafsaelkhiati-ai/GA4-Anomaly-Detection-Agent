"""
GA4 Client
==========
Pulls daily sessions, conversions, events, and channel breakdowns
from the Google Analytics Data API (GA4).

Requires:
- google-analytics-data Python package
- A service account JSON key with GA4 read permissions
"""

import os
import pandas as pd
from datetime import datetime, timedelta
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    DateRange,
    Dimension,
    Metric,
    OrderBy,
    Filter,
    FilterExpression,
)
from google.oauth2 import service_account
import logging

logger = logging.getLogger(__name__)


class GA4Client:
    """
    Wraps the Google Analytics Data API v1beta.

    Setup:
    1. Go to Google Cloud Console → Create a Service Account
    2. Grant it "Viewer" role on your GA4 property
    3. Download the JSON key → save path in GA4_CREDENTIALS_PATH (.env)
    4. In GA4 Admin → Account Access Management → add service account email
    """

    def __init__(self, property_id: str, credentials_path: str):
        """
        :param property_id: Your GA4 property ID (numeric, e.g. "123456789")
                            Found in GA4 Admin → Property Settings
        :param credentials_path: Path to the service account JSON file
                                 e.g. "secrets/ga4-service-account.json"
        """
        if not property_id:
            raise ValueError("GA4_PROPERTY_ID is not set. Add it to your .env file.")
        if not credentials_path or not os.path.exists(credentials_path):
            raise FileNotFoundError(
                f"GA4 credentials file not found at: {credentials_path}\n"
                "Set GA4_CREDENTIALS_PATH in your .env file."
            )

        self.property_id = property_id
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/analytics.readonly"]
        )
        self.client = BetaAnalyticsDataClient(credentials=credentials)
        logger.info(f"GA4Client initialized for property: {property_id}")

    def fetch_daily_metrics(self, lookback_days: int = 35) -> pd.DataFrame:
        """
        Fetches daily aggregate metrics for anomaly detection baseline.

        Returns DataFrame with columns:
            date, sessions, conversions, bounce_rate, avg_session_duration,
            new_users, total_users
        """
        end_date = datetime.today() - timedelta(days=1)  # yesterday
        start_date = end_date - timedelta(days=lookback_days)

        request = RunReportRequest(
            property=f"properties/{self.property_id}",
            date_ranges=[DateRange(
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d")
            )],
            dimensions=[Dimension(name="date")],
            metrics=[
                Metric(name="sessions"),
                Metric(name="conversions"),
                Metric(name="bounceRate"),
                Metric(name="averageSessionDuration"),
                Metric(name="newUsers"),
                Metric(name="totalUsers"),
            ],
            order_bys=[OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"))]
        )

        response = self.client.run_report(request)
        rows = []
        for row in response.rows:
            rows.append({
                "date": row.dimension_values[0].value,
                "sessions": int(row.metric_values[0].value),
                "conversions": int(row.metric_values[1].value),
                "bounce_rate": float(row.metric_values[2].value),
                "avg_session_duration": float(row.metric_values[3].value),
                "new_users": int(row.metric_values[4].value),
                "total_users": int(row.metric_values[5].value),
            })

        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
        df = df.sort_values("date").reset_index(drop=True)
        logger.info(f"Fetched daily metrics: {len(df)} rows from {start_date.date()} to {end_date.date()}")
        return df

    def fetch_channel_breakdown(self, lookback_days: int = 7) -> pd.DataFrame:
        """
        Fetches sessions broken down by default channel group for
        the last N days (used for hypothesis context).

        Returns DataFrame with columns:
            date, channel, sessions, conversions
        """
        end_date = datetime.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=lookback_days)

        request = RunReportRequest(
            property=f"properties/{self.property_id}",
            date_ranges=[DateRange(
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d")
            )],
            dimensions=[
                Dimension(name="date"),
                Dimension(name="sessionDefaultChannelGroup"),
            ],
            metrics=[
                Metric(name="sessions"),
                Metric(name="conversions"),
            ],
            order_bys=[OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"))]
        )

        response = self.client.run_report(request)
        rows = []
        for row in response.rows:
            rows.append({
                "date": row.dimension_values[0].value,
                "channel": row.dimension_values[1].value,
                "sessions": int(row.metric_values[0].value),
                "conversions": int(row.metric_values[1].value),
            })

        df = pd.DataFrame(rows)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
        logger.info(f"Fetched channel breakdown: {len(df)} rows")
        return df
