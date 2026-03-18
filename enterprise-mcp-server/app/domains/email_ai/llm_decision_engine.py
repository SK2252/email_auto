"""
LLM Decision Engine — Unified Email Classification.

Single Groq API call that returns structured JSON with:
  - intent      : one-sentence description of what the sender wants
  - category    : awaiting_reply | follow_up | action_needed
  - priority    : high | medium | low
  - department  : legal | finance | hr | sales | engineering | operations | executive | general
  - routing_hint: why this department was chosen

Replaces the legacy grok_classify_email() which only returned category.
Falls back to rule-based classification if LLM fails.
"""

import json
import logging
from typing import Optional

from groq import Groq
from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt Templates
# ---------------------------------------------------------------------------

CLASSIFICATION_SYSTEM_PROMPT = """
You are an expert enterprise email triage assistant.
Analyze the email and return a structured JSON classification.

CATEGORY OPTIONS:
  - awaiting_reply   : Professional conversations awaiting our response
  - follow_up        : Items to revisit later; not immediately urgent
  - action_needed    : Requires immediate action, approval, or a specific task

PRIORITY RULES:
  - high   : C-suite sender, legal/financial risk, SLA deadline < 24h, words like "urgent/ASAP/critical"
  - medium : Internal colleague, project update, scheduled meeting, response needed within 3 days
  - low    : Newsletters, FYI threads, no explicit action, automated notifications

DEPARTMENT ROUTING HINTS:
  - legal, finance, hr, sales, engineering, operations, executive, general

Return ONLY valid JSON. No markdown, no explanation:
{
  "intent":        "<one-sentence description of what the sender wants>",
  "category":      "awaiting_reply | follow_up | action_needed",
  "priority":      "high | medium | low",
  "department":    "<department name>",
  "routing_hint":  "<why you chose this department>"
}
"""

USER_PROMPT_TEMPLATE = """
From: {sender}
Subject: {subject}
Date: {date}
Thread length: {message_count} message(s)

Email body:
{body}
"""

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

VALID_CATEGORIES = {"awaiting_reply", "follow_up", "action_needed"}
VALID_PRIORITIES = {"high", "medium", "low"}
VALID_DEPARTMENTS = {
    "legal", "finance", "hr", "sales",
    "engineering", "operations", "executive", "general",
}


def _validate_llm_result(result: dict) -> None:
    """Raise ValueError if LLM output is malformed."""
    if result.get("category") not in VALID_CATEGORIES:
        raise ValueError(f"Invalid category: {result.get('category')}")
    if result.get("priority") not in VALID_PRIORITIES:
        raise ValueError(f"Invalid priority: {result.get('priority')}")


# ---------------------------------------------------------------------------
# Rule-Based Fallback
# ---------------------------------------------------------------------------

def _rule_based_fallback(subject: str, body: str) -> dict:
    """Keyword-based classification used when LLM fails."""
    text = (subject + " " + body).lower()

    # Priority detection
    if any(k in text for k in ["urgent", "asap", "critical", "immediately", "deadline"]):
        priority = "high"
    elif any(k in text for k in ["newsletter", "unsubscribe", "promotion", "no-reply"]):
        priority = "low"
    else:
        priority = "medium"

    # Category detection
    if any(k in text for k in ["action required", "please approve", "urgent", "asap", "sign off"]):
        category = "action_needed"
    elif any(k in text for k in ["newsletter", "unsubscribe", "fyi", "no action"]):
        category = "follow_up"
    else:
        category = "awaiting_reply"

    # Department detection
    department = "general"
    if any(k in text for k in ["invoice", "payment", "budget", "finance", "accounting"]):
        department = "finance"
    elif any(k in text for k in ["contract", "legal", "lawsuit", "compliance"]):
        department = "legal"
    elif any(k in text for k in ["hr", "onboarding", "payroll", "leave", "hiring"]):
        department = "hr"
    elif any(k in text for k in ["sales", "deal", "proposal", "client", "revenue"]):
        department = "sales"
    elif any(k in text for k in ["bug", "deploy", "server", "api", "engineering", "code"]):
        department = "engineering"

    return {
        "intent": "Classified by rule-based fallback",
        "category": category,
        "priority": priority,
        "department": department,
        "routing_hint": "Fallback: keyword-based classification (LLM unavailable)",
    }


# ---------------------------------------------------------------------------
# Main Classification Function
# ---------------------------------------------------------------------------

async def classify_email_full(
    sender: str,
    subject: str,
    body: str,
    date: str = "",
    message_count: int = 1,
) -> dict:
    """
    Single LLM call returning all classification dimensions.

    Args:
        sender:        Email sender address/name
        subject:       Email subject line
        body:          Email body text (truncated to 3000 chars)
        date:          Email date string
        message_count: Number of messages in the thread

    Returns:
        Dict with keys: intent, category, priority, department, routing_hint
        Falls back to rule-based if LLM fails.
    """
    user_prompt = USER_PROMPT_TEMPLATE.format(
        sender=sender,
        subject=subject,
        body=body[:3000],
        date=date,
        message_count=message_count,
    )

    try:
        client = Groq(api_key=settings.grok_api_key)
        completion = client.chat.completions.create(
            model=settings.grok_model,
            messages=[
                {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=200,
            response_format={"type": "json_object"},
        )

        raw = completion.choices[0].message.content
        result = json.loads(raw)
        _validate_llm_result(result)

        # Normalise department to known values
        dept = result.get("department", "general").lower()
        result["department"] = dept if dept in VALID_DEPARTMENTS else "general"

        logger.info(
            "llm_classification_success",
            extra={
                "category": result["category"],
                "priority": result["priority"],
                "department": result["department"],
            },
        )
        return result

    except Exception as e:
        logger.error(
            "llm_classification_failed",
            extra={"error": str(e), "fallback_used": True},
        )
        return _rule_based_fallback(subject, body)
