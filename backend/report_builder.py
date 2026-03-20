"""
Report Builder
==============
Builds Slack Block Kit payloads and HTML email bodies
from the list of enriched Anomaly objects.
"""

from datetime import datetime
from typing import List
import pandas as pd
from anomaly_detector import Anomaly

SEVERITY_COLOR = {
    "critical": "#e53e3e",
    "warning":  "#dd6b20",
    "info":     "#3182ce",
}

SEVERITY_EMOJI = {
    "critical": "🚨",
    "warning":  "⚠️",
    "info":     "ℹ️",
}

DIRECTION_EMOJI = {
    "drop":  "📉",
    "spike": "📈",
}

METRIC_LABELS = {
    "sessions":            "Sessions",
    "conversions":         "Conversions",
    "bounce_rate":         "Bounce Rate",
    "new_users":           "New Users",
    "avg_session_duration":"Avg. Session Duration",
}


class ReportBuilder:
    """Builds formatted reports for Slack and email."""

    # ─── SLACK BLOCK KIT ─────────────────────────────────────────────────────

    def build_slack_blocks(self, anomalies: List[Anomaly], df: pd.DataFrame) -> list:
        today_str = datetime.now().strftime("%A, %b %d %Y")
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"⚠️ GA4 Anomaly Report — {today_str}"}
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{len(anomalies)} anomaly/anomalies detected* compared to 7-day baseline.\n"
                            "_Review and act before your client notices._"
                }
            },
            {"type": "divider"}
        ]

        for a in anomalies:
            emoji_dir  = DIRECTION_EMOJI.get(a.direction, "")
            emoji_sev  = SEVERITY_EMOJI.get(a.severity, "")
            label      = METRIC_LABELS.get(a.metric, a.metric.replace("_", " ").title())
            color_indicator = "🔴" if a.severity == "critical" else "🟠" if a.severity == "warning" else "🔵"

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"{emoji_sev} {color_indicator} *{label}* {emoji_dir}\n"
                        f"*Today:* `{a.current_value}` | *Expected:* `{a.expected_value}` | "
                        f"*Change:* `{a.pct_change:+.1f}%` | *Z-score:* `{a.zscore}`\n\n"
                        f"*Hypothesis:* {a.hypothesis}\n"
                        f"*Action:* _{a.suggested_action}_"
                    )
                }
            })
            blocks.append({"type": "divider"})

        # Summary stats footer
        if not df.empty:
            latest = df.iloc[-1]
            blocks.append({
                "type": "context",
                "elements": [{
                    "type": "mrkdwn",
                    "text": (
                        f"📊 Today's snapshot: "
                        f"Sessions `{int(latest.get('sessions', 0)):,}` | "
                        f"Conversions `{int(latest.get('conversions', 0)):,}` | "
                        f"New Users `{int(latest.get('new_users', 0)):,}` | "
                        f"Bounce Rate `{latest.get('bounce_rate', 0):.1f}%`"
                    )
                }]
            })

        return blocks

    def build_all_clear_blocks(self, df: pd.DataFrame) -> list:
        today_str = datetime.now().strftime("%A, %b %d %Y")
        latest = df.iloc[-1] if not df.empty else {}
        return [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"✅ GA4 Daily Digest — {today_str}"}
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*All metrics within normal range.* No anomalies detected.\n\n"
                        f"📊 Sessions: `{int(latest.get('sessions', 0)):,}` | "
                        f"Conversions: `{int(latest.get('conversions', 0)):,}` | "
                        f"New Users: `{int(latest.get('new_users', 0)):,}`"
                    )
                }
            }
        ]

    # ─── EMAIL HTML ───────────────────────────────────────────────────────────

    def build_email_html(self, anomalies: List[Anomaly], df: pd.DataFrame) -> str:
        today_str = datetime.now().strftime("%B %d, %Y")
        latest = df.iloc[-1] if not df.empty else {}

        anomaly_rows = ""
        for a in anomalies:
            color  = SEVERITY_COLOR.get(a.severity, "#3182ce")
            label  = METRIC_LABELS.get(a.metric, a.metric.replace("_", " ").title())
            sign   = "▼" if a.direction == "drop" else "▲"
            anomaly_rows += f"""
            <tr>
              <td style="padding:12px;border-bottom:1px solid #e2e8f0;">
                <strong style="color:{color};">{sign} {label}</strong>
              </td>
              <td style="padding:12px;border-bottom:1px solid #e2e8f0;">{a.current_value:,}</td>
              <td style="padding:12px;border-bottom:1px solid #e2e8f0;">{a.expected_value:,}</td>
              <td style="padding:12px;border-bottom:1px solid #e2e8f0;font-weight:bold;color:{color};">{a.pct_change:+.1f}%</td>
              <td style="padding:12px;border-bottom:1px solid #e2e8f0;font-size:13px;">{a.hypothesis}</td>
              <td style="padding:12px;border-bottom:1px solid #e2e8f0;font-size:13px;color:#2d7d46;">{a.suggested_action}</td>
            </tr>
            """

        return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:system-ui,-apple-system,sans-serif;background:#f7fafc;margin:0;padding:20px;">
  <div style="max-width:800px;margin:0 auto;background:white;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
    
    <div style="background:#1a202c;padding:24px 32px;">
      <h1 style="color:white;margin:0;font-size:20px;">⚠️ GA4 Anomaly Report</h1>
      <p style="color:#a0aec0;margin:4px 0 0;">{today_str} — {len(anomalies)} anomaly/anomalies detected</p>
    </div>

    <div style="padding:24px 32px;">
      <h2 style="font-size:16px;color:#2d3748;margin:0 0 16px;">Today's Snapshot</h2>
      <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:24px;">
        <div style="background:#edf2f7;border-radius:6px;padding:12px 20px;">
          <div style="font-size:11px;color:#718096;text-transform:uppercase;letter-spacing:0.05em;">Sessions</div>
          <div style="font-size:22px;font-weight:700;color:#2d3748;">{int(latest.get('sessions', 0)):,}</div>
        </div>
        <div style="background:#edf2f7;border-radius:6px;padding:12px 20px;">
          <div style="font-size:11px;color:#718096;text-transform:uppercase;letter-spacing:0.05em;">Conversions</div>
          <div style="font-size:22px;font-weight:700;color:#2d3748;">{int(latest.get('conversions', 0)):,}</div>
        </div>
        <div style="background:#edf2f7;border-radius:6px;padding:12px 20px;">
          <div style="font-size:11px;color:#718096;text-transform:uppercase;letter-spacing:0.05em;">New Users</div>
          <div style="font-size:22px;font-weight:700;color:#2d3748;">{int(latest.get('new_users', 0)):,}</div>
        </div>
        <div style="background:#edf2f7;border-radius:6px;padding:12px 20px;">
          <div style="font-size:11px;color:#718096;text-transform:uppercase;letter-spacing:0.05em;">Bounce Rate</div>
          <div style="font-size:22px;font-weight:700;color:#2d3748;">{latest.get('bounce_rate', 0):.1f}%</div>
        </div>
      </div>

      <h2 style="font-size:16px;color:#2d3748;margin:0 0 16px;">Detected Anomalies</h2>
      <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <thead>
          <tr style="background:#f7fafc;">
            <th style="padding:10px 12px;text-align:left;color:#718096;font-weight:600;border-bottom:2px solid #e2e8f0;">Metric</th>
            <th style="padding:10px 12px;text-align:left;color:#718096;font-weight:600;border-bottom:2px solid #e2e8f0;">Today</th>
            <th style="padding:10px 12px;text-align:left;color:#718096;font-weight:600;border-bottom:2px solid #e2e8f0;">Expected</th>
            <th style="padding:10px 12px;text-align:left;color:#718096;font-weight:600;border-bottom:2px solid #e2e8f0;">Change</th>
            <th style="padding:10px 12px;text-align:left;color:#718096;font-weight:600;border-bottom:2px solid #e2e8f0;">Hypothesis</th>
            <th style="padding:10px 12px;text-align:left;color:#718096;font-weight:600;border-bottom:2px solid #e2e8f0;">Action</th>
          </tr>
        </thead>
        <tbody>{anomaly_rows}</tbody>
      </table>
    </div>

    <div style="background:#f7fafc;padding:16px 32px;border-top:1px solid #e2e8f0;">
      <p style="margin:0;font-size:12px;color:#a0aec0;">
        Sent by GA4 Anomaly Detection Agent · Monitoring: sessions, conversions, bounce rate, new users, session duration
      </p>
    </div>
  </div>
</body>
</html>
        """.strip()
