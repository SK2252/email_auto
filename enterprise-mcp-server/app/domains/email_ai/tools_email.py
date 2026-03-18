"""
Gmail Email MCP Tools.

Replaces the legacy Outlook COM-based email tools with 16 Gmail API tools.
All tools use the gmail_client wrapper for OAuth, retry, and rate limiting.

Tool Categories:
  - Messages: list, fetch, search, send
  - Threads:  list, fetch, search, unanswered, summarize
  - Drafts:   create, list, delete, generate_reply
  - Profile:  fetch_profile
  - AI:       auto_label_messages, suggest_followups
"""

import base64
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional

from app.core.logging import get_logger
from app.infrastructure.external.gmail_client import (
    get_gmail_service,
    execute_gmail_api,
    sanitize_for_log,
    GmailClientError,
    GmailNotConfiguredError,
)

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helper Utilities
# ---------------------------------------------------------------------------

def _safe_result(func_name: str, result: Any) -> Dict[str, Any]:
    """Wrap a successful result with status metadata."""
    return {"status": "OK", "tool": func_name, "data": result}


def _error_result(func_name: str, error: str) -> Dict[str, Any]:
    """Wrap an error with status metadata."""
    return {"status": "ERROR", "tool": func_name, "error": error}


def _parse_message_headers(headers: list) -> Dict[str, str]:
    """Extract common headers (From, To, Subject, Date) from message headers."""
    result = {}
    for h in headers:
        name = h.get("name", "").lower()
        if name in ("from", "to", "subject", "date", "cc", "bcc"):
            result[name] = h.get("value", "")
    return result


def _decode_body(payload: dict) -> str:
    """Decode the email body from base64url encoding."""
    # Simple text body
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    # Multipart — find text/plain or text/html part
    parts = payload.get("parts", [])
    for part in parts:
        mime_type = part.get("mimeType", "")
        if mime_type == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")

    # Fallback: try text/html
    for part in parts:
        mime_type = part.get("mimeType", "")
        if mime_type == "text/html" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")

    # Nested multipart
    for part in parts:
        if part.get("parts"):
            result = _decode_body(part)
            if result:
                return result

    return ""


# ===========================================================================
# MESSAGE TOOLS
# ===========================================================================

async def gmail_list_messages(
    user_id: str = "me",
    max_results: int = 20,
    query: Optional[str] = None,
    label_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    List Gmail messages with optional query filter.

    Args:
        user_id: Gmail user ID (use "me" for authenticated user)
        max_results: Maximum number of messages to return (default 20, max 500)
        query: Gmail search query (e.g., "is:unread", "from:boss@company.com")
        label_ids: Filter by label IDs (e.g., ["INBOX", "UNREAD"])

    Returns:
        List of message summaries with id, threadId, snippet, and headers.
    """
    try:
        service = get_gmail_service()
        kwargs: dict = {"userId": user_id, "maxResults": min(max_results, 500)}
        if query:
            kwargs["q"] = query
        if label_ids:
            kwargs["labelIds"] = label_ids

        response = execute_gmail_api(service.users().messages().list(**kwargs))
        messages = response.get("messages", [])

        # Fetch summary for each message
        results = []
        for msg_ref in messages[:max_results]:
            msg = execute_gmail_api(
                service.users().messages().get(
                    userId=user_id, id=msg_ref["id"], format="metadata",
                    metadataHeaders=["From", "To", "Subject", "Date"]
                )
            )
            headers = _parse_message_headers(msg.get("payload", {}).get("headers", []))
            results.append({
                "id": msg["id"],
                "threadId": msg.get("threadId"),
                "snippet": msg.get("snippet", ""),
                "from": headers.get("from", ""),
                "to": headers.get("to", ""),
                "subject": headers.get("subject", ""),
                "date": headers.get("date", ""),
                "labelIds": msg.get("labelIds", []),
            })

        logger.info("Listed Gmail messages",
                    count=len(results),
                    query=sanitize_for_log(query or ""))
        return _safe_result("gmail_list_messages", {"messages": results, "count": len(results)})

    except GmailNotConfiguredError as e:
        return _error_result("gmail_list_messages", str(e))
    except GmailClientError as e:
        logger.error("gmail_list_messages failed", error=str(e))
        return _error_result("gmail_list_messages", str(e))


async def gmail_fetch_message(
    user_id: str = "me",
    message_id: str = "",
) -> Dict[str, Any]:
    """
    Fetch a full Gmail message by ID.

    Args:
        user_id: Gmail user ID (use "me" for authenticated user)
        message_id: The message ID to fetch

    Returns:
        Full message with headers, body, labels, and attachment info.
    """
    if not message_id:
        return _error_result("gmail_fetch_message", "message_id is required")

    try:
        service = get_gmail_service()
        msg = execute_gmail_api(
            service.users().messages().get(userId=user_id, id=message_id, format="full")
        )

        payload = msg.get("payload", {})
        headers = _parse_message_headers(payload.get("headers", []))
        body = _decode_body(payload)

        # List attachments
        attachments = []
        for part in payload.get("parts", []):
            filename = part.get("filename")
            if filename:
                attachments.append({
                    "filename": filename,
                    "mimeType": part.get("mimeType", ""),
                    "size": part.get("body", {}).get("size", 0),
                    "attachmentId": part.get("body", {}).get("attachmentId", ""),
                })

        result = {
            "id": msg["id"],
            "threadId": msg.get("threadId"),
            "labelIds": msg.get("labelIds", []),
            "snippet": msg.get("snippet", ""),
            "headers": headers,
            "body": body[:5000],  # Truncate very long bodies
            "bodyTruncated": len(body) > 5000,
            "attachments": attachments,
            "internalDate": msg.get("internalDate"),
        }

        logger.info("Fetched Gmail message",
                    message_id=message_id,
                    subject=sanitize_for_log(headers.get("subject", "")))
        return _safe_result("gmail_fetch_message", result)

    except GmailClientError as e:
        logger.error("gmail_fetch_message failed", error=str(e))
        return _error_result("gmail_fetch_message", str(e))


async def gmail_search_messages(
    user_id: str = "me",
    query: str = "",
    from_sender: Optional[str] = None,
    to_recipient: Optional[str] = None,
    subject: Optional[str] = None,
    after_date: Optional[str] = None,
    before_date: Optional[str] = None,
    has_attachment: bool = False,
    max_results: int = 20,
) -> Dict[str, Any]:
    """
    Search Gmail messages with flexible query parameters.

    Args:
        user_id: Gmail user ID
        query: Raw Gmail search query (combined with other filters)
        from_sender: Filter by sender email
        to_recipient: Filter by recipient
        subject: Filter by subject text
        after_date: Messages after this date (YYYY/MM/DD)
        before_date: Messages before this date (YYYY/MM/DD)
        has_attachment: Only messages with attachments
        max_results: Maximum results to return

    Returns:
        List of matching message summaries.
    """
    # Build combined query
    parts = []
    if query:
        parts.append(query)
    if from_sender:
        parts.append(f"from:{from_sender}")
    if to_recipient:
        parts.append(f"to:{to_recipient}")
    if subject:
        parts.append(f"subject:{subject}")
    if after_date:
        parts.append(f"after:{after_date}")
    if before_date:
        parts.append(f"before:{before_date}")
    if has_attachment:
        parts.append("has:attachment")

    combined_query = " ".join(parts) if parts else "in:inbox"

    return await gmail_list_messages(
        user_id=user_id,
        max_results=max_results,
        query=combined_query,
    )


async def gmail_send_email(
    user_id: str = "me",
    to: str = "",
    subject: str = "",
    body: str = "",
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
    html_body: Optional[str] = None,
    thread_id: Optional[str] = None,
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
        service = get_gmail_service()

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

        result = execute_gmail_api(
            service.users().messages().send(userId=user_id, body=send_body)
        )

        logger.info("Email sent via Gmail",
                    message_id=result.get("id"),
                    to=sanitize_for_log(to),
                    subject=sanitize_for_log(subject))

        return _safe_result("gmail_send_email", {
            "message_id": result.get("id"),
            "threadId": result.get("threadId"),
            "labelIds": result.get("labelIds", []),
        })

    except GmailClientError as e:
        logger.error("gmail_send_email failed", error=str(e))
        return _error_result("gmail_send_email", str(e))


# ===========================================================================
# THREAD TOOLS
# ===========================================================================

async def gmail_list_threads(
    user_id: str = "me",
    max_results: int = 20,
    query: Optional[str] = None,
    label_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    List Gmail conversation threads.

    Args:
        user_id: Gmail user ID
        max_results: Maximum threads to return
        query: Gmail search query
        label_ids: Filter by label IDs

    Returns:
        List of thread summaries.
    """
    try:
        service = get_gmail_service()
        kwargs: dict = {"userId": user_id, "maxResults": min(max_results, 500)}
        if query:
            kwargs["q"] = query
        if label_ids:
            kwargs["labelIds"] = label_ids

        response = execute_gmail_api(service.users().threads().list(**kwargs))
        threads = response.get("threads", [])

        results = []
        for t in threads[:max_results]:
            thread_data = execute_gmail_api(
                service.users().threads().get(
                    userId=user_id, id=t["id"], format="metadata",
                    metadataHeaders=["Subject", "From", "Date"]
                )
            )
            msgs = thread_data.get("messages", [])
            first_headers = _parse_message_headers(
                msgs[0].get("payload", {}).get("headers", []) if msgs else []
            )
            results.append({
                "id": thread_data["id"],
                "subject": first_headers.get("subject", ""),
                "from": first_headers.get("from", ""),
                "message_count": len(msgs),
                "snippet": thread_data.get("snippet", ""),
            })

        logger.info("Listed Gmail threads", count=len(results))
        return _safe_result("gmail_list_threads", {"threads": results, "count": len(results)})

    except GmailClientError as e:
        logger.error("gmail_list_threads failed", error=str(e))
        return _error_result("gmail_list_threads", str(e))


async def gmail_fetch_thread(
    user_id: str = "me",
    thread_id: str = "",
) -> Dict[str, Any]:
    """
    Fetch a full Gmail thread with all messages.

    Args:
        user_id: Gmail user ID
        thread_id: The thread ID to fetch

    Returns:
        Full thread with all messages, headers, and bodies.
    """
    if not thread_id:
        return _error_result("gmail_fetch_thread", "thread_id is required")

    try:
        service = get_gmail_service()
        thread = execute_gmail_api(
            service.users().threads().get(userId=user_id, id=thread_id, format="full")
        )

        messages = []
        for msg in thread.get("messages", []):
            payload = msg.get("payload", {})
            headers = _parse_message_headers(payload.get("headers", []))
            body = _decode_body(payload)
            messages.append({
                "id": msg["id"],
                "from": headers.get("from", ""),
                "to": headers.get("to", ""),
                "date": headers.get("date", ""),
                "body": body[:3000],
                "bodyTruncated": len(body) > 3000,
                "labelIds": msg.get("labelIds", []),
            })

        first_headers = _parse_message_headers(
            thread["messages"][0].get("payload", {}).get("headers", []) if thread.get("messages") else []
        )

        result = {
            "id": thread["id"],
            "subject": first_headers.get("subject", ""),
            "messages": messages,
            "message_count": len(messages),
        }

        logger.info("Fetched Gmail thread",
                    thread_id=thread_id,
                    message_count=len(messages))
        return _safe_result("gmail_fetch_thread", result)

    except GmailClientError as e:
        logger.error("gmail_fetch_thread failed", error=str(e))
        return _error_result("gmail_fetch_thread", str(e))


async def gmail_search_threads(
    user_id: str = "me",
    query: str = "",
    max_results: int = 20,
) -> Dict[str, Any]:
    """
    Search Gmail threads by query.

    Args:
        user_id: Gmail user ID
        query: Gmail search query
        max_results: Maximum results

    Returns:
        List of matching thread summaries.
    """
    return await gmail_list_threads(user_id=user_id, max_results=max_results, query=query)


async def gmail_list_unanswered(
    user_id: str = "me",
    max_results: int = 20,
) -> Dict[str, Any]:
    """
    Find threads where you received a message but haven't replied.

    Args:
        user_id: Gmail user ID
        max_results: Maximum results

    Returns:
        List of unanswered threads with last sender info.
    """
    try:
        service = get_gmail_service()

        # Get user's email to identify their messages
        profile = execute_gmail_api(service.users().getProfile(userId=user_id))
        my_email = profile.get("emailAddress", "")

        # Get recent inbox threads
        response = execute_gmail_api(
            service.users().threads().list(
                userId=user_id, maxResults=50, q="in:inbox"
            )
        )
        threads = response.get("threads", [])

        unanswered = []
        for t in threads:
            if len(unanswered) >= max_results:
                break

            thread = execute_gmail_api(
                service.users().threads().get(
                    userId=user_id, id=t["id"], format="metadata",
                    metadataHeaders=["From", "Subject", "Date"]
                )
            )
            msgs = thread.get("messages", [])
            if not msgs:
                continue

            # Check if last message is from someone else (not me)
            last_msg = msgs[-1]
            last_headers = _parse_message_headers(
                last_msg.get("payload", {}).get("headers", [])
            )
            last_from = last_headers.get("from", "")

            if my_email.lower() not in last_from.lower():
                first_headers = _parse_message_headers(
                    msgs[0].get("payload", {}).get("headers", [])
                )
                unanswered.append({
                    "thread_id": thread["id"],
                    "subject": first_headers.get("subject", ""),
                    "last_sender": last_from,
                    "last_date": last_headers.get("date", ""),
                    "message_count": len(msgs),
                })

        logger.info("Found unanswered threads", count=len(unanswered))
        return _safe_result("gmail_list_unanswered", {
            "threads": unanswered, "count": len(unanswered)
        })

    except GmailClientError as e:
        logger.error("gmail_list_unanswered failed", error=str(e))
        return _error_result("gmail_list_unanswered", str(e))


async def gmail_summarize_thread(
    user_id: str = "me",
    thread_id: str = "",
) -> Dict[str, Any]:
    """
    Summarize a Gmail thread (returns structured metadata for AI summarization).

    Note: Actual AI summarization is done by the EmailAgent using LLM.
    This tool extracts and structures the thread data for summarization.

    Args:
        user_id: Gmail user ID
        thread_id: Thread to summarize

    Returns:
        Structured thread data ready for AI summarization.
    """
    if not thread_id:
        return _error_result("gmail_summarize_thread", "thread_id is required")

    try:
        # Fetch full thread
        thread_result = await gmail_fetch_thread(user_id=user_id, thread_id=thread_id)
        if thread_result["status"] != "OK":
            return thread_result

        thread_data = thread_result["data"]
        messages = thread_data.get("messages", [])

        # Build summary structure
        participants = set()
        timeline = []
        for msg in messages:
            sender = msg.get("from", "Unknown")
            participants.add(sender)
            timeline.append({
                "from": sender,
                "date": msg.get("date", ""),
                "body_preview": msg.get("body", "")[:500],
            })

        summary = {
            "thread_id": thread_id,
            "subject": thread_data.get("subject", ""),
            "participant_count": len(participants),
            "participants": list(participants),
            "message_count": len(messages),
            "timeline": timeline,
            "needs_reply": len(messages) > 0 and messages[-1].get("from", "") != user_id,
        }

        logger.info(f"Summarized Gmail thread {thread_id} with {len(messages)} messages")
        return _safe_result("gmail_summarize_thread", summary)

    except GmailClientError as e:
        logger.error(f"gmail_summarize_thread failed for {thread_id}: {e}")
        return _error_result("gmail_summarize_thread", str(e))


# ===========================================================================
# DRAFT TOOLS
# ===========================================================================

async def gmail_create_draft(
    user_id: str = "me",
    to: str = "",
    subject: str = "",
    body: str = "",
    cc: Optional[str] = None,
    html_body: Optional[str] = None,
    thread_id: Optional[str] = None,
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
        service = get_gmail_service()

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

        result = execute_gmail_api(
            service.users().drafts().create(userId=user_id, body=draft_body)
        )

        logger.info("Gmail draft created",
                    draft_id=result.get("id"),
                    to=sanitize_for_log(to))

        return _safe_result("gmail_create_draft", {
            "draft_id": result.get("id"),
            "message_id": result.get("message", {}).get("id"),
        })

    except GmailClientError as e:
        logger.error("gmail_create_draft failed", error=str(e))
        return _error_result("gmail_create_draft", str(e))


async def gmail_list_drafts(
    user_id: str = "me",
    max_results: int = 20,
) -> Dict[str, Any]:
    """
    List Gmail drafts.

    Args:
        user_id: Gmail user ID
        max_results: Maximum drafts to return

    Returns:
        List of draft summaries.
    """
    try:
        service = get_gmail_service()
        response = execute_gmail_api(
            service.users().drafts().list(userId=user_id, maxResults=min(max_results, 500))
        )
        drafts = response.get("drafts", [])

        results = []
        for d in drafts[:max_results]:
            draft = execute_gmail_api(
                service.users().drafts().get(userId=user_id, id=d["id"], format="metadata")
            )
            msg = draft.get("message", {})
            headers = _parse_message_headers(msg.get("payload", {}).get("headers", []))
            results.append({
                "id": draft["id"],
                "message_id": msg.get("id"),
                "to": headers.get("to", ""),
                "subject": headers.get("subject", ""),
                "snippet": msg.get("snippet", ""),
            })

        logger.info("Listed Gmail drafts", count=len(results))
        return _safe_result("gmail_list_drafts", {"drafts": results, "count": len(results)})

    except GmailClientError as e:
        logger.error("gmail_list_drafts failed", error=str(e))
        return _error_result("gmail_list_drafts", str(e))


async def gmail_delete_draft(
    user_id: str = "me",
    draft_id: str = "",
) -> Dict[str, Any]:
    """
    Delete a Gmail draft.

    Args:
        user_id: Gmail user ID
        draft_id: Draft ID to delete

    Returns:
        Confirmation of deletion.
    """
    if not draft_id:
        return _error_result("gmail_delete_draft", "draft_id is required")

    try:
        service = get_gmail_service()
        execute_gmail_api(
            service.users().drafts().delete(userId=user_id, id=draft_id)
        )

        logger.info("Gmail draft deleted", draft_id=draft_id)
        return _safe_result("gmail_delete_draft", {"deleted": True, "draft_id": draft_id})

    except GmailClientError as e:
        logger.error("gmail_delete_draft failed", error=str(e))
        return _error_result("gmail_delete_draft", str(e))


async def gmail_generate_reply_draft(
    user_id: str = "me",
    thread_id: str = "",
    reply_body: str = "",
    reply_html: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a reply draft for a thread.

    Note: The actual AI-generated reply text should be created by the EmailAgent
    using LLM, then passed here as reply_body. This tool handles the Gmail-specific
    draft creation with proper threading.

    Args:
        user_id: Gmail user ID
        thread_id: Thread to reply to
        reply_body: The reply text (typically AI-generated by the agent)
        reply_html: Optional HTML version of the reply

    Returns:
        Created reply draft ID.
    """
    if not thread_id:
        return _error_result("gmail_generate_reply_draft", "thread_id is required")
    if not reply_body:
        return _error_result("gmail_generate_reply_draft", "reply_body is required")

    try:
        # Fetch thread to get the last message's From address and subject
        thread_result = await gmail_fetch_thread(user_id=user_id, thread_id=thread_id)
        if thread_result["status"] != "OK":
            return thread_result

        thread_data = thread_result["data"]
        messages = thread_data.get("messages", [])
        if not messages:
            return _error_result("gmail_generate_reply_draft", "Thread has no messages")

        last_msg = messages[-1]
        reply_to = last_msg.get("from", "")
        subject = thread_data.get("subject", "")
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        # Create the reply draft
        return await gmail_create_draft(
            user_id=user_id,
            to=reply_to,
            subject=subject,
            body=reply_body,
            html_body=reply_html,
            thread_id=thread_id,
        )

    except GmailClientError as e:
        logger.error("gmail_generate_reply_draft failed", error=str(e))
        return _error_result("gmail_generate_reply_draft", str(e))


# ===========================================================================
# PROFILE TOOL
# ===========================================================================

async def gmail_fetch_profile(
    user_id: str = "me",
) -> Dict[str, Any]:
    """
    Fetch the authenticated user's Gmail profile.

    Args:
        user_id: Gmail user ID

    Returns:
        Email address, total messages, total threads, and history ID.
    """
    try:
        service = get_gmail_service()
        profile = execute_gmail_api(service.users().getProfile(userId=user_id))

        result = {
            "emailAddress": profile.get("emailAddress"),
            "messagesTotal": profile.get("messagesTotal"),
            "threadsTotal": profile.get("threadsTotal"),
            "historyId": profile.get("historyId"),
        }

        logger.info("Fetched Gmail profile",
                    email=sanitize_for_log(result.get("emailAddress", "")))
        return _safe_result("gmail_fetch_profile", result)

    except GmailClientError as e:
        logger.error("gmail_fetch_profile failed", error=str(e))
        return _error_result("gmail_fetch_profile", str(e))


# ===========================================================================
# AI / AUTOMATION TOOLS
# ===========================================================================

async def gmail_auto_label_messages(
    user_id: str = "me",
    message_ids: Optional[List[str]] = None,
    add_labels: Optional[List[str]] = None,
    remove_labels: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Apply or remove labels on Gmail messages.

    Args:
        user_id: Gmail user ID
        message_ids: List of message IDs to modify
        add_labels: Label IDs to add (e.g., ["STARRED", "Label_123"])
        remove_labels: Label IDs to remove (e.g., ["UNREAD"])

    Returns:
        Count of successfully labeled messages.
    """
    if not message_ids:
        return _error_result("gmail_auto_label_messages", "message_ids is required")
    if not add_labels and not remove_labels:
        return _error_result("gmail_auto_label_messages",
                           "At least one of add_labels or remove_labels is required")

    try:
        service = get_gmail_service()
        labeled_count = 0

        for msg_id in message_ids:
            body: dict = {}
            if add_labels:
                body["addLabelIds"] = add_labels
            if remove_labels:
                body["removeLabelIds"] = remove_labels

            execute_gmail_api(
                service.users().messages().modify(userId=user_id, id=msg_id, body=body)
            )
            labeled_count += 1

        logger.info("Auto-labeled Gmail messages",
                    count=labeled_count,
                    add_labels=add_labels,
                    remove_labels=remove_labels)

        return _safe_result("gmail_auto_label_messages", {
            "labeled_count": labeled_count,
            "add_labels": add_labels,
            "remove_labels": remove_labels,
        })

    except GmailClientError as e:
        logger.error("gmail_auto_label_messages failed", error=str(e))
        return _error_result("gmail_auto_label_messages", str(e))


async def gmail_suggest_followups(
    user_id: str = "me",
    thread_ids: Optional[List[str]] = None,
    max_results: int = 10,
) -> Dict[str, Any]:
    """
    Identify threads that need follow-up action.

    Analyzes threads to find ones where:
    - Last message is from someone else (not user)
    - Thread has been idle for a configurable period
    - Thread has certain labels suggesting action needed

    Note: The EmailAgent can run AI analysis on the returned data
    to provide more nuanced follow-up suggestions.

    Args:
        user_id: Gmail user ID
        thread_ids: Specific thread IDs to check (if None, scans recent inbox)
        max_results: Maximum follow-up suggestions to return

    Returns:
        List of threads needing follow-up with reason and priority.
    """
    try:
        service = get_gmail_service()

        # Get user email
        profile = execute_gmail_api(service.users().getProfile(userId=user_id))
        my_email = profile.get("emailAddress", "").lower()

        # Get threads to analyze
        if thread_ids:
            threads_to_check = [{"id": tid} for tid in thread_ids]
        else:
            response = execute_gmail_api(
                service.users().threads().list(
                    userId=user_id, maxResults=50, q="in:inbox is:unread"
                )
            )
            threads_to_check = response.get("threads", [])

        followups = []
        for t in threads_to_check:
            if len(followups) >= max_results:
                break

            thread = execute_gmail_api(
                service.users().threads().get(
                    userId=user_id, id=t["id"], format="metadata",
                    metadataHeaders=["From", "Subject", "Date"]
                )
            )

            msgs = thread.get("messages", [])
            if not msgs:
                continue

            last_msg = msgs[-1]
            last_headers = _parse_message_headers(
                last_msg.get("payload", {}).get("headers", [])
            )
            last_from = last_headers.get("from", "").lower()
            first_headers = _parse_message_headers(
                msgs[0].get("payload", {}).get("headers", [])
            )

            # Determine if follow-up needed
            reasons = []
            priority = "low"

            if my_email not in last_from:
                reasons.append("awaiting_your_reply")
                priority = "medium"

            if "IMPORTANT" in last_msg.get("labelIds", []):
                reasons.append("marked_important")
                priority = "high"

            if len(msgs) > 3:
                reasons.append("long_conversation")

            if reasons:
                followups.append({
                    "thread_id": thread["id"],
                    "subject": first_headers.get("subject", ""),
                    "last_sender": last_headers.get("from", ""),
                    "last_date": last_headers.get("date", ""),
                    "message_count": len(msgs),
                    "reasons": reasons,
                    "priority": priority,
                })

        logger.info(f"Suggested {len(followups)} follow-ups")
        return _safe_result("gmail_suggest_followups", {
            "followups": followups, "count": len(followups)
        })

    except GmailClientError as e:
        logger.error(f"gmail_suggest_followups failed: {e}")
        return _error_result("gmail_suggest_followups", str(e))


# ===========================================================================
# ARCHIVE & MOVE TOOLS (Phase 5B)
# ===========================================================================

async def gmail_archive_messages(
    user_id: str = "me",
    message_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Archive Gmail messages (remove INBOX label).

    Args:
        user_id: Gmail user ID
        message_ids: List of message IDs to archive

    Returns:
        Count of archived messages.
    """
    if not message_ids:
        return _error_result("gmail_archive_messages", "message_ids is required")

    return await gmail_auto_label_messages(
        user_id=user_id,
        message_ids=message_ids,
        remove_labels=["INBOX"],
    )


async def gmail_move_to_folder(
    user_id: str = "me",
    message_ids: Optional[List[str]] = None,
    folder_label: str = "",
) -> Dict[str, Any]:
    """
    Move messages to a folder/label (creates label if it doesn't exist).

    Args:
        user_id: Gmail user ID
        message_ids: List of message IDs to move
        folder_label: Target label name (e.g., "Projects/Client-A")

    Returns:
        Count of moved messages and label ID used.
    """
    if not message_ids:
        return _error_result("gmail_move_to_folder", "message_ids is required")
    if not folder_label:
        return _error_result("gmail_move_to_folder", "folder_label is required")

    try:
        service = get_gmail_service()

        # Find or create the label
        labels_response = execute_gmail_api(
            service.users().labels().list(userId=user_id)
        )
        existing_labels = {
            lbl["name"]: lbl["id"]
            for lbl in labels_response.get("labels", [])
        }

        if folder_label in existing_labels:
            label_id = existing_labels[folder_label]
        else:
            # Create new label
            new_label = execute_gmail_api(
                service.users().labels().create(
                    userId=user_id,
                    body={
                        "name": folder_label,
                        "labelListVisibility": "labelShow",
                        "messageListVisibility": "show",
                    }
                )
            )
            label_id = new_label["id"]
            logger.info("Created Gmail label", name=folder_label, id=label_id)

        # Apply label and remove from INBOX
        result = await gmail_auto_label_messages(
            user_id=user_id,
            message_ids=message_ids,
            add_labels=[label_id],
            remove_labels=["INBOX"],
        )

        if result["status"] == "OK":
            result["data"]["label_id"] = label_id
            result["data"]["folder_label"] = folder_label

        return result

    except GmailClientError as e:
        logger.error("gmail_move_to_folder failed", error=str(e))
        return _error_result("gmail_move_to_folder", str(e))


# ===========================================================================
# ATTACHMENT DOWNLOAD TOOL — added by patch_tools_email.py
# ===========================================================================

async def gmail_get_attachment(
    message_id: str = "",
    attachment_id: str = "",
    user_id: str = "me",
) -> Dict[str, Any]:
    """
    Download raw attachment bytes (base64url) from Gmail API.

    Args:
        message_id:    Gmail message ID containing the attachment
        attachment_id: Attachment ID from gmail_fetch_message response
        user_id:       Gmail user ID (use "me" for authenticated user)

    Returns:
        Dict with status and base64url-encoded data field.
        Decode with: base64.urlsafe_b64decode(data["data"] + "==")
    """
    if not message_id:
        return _error_result("gmail_get_attachment", "message_id is required")
    if not attachment_id:
        return _error_result("gmail_get_attachment", "attachment_id is required")

    try:
        service = get_gmail_service()

        att = execute_gmail_api(
            service.users().messages().attachments().get(
                userId=user_id,
                messageId=message_id,
                id=attachment_id,
            )
        )

        data_b64 = att.get("data", "")
        size     = att.get("size", 0)

        if not data_b64:
            return _error_result("gmail_get_attachment", "Empty attachment data returned by Gmail API")

        logger.info(
            "Fetched Gmail attachment",
            message_id=message_id,
            attachment_id=attachment_id,
            size=size,
        )

        return _safe_result("gmail_get_attachment", {
            "message_id":    message_id,
            "attachment_id": attachment_id,
            "size":          size,
            "data":          data_b64,
        })

    except GmailClientError as e:
        logger.error("gmail_get_attachment failed", error=str(e))
        return _error_result("gmail_get_attachment", str(e))
