import httpx
import logging
from celery import shared_task
from app.core.celery_app import celery_app

logger = logging.getLogger("celery.routing_worker")

# OPN-Agent URL (runs on port 8001)
OPN_AGENT_URL = "http://localhost:8001/api/agents/email/classify-and-route"

@celery_app.task(name='tasks.route_and_allocate_email', bind=True, max_retries=3)
def route_and_allocate_email(self, payload: dict):
    """
    Celery task that receives the LLM classification and dispatches it 
    to the OPN-Agent for sub-agent routing and allocation.
    """
    message_id = payload.get("message_id")
    classification = payload.get("classification", {})
    
    logger.info(f"Routing task started for message {message_id}")
    
    try:
        # We use a synchronous httpx client here since Celery tasks are synchronous by default unless using async event loop explicitly
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                OPN_AGENT_URL,
                json={
                    "message_id": message_id,
                    "classification": classification
                }
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Routing completed successfully for {message_id}: {result}")
            return result
            
    except httpx.HTTPStatusError as exc:
        logger.error(f"HTTP Error calling OPN-Agent: {exc.response.text}")
        # Retry for 5xx errors or connection errors
        if exc.response.status_code >= 500:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        raise
    except httpx.RequestError as exc:
        logger.error(f"Network error calling OPN-Agent: {exc}")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
    except Exception as exc:
        logger.error(f"Unexpected error in routing task: {exc}")
        raise
