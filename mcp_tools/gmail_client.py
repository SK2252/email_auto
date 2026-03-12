import logging
import json
from typing import Optional, List, Any, Dict
from app.domains.email_ai import tools_email as email_tools

# Structured logging setup
logger = logging.getLogger(__name__)

class GmailClient:
    """
    Thin wrapper over Enterprise MCP Gmail tools.
    Provides a consistent interface for agents to interact with Gmail.
    """

    async def poll_inbox(self) -> Dict[str, Any]:
        """Find threads where we haven't replied yet."""
        try:
            return await email_tools.gmail_list_unanswered()
        except Exception as e:
            logger.error(json.dumps({
                "event": "poll_inbox_failed",
                "error": str(e)
            }))
            raise

    async def fetch_message(self, message_id: str) -> Dict[str, Any]:
        """Fetch full content of a specific message."""
        try:
            return await email_tools.gmail_fetch_message(message_id=message_id)
        except Exception as e:
            logger.error(json.dumps({
                "event": "fetch_message_failed",
                "message_id": message_id,
                "error": str(e)
            }))
            raise

    async def fetch_thread(self, thread_id: str) -> Dict[str, Any]:
        """Fetch all messages in a conversation thread."""
        try:
            return await email_tools.gmail_fetch_thread(thread_id=thread_id)
        except Exception as e:
            logger.error(json.dumps({
                "event": "fetch_thread_failed",
                "thread_id": thread_id,
                "error": str(e)
            }))
            raise

    async def send_reply(self, to: str, subject: str, body: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """Send a real email reply (or a new email if thread_id is None)."""
        try:
            return await email_tools.gmail_send_email(
                to=to,
                subject=subject,
                body=body,
                thread_id=thread_id
            )
        except Exception as e:
            logger.error(json.dumps({
                "event": "send_reply_failed",
                "to": to,
                "thread_id": thread_id,
                "error": str(e)
            }))
            raise

    async def create_draft(self, to: str, subject: str, body: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a draft response in Gmail."""
        try:
            return await email_tools.gmail_create_draft(
                to=to,
                subject=subject,
                body=body,
                thread_id=thread_id
            )
        except Exception as e:
            logger.error(json.dumps({
                "event": "create_draft_failed",
                "to": to,
                "thread_id": thread_id,
                "error": str(e)
            }))
            raise

    async def move_to_folder(self, message_id: str, folder_label: str) -> Dict[str, Any]:
        """Move a message to a specific label (folder)."""
        try:
            return await email_tools.gmail_move_to_folder(
                message_ids=[message_id],
                folder_label=folder_label
            )
        except Exception as e:
            logger.error(json.dumps({
                "event": "move_to_folder_failed",
                "message_id": message_id,
                "folder": folder_label,
                "error": str(e)
            }))
            raise

    async def archive_message(self, message_id: str) -> Dict[str, Any]:
        """Archive a message (removes from INBOX)."""
        try:
            return await email_tools.gmail_archive_messages(
                message_ids=[message_id]
            )
        except Exception as e:
            logger.error(json.dumps({
                "event": "archive_message_failed",
                "message_id": message_id,
                "error": str(e)
            }))
            raise

# Singleton instance for app-wide use
gmail_client = GmailClient()
