from celery import shared_task
import asyncio
from typing import Dict, Any
import logging

try:
    from mlflow_ops.analytics_engine import AnalyticsEngine
    from mlflow_ops.slack_integration import SlackReporter
except ImportError:
    AnalyticsEngine = None
    SlackReporter = None

logger = logging.getLogger(__name__)

@shared_task(name="daily_performance_summary_report")
def daily_performance_summary_report():
    if not AnalyticsEngine:
        return
    engine = AnalyticsEngine()
    reporter = SlackReporter()
    try:
        data = asyncio.run(engine.generate_performance_summary())
        reporter.send_report("Daily Performance Summary", data)
    except Exception as e:
        logger.error(f"Failed to generate/send performance summary: {e}")

@shared_task(name="realtime_dashboard_update")
def realtime_dashboard_update():
    if not AnalyticsEngine:
        return
    engine = AnalyticsEngine()
    reporter = SlackReporter()
    try:
        data = asyncio.run(engine.generate_dashboard_insights())
        reporter.send_report("Dashboard Snapshot", data)
    except Exception as e:
        logger.error(f"Failed to generate/send dashboard snapshot: {e}")

MLFLOW_CELERY_BEAT_SCHEDULE = {
    "daily-performance-summary": {
        "task": "daily_performance_summary_report",
        "schedule": 86400.0, # Every 24 hours
    },
    "realtime-dashboard-update": {
        "task": "realtime_dashboard_update",
        "schedule": 300.0, # Every 5 min
    }
}
