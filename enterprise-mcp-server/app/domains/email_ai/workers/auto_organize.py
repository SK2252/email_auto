# app/domains/email_ai/workers/auto_organize.py

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any

from celery import shared_task
from app.core.config import settings
from app.infrastructure.database.models import (
    FollowUpTask,
    FollowUpTaskStatus,
    FollowUpTaskCategory,
    FollowUpTaskPriority,
)
from app.infrastructure.database.engine import async_session_factory
from app.domains.email_ai.tools_email import (
    gmail_list_messages,
    gmail_auto_label_messages,
    gmail_archive_messages,
    get_gmail_service,
    execute_gmail_api,
)
from app.domains.email_ai.llm_decision_engine import classify_email_full
from app.domains.email_ai.label_manager import (
    get_label_name,
    ensure_label,
    bootstrap_labels,
    get_ai_label_ids,
)
from app.infrastructure.cache.redis_client import publish_email_update

logger = logging.getLogger(__name__)

# Categories that should be auto-archived
AUTO_ARCHIVE_CATEGORIES = {
    "marketing",
    "promotions",
    "notifications",
    "fyi"
}

# Default reminder frequency (hours)
REMINDER_FREQUENCY = {
    "action_required": 4,  # Remind every 4 hours
    "awaiting_reply": 24,  # Remind every 24 hours
    "follow_up": 24
}

@shared_task
def auto_organize_inbox(user_id: str, gmail_user_id: str):
    """
    Background job entry point for Celery (processes everything in inbox).
    """
    return asyncio.run(_auto_organize_inbox_internal(user_id, gmail_user_id, "is:inbox", max_results=100))

@shared_task
def backfill_inbox(user_id: str, gmail_user_id: str, max_results: int = 500):
    """
    Sweep through existing emails to apply AI labels.
    """
    return asyncio.run(_auto_organize_inbox_internal(user_id, gmail_user_id, "", max_results))


async def _auto_organize_inbox_internal(user_id: str, gmail_user_id: str, query: str = "is:unread", max_results: int = 50):
    """
    Async implementation of auto-organize logic.
    """
    async with async_session_factory() as db:
        try:
            logger.info(f"Starting email organization for {user_id}/{gmail_user_id} with query='{query}'")
            
            service = get_gmail_service()
            
            # 2. Fetch messages
            result = await gmail_list_messages(
                user_id=gmail_user_id,
                query=query,
                max_results=max_results
            )
            
            if result.get("status") != "OK":
                logger.error(f"Failed to list messages: {result.get('error')}")
                return {"status": "ERROR", "error": result.get("error")}
            
            data = result.get("data", {})
            message_list = data.get("messages", [])
            
            if not message_list:
                logger.info("No messages found matching criteria")
                return {"organized": 0, "follow_ups_created": 0}
            
            # 3. Ensure all nested labels exist
            await bootstrap_labels(gmail_user_id)

            # 4. Process each message
            organized_count = 0
            follow_ups_created = 0
            archived_count = 0
            
            # Get list of all AI label IDs once
            all_ai_ids = set(get_ai_label_ids())

            for message in message_list:
                try:
                    msg_id = message.get('id')
                    thread_id = message.get('threadId')
                    msg_labels = message.get('labelIds', [])

                    # ── LLM unified classification ──────────────────────────
                    classification = await classify_email_full(
                        sender=message.get('from', ''),
                        subject=message.get('subject', ''),
                        body=message.get('snippet', ''),
                        message_count=1,
                    )

                    category_key = classification['category']   # e.g. "action_needed"
                    priority_key = classification['priority']   # e.g. "high"

                    # ── Apply nested Gmail label ────────────────────────────
                    nested_label = get_label_name(category_key, priority_key)
                    label_id = await ensure_label(nested_label, service, gmail_user_id)
                    
                    # Prevent duplication: identify AI labels currently on message
                    current_ai_labels = [l for l in msg_labels if l in all_ai_ids]
                    
                    # Skip if the message already has the correct AI label AND nothing else
                    if len(current_ai_labels) == 1 and label_id in current_ai_labels:
                        continue

                    # Apply new label and REMOVE all other AI labels
                    await gmail_auto_label_messages(
                        user_id=gmail_user_id,
                        message_ids=[msg_id],
                        add_labels=[label_id],
                        remove_labels=current_ai_labels
                    )
                    organized_count += 1

                    # ── Auto-archive follow_up/low ──────────────────────────
                    if category_key == 'follow_up' and priority_key == 'low' and 'UNREAD' in msg_labels:
                        await gmail_archive_messages(
                            user_id=gmail_user_id,
                            message_ids=[msg_id],
                        )
                        archived_count += 1

                    # ── Persist follow-up task for awaiting_reply ───────────
                    if category_key == 'awaiting_reply':
                        from sqlalchemy import select
                        stmt = select(FollowUpTask).where(
                            FollowUpTask.user_id == user_id,
                            FollowUpTask.thread_id == thread_id,
                            FollowUpTask.is_active == True,
                        )
                        existing_result = await db.execute(stmt)
                        if not existing_result.scalar_one_or_none():
                            prio_map = {
                                'high':   FollowUpTaskPriority.HIGH,
                                'medium': FollowUpTaskPriority.MEDIUM,
                                'low':    FollowUpTaskPriority.LOW,
                            }
                            followup = FollowUpTask(
                                user_id=user_id,
                                gmail_user_id=gmail_user_id,
                                thread_id=thread_id,
                                message_id=msg_id,
                                sender=message.get('from', 'Unknown'),
                                subject=message.get('subject', 'No Subject'),
                                snippet=message.get('snippet', ''),
                                category=FollowUpTaskCategory.AWAITING_REPLY,
                                priority=prio_map.get(priority_key, FollowUpTaskPriority.MEDIUM),
                                remind_at=datetime.now(timezone.utc) + timedelta(
                                    hours=REMINDER_FREQUENCY['awaiting_reply']
                                ),
                            )
                            db.add(followup)
                            await db.commit()
                            follow_ups_created += 1

                    # ── Dispatch to OPN-Agent for routing + allocation ───────
                    from app.core.celery_app import celery_app
                    celery_app.send_task(
                        'tasks.route_and_allocate_email',
                        kwargs={
                            'payload': {
                                'message_id': msg_id,
                                'thread_id':  thread_id,
                                'classification': classification,
                            }
                        },
                        queue='routing',
                    )

                except Exception as e:
                    logger.error(f"Error processing message {message.get('id')}: {e}")
                    continue
            
            result_stats = {
                "organized": organized_count,
                "archived": archived_count,
                "follow_ups_created": follow_ups_created
            }
            
            if organized_count > 0 or archived_count > 0 or follow_ups_created > 0:
                await publish_email_update("emails_organized", result_stats)
                
            return result_stats
        
        except Exception as e:
            logger.error(f"Organization job failed: {e}")
            raise

# Legacy grok_classify_email and classify_email have been replaced by
# app.domains.email_ai.llm_decision_engine.classify_email_full
# which returns a full structured JSON classification (category + priority + department).
