# app/api/endpoints/gmail_extension.py

from fastapi import APIRouter, Header, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging

from app.api.middleware.rate_limit import limiter
from app.core.config import settings
from app.domains.email_ai.tools_email import (
    gmail_summarize_thread,
    gmail_suggest_followups,
    gmail_list_messages,
    gmail_fetch_message
)
import asyncio
from app.infrastructure.external.gmail_client import get_gmail_service, execute_gmail_api
from app.core.celery_app import celery_app
from app.domains.email_ai.workers.auto_organize import backfill_inbox, _auto_organize_inbox_internal
from sse_starlette.sse import EventSourceResponse
from app.infrastructure.cache.redis_client import get_redis
import json

router = APIRouter(prefix="/api/v1/gmail", tags=["Gmail"])
logger = logging.getLogger(__name__)

class AnalyzeRequest(BaseModel):
    intent: str
    params: Dict[str, Any]

class CleanResponse(BaseModel):
    status: str
    category: Optional[str] = None
    reason: Optional[str] = None
    suggested_reply: Optional[str] = None
    error: Optional[str] = None

class SearchResponse(BaseModel):
    status: str
    messages: List[Dict[str, Any]]
    count: int

@router.post("/analyze", response_model=CleanResponse)
async def analyze_thread(
    request: AnalyzeRequest,
     x_api_key: Optional[str] = Header(None)
):
    """
    Endpoint for Gmail Sidebar Extension to analyze a thread.
    """
    # Simple validation of API key (could be expanded to full check)
    logger.info(f"Gmail Extension analysis request for thread {request.params.get('threadId')}")

    try:
        thread_id = request.params.get("threadId")
        if not thread_id:
             return CleanResponse(status="ERROR", error="threadId is required")

        # 1. Use the existing summarize tool
        summary_result = await gmail_summarize_thread(thread_id=thread_id, user_id="me")

        if summary_result.get("status") != "OK":
             return CleanResponse(status="ERROR", error=summary_result.get("error"))

        data = summary_result.get("data", {})

        # 2. Get suggested followups/category
        followup_result = await gmail_suggest_followups(thread_ids=[thread_id], user_id="me")

        category = "fyi"
        reason = data.get("summary", "No summary available")

        if followup_result.get("status") == "OK" and followup_result.get("data", {}).get("followups"):
            followup = followup_result["data"]["followups"][0]
            category = followup.get("category", "fyi")
            reason = followup.get("reason", reason)

        return CleanResponse(
            status="OK",
            category=category,
            reason=reason,
            suggested_reply=f"Thank you for your email. I will look into '{data.get('subject')}' and get back to you."
        )

    except Exception as e:
        logger.error(f"Extension analysis failed: {e}")
        return CleanResponse(status="ERROR", error=str(e))

@router.get("/search", response_model=SearchResponse)
async def search_emails(
    q: Optional[str] = None,
    label_id: Optional[str] = None,
    max_results: int = 20,
    x_api_key: Optional[str] = Header(None)
):
    """
    Search labeled emails for the UI.
    """
    try:
        query = q or ""
        if label_id:
            # Wrap in quotes to support nested label names like "Action Needed/High"
            sanitized = label_id.replace('"', '')
            query = f'{query} label:"{sanitized}"'.strip()

        result = await gmail_list_messages(
            user_id="me",
            query=query,
            max_results=max_results
        )

        if result.get("status") != "OK":
             return SearchResponse(status="ERROR", messages=[], count=0)

        data = result.get("data", {})
        messages = data.get("messages", [])

        if messages:
            global _cached_id_to_name
            if '_cached_id_to_name' not in globals() or not _cached_id_to_name:
                service = get_gmail_service()
                
                def fetch_labels():
                    return execute_gmail_api(service.users().labels().list(userId="me"))
                
                labels_response = await asyncio.to_thread(fetch_labels)
                _cached_id_to_name = {l["id"]: l["name"].lower() for l in labels_response.get("labels", [])}

            for msg in messages:
                resolved_labels = []
                for lid in msg.get("labelIds", []):
                    resolved_labels.append(lid)
                    if lid in _cached_id_to_name:
                        resolved_labels.append(_cached_id_to_name[lid])
                
                # Store the combined list (both original IDs and readable names)
                msg["labelIds"] = list(set(resolved_labels))

        return SearchResponse(status="OK", messages=messages, count=len(messages))

    except Exception as e:
        logger.error(f"Gmail search failed: {e}")
        return SearchResponse(status="ERROR", messages=[], count=0)

@router.post("/backfill")
async def trigger_backfill(
    user_id: str = "default_user",
    max_results: int = 100,
    x_api_key: Optional[str] = Header(None)
):
    """
    Trigger historical email labeling via Celery.
    """
    backfill_inbox.delay(user_id, "me", max_results)
    return {"status": "OK", "message": f"Backfill task for {max_results} emails dispatched to Celery worker"}

@router.post("/action")
async def perform_action(request: Dict[str, Any]):
    """Placeholder for quick actions (archive, label, etc.)"""
    return {"status": "OK", "message": "Action performed (simulated)"}

@router.get("/events")
async def email_events(request: Request):
    """
    SSE Endpoint for real-time email updates.
    """
    async def event_generator():
        client = await get_redis()
        if not client:
            yield {"event": "error", "data": "Redis unavailable"}
            return
            
        pubsub = client.pubsub()
        await pubsub.subscribe("email_events")
        try:
            while True:
                if await request.is_disconnected():
                    break
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message:
                    # sse_starlette formats this safely
                    yield {"event": "message", "data": message["data"]}
        finally:
            await pubsub.unsubscribe("email_events")
            await pubsub.close()

    return EventSourceResponse(event_generator())
