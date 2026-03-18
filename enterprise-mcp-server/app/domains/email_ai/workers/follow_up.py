# app/orchestrator/follow_up_job.py

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any

from celery import shared_task
from sqlalchemy import select

from app.infrastructure.database.models import (
    FollowUpTask,
    FollowUpTaskStatus,
    ApiKey,
    InAppNotification
)
from app.infrastructure.database.engine import async_session_factory
from app.domains.email_ai.tools_email import gmail_send_email

logger = logging.getLogger(__name__)

@shared_task
def check_follow_ups():
    """
    Background job entry point for Celery.
    """
    return asyncio.run(_check_follow_ups_internal())


async def _check_follow_ups_internal():
    """
    Async implementation of follow-up reminder logic.
    """
    async with async_session_factory() as db:
        try:
            logger.info("Starting check_follow_ups")
            
            # Find active follow-ups past their remind_at time
            now = datetime.now(timezone.utc)
            
            stmt = select(FollowUpTask).where(
                FollowUpTask.is_active == True,
                FollowUpTask.status == FollowUpTaskStatus.PENDING,
                FollowUpTask.remind_at <= now,
                FollowUpTask.resolved_at == None
            )
            result = await db.execute(stmt)
            pending_followups = result.scalars().all()
            
            logger.info(f"Found {len(pending_followups)} follow-ups needing reminder")
            
            reminded_count = 0
            for followup in pending_followups:
                try:
                    # 1. Send notifications
                    await send_followup_notification(db, followup)
                    
                    # 2. Update status
                    followup.status = FollowUpTaskStatus.REMINDED
                    followup.last_reminder_sent_at = now
                    followup.reminder_sent_count += 1
                    
                    await db.commit()
                    reminded_count += 1
                    
                    logger.info(f"Sent reminder for follow-up {followup.id}")
                    
                except Exception as e:
                    logger.error(f"Error sending reminder for {followup.id}: {e}")
                    await db.rollback()
                    continue
            
            logger.info(f"check_follow_ups completed: {reminded_count} reminders sent")
            
            return {"reminded": reminded_count}
        
        except Exception as e:
            logger.error(f"check_follow_ups failed: {e}")
            raise


async def send_followup_notification(db, followup: FollowUpTask):
    """
    Send reminder notification to user.
    """
    # Get user's email
    api_key_stmt = select(ApiKey).where(ApiKey.owner == followup.user_id)
    api_key_result = await db.execute(api_key_stmt)
    api_key = api_key_result.scalar_one_or_none()
    
    user_email = api_key.email if api_key else None
    
    # Method 1: Email notification (via Gmail API)
    if user_email:
        await send_email_notification(followup, user_email)
    
    # Method 2: In-app notification
    await send_inapp_notification(db, followup)


async def send_email_notification(followup: FollowUpTask, to_email: str):
    """Send email reminder using the existing gmail_send_email tool."""
    try:
        subject = f"Follow-up needed: {followup.subject[:50]}"
        body = f"""
        You've been waiting for a reply from {followup.sender}.
        
        Subject: {followup.subject}
        Category: {followup.category.value}
        
        Open in Gmail: https://mail.google.com/mail/u/0/#search/{followup.thread_id}
        
        This is reminder #{followup.reminder_sent_count + 1}
        """
        
        # Use me for sending the reminder to the same user
        await gmail_send_email(
            user_id="me", # The reminder is sent FROM the user TO the user (or TO their configured email)
            to=to_email,
            subject=subject,
            body=body
        )
        
        logger.info(f"Sent email notification for follow-up {followup.id} to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email notification: {e}")
        # Don't raise - continue with in-app notification


async def send_inapp_notification(db, followup: FollowUpTask):
    """Store in-app notification in DB."""
    try:
        notification = InAppNotification(
            user_id=followup.user_id,
            title=f"Follow-up needed from {followup.sender[:30]}",
            message=f"Waiting for: {followup.subject[:60]}",
            type="follow_up_reminder",
            action_url=f"https://mail.google.com/mail/u/0/#search/{followup.thread_id}",
            is_read=False
        )
        db.add(notification)
        # Session commit is handled by the caller loop
        logger.info(f"Prepared in-app notification for follow-up {followup.id}")
    except Exception as e:
        logger.error(f"Failed to prepare in-app notification: {e}")
