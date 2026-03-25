import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from mcp.server.fastmcp import Context
from app.core.logging import get_logger
from app.infrastructure.external.gmail_client import sanitize_for_log
from ._helpers import _safe_result, _error_result

logger = get_logger(__name__)

async def tool(
    user_id: str = "me",
    to: str = "",
    subject: str = "",
    body: str = "",
    cc: Optional[str] = None,
    html_body: Optional[str] = None,
    thread_id: Optional[str] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Create a Gmail draft.

    Args:
        user_id: Gmail user ID
        to: Recipient email
        subject: Draft subject
        body: Plain text body
        cc: CC recipients
        html_body: HTML body (optional)
        thread_id: Thread ID for reply drafts

    Returns:
        Created draft ID.
    """
    if not to:
        return _error_result("gmail_create_draft", "Recipient 'to' is required")
    try:
        gmail = ctx.request_context.lifespan_context["gmail"]
        if html_body:
            message = MIMEMultipart("alternative")
            message.attach(MIMEText(body, "plain"))
            message.attach(MIMEText(html_body, "html"))
        else:
            message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        if cc:
            message["cc"] = cc
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        draft_body: dict = {"message": {"raw": raw}}
        if thread_id:
            draft_body["message"]["threadId"] = thread_id
        result = await gmail.create_draft(user_id, draft_body)
        logger.info("Gmail draft created", draft_id=result.get("id"),
                    to=sanitize_for_log(to))
        return _safe_result("gmail_create_draft", {
            "draft_id": result.get("id"),
            "message_id": result.get("message", {}).get("id"),
        })
    except Exception as e:
        logger.error("gmail_create_draft failed", error=str(e))
        return _error_result("gmail_create_draft", str(e))
