"""
main.py — Primary Entry Point for the AI Inbox Management System
Phase 7: Polling Loop + Celery Beat Configuration
"""

import asyncio
import logging
import sys
from celery import Celery
from config.settings import settings
from agents.intake_agent import poll_and_ingest
from agents.sla_agent import SLA_CELERY_BEAT_SCHEDULE

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Celery App Configuration
# ---------------------------------------------------------------------------
# This app is used by workers and beat. 
# Workers: celery -A main.celery_app worker --loglevel=info
# Beat:    celery -A main.celery_app beat --loglevel=info
celery_app = Celery("email_ai_system", broker=settings.CELERY_BROKER_URL)
celery_app.conf.update(
    beat_schedule=SLA_CELERY_BEAT_SCHEDULE,
    timezone='UTC',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
)

# Import tasks to ensure registration
import agents.sla_agent  # noqa

# ---------------------------------------------------------------------------
# Polling Loop (Intake)
# ---------------------------------------------------------------------------
async def polling_loop():
    """
    Persistent loop for ST-E1-01 Gmail polling.
    Triggers run_pipeline for each new email discovered.
    """
    interval = getattr(settings, "POLLING_INTERVAL_SECONDS", 30)
    logger.info(f"Starting Gmail polling loop (Interval: {interval}s)...")
    
    while True:
        try:
            await poll_and_ingest()
        except Exception as exc:
            logger.error(f"Critical error in polling loop: {exc}", exc_info=True)
        
        await asyncio.sleep(interval)

# ---------------------------------------------------------------------------
# Main Runner
# ---------------------------------------------------------------------------
async def main():
    """Starts the primary polling loop."""
    logger.info("AI Inbox Management System: Initializing components...")
    
    # Note: In production, Celery worker and beat would run as separate processes.
    # This main.py script runs the persistent intake polling loop.
    
    try:
        await polling_loop()
    except KeyboardInterrupt:
        logger.info("System shutting down...")
    except Exception as exc:
        logger.critical(f"Unhandled exception in main: {exc}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
