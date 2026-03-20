import httpx
import json
import logging
from typing import Dict, Any

# We use the existing config.settings
try:
    from config.settings import settings
except ImportError:
    settings = type("Settings", (), {"SLACK_BOT_TOKEN": None, "SLACK_CHANNEL_ANALYTICS": "#ops-analytics"})()

logger = logging.getLogger(__name__)

class SlackReporter:
    def __init__(self):
        self.token = getattr(settings, "SLACK_BOT_TOKEN", None)
        self.channel = getattr(settings, "SLACK_CHANNEL_ANALYTICS", "#ops-analytics")
    
    def send_report(self, title: str, report_data: Dict[str, Any]):
        if not self.token:
            logger.warning("No Slack token configured. Skipping analytics report.")
            return False
            
        # Optional: Parse standard format from prompts
        if "headline" in report_data:
            title = f"{report_data.get('health_status', '')} {report_data['headline']}"
            
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": title[:150]}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"```\n{json.dumps(report_data, indent=2)}\n```"}}
        ]
        
        try:
            resp = httpx.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
                json={"channel": self.channel, "blocks": blocks},
                timeout=10
            )
            data = resp.json()
            if not data.get("ok"):
                logger.error(f"Slack API error: {data.get('error')}")
                return False
            logger.info(f"Successfully sent Slack report: {title}")
            return True
        except Exception as e:
            logger.error(f"Failed to send Slack report: {e}")
            return False
