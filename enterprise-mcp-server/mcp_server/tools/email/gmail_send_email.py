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
    bcc: Optional[str] = None,
    html_body: Optional[str] = None,
    thread_id: Optional[str] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Send an email via Gmail API.

    Args:
        user_id: Gmail user ID
        to: Recipient email address(es), comma-separated
        subject: Email subject
        body: Plain text body
        cc: CC recipients (comma-separated)
        bcc: BCC recipients (comma-separated)
        html_body: HTML body (if provided, creates multipart message)
        thread_id: Thread ID to reply to (for in-thread replies)

    Returns:
        Sent message ID and thread ID.
    """
    if not to:
        return _error_result("gmail_send_email", "Recipient 'to' is required")
    if not subject and not thread_id:
        return _error_result("gmail_send_email", "Subject is required for new emails")
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
        if bcc:
            message["bcc"] = bcc
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        send_body: dict = {"raw": raw}
        if thread_id:
            send_body["threadId"] = thread_id
        result = await gmail.send_message(user_id, send_body)
        logger.info("Email sent via Gmail",
                    message_id=result.get("id"),
                    to=sanitize_for_log(to),
                    subject=sanitize_for_log(subject))
        return _safe_result("gmail_send_email", {
            "message_id": result.get("id"),
            "threadId": result.get("threadId"),
            "labelIds": result.get("labelIds", []),
        })
    except Exception as e:
        logger.error("gmail_send_email failed", error=str(e))
        return _error_result("gmail_send_email", str(e))
