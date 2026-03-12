"""
agents/sla_agent.py — AG-05: SLA Monitoring Agent
Sprint 9. Celery task — NOT a LangGraph node.

DESIGN (master prompt spec, locked):

  Task name : sla_check_all_open_emails
  Cron      : every 5 minutes (Celery beat)
  No LLM    : pure logic / DB / Redis / Slack

  ST-E5-01  SLA deadline set at AG-01 intake (stored in emails.sla_deadline)
  ST-E5-02  Every 5 min: query all open emails, compute elapsed_pct
  ST-E5-03  At 80% elapsed → Slack alert #sla-alerts
            Dedup  key: sla_alert_sent:{email_id}   TTL = 1800s (30 min)
  ST-E5-04  At 100% breach → reassign to Team Lead + second Slack alert + DM
            Dedup  key: sla_breach_sent:{email_id}  TTL = 3600s (60 min)
  ST-E5-05  Expose SLA elapsed_pct per open email via REST endpoint (Week 5)

  Slack failure → ACTUALLY send email via gmail_send_email (gmail-mcp).
  Only log if gmail-mcp ALSO fails. Never silently skip.

  DB failure   → retry 3x with 1s backoff. Log error, skip cycle.
  Redis failure → skip dedup check (fail-open), fire alert anyway.

Redis key patterns:
  sla_alert_sent:{email_id}   TTL=1800   (30 min — prevents re-alert before next window)
  sla_breach_sent:{email_id}  TTL=3600   (60 min — prevents repeat breach DM)
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
import redis as redis_lib

# Celery app — imported from tasks.celery_app (created in main.py Week 5)
# Circular-import safe: task is registered on the shared app instance.
from celery import shared_task

from config.settings import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Redis client — shared singleton
# ---------------------------------------------------------------------------
def _get_redis() -> redis_lib.Redis:
    """Return a Redis client. Connects to CELERY_BROKER_URL (localhost:6379)."""
    broker_url = getattr(settings, "CELERY_BROKER_URL", "redis://localhost:6379/0")
    return redis_lib.from_url(broker_url, decode_responses=True)


# ---------------------------------------------------------------------------
# Postgres helper (Phase 1: asyncpg wired in Week 3)
# Phase 1: synchronous psycopg2 for Celery worker context
# ---------------------------------------------------------------------------
def _get_open_emails(conn) -> List[Dict[str, Any]]:
    """
    Query all emails that are NOT closed and have an sla_deadline set.
    Returns list of dicts with keys:
      email_id, sla_deadline, created_at, current_assignee,
      tenant_id, case_reference, sender, subject,
      alert_80_sent, escalated
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT
            email_id::text,
            sla_deadline,
            created_at,
            current_assignee,
            tenant_id,
            case_reference,
            sender,
            subject,
            alert_80_sent,
            escalated
        FROM emails
        WHERE current_step NOT IN ('closed', 'archived')
          AND sla_deadline IS NOT NULL
        ORDER BY sla_deadline ASC
    """)
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    cur.close()
    return rows


def _update_email_sla_fields(
    conn,
    email_id:         str,
    elapsed_time:     float,
    alert_80_sent:    bool,
    escalated:        bool,
    current_assignee: Optional[str] = None,
) -> None:
    """Update SLA tracking fields in emails table. Phase 1 synchronous write."""
    cur = conn.cursor()
    if current_assignee:
        cur.execute("""
            UPDATE emails
            SET elapsed_time=$1, alert_80_sent=$2, escalated=$3,
                current_assignee=$4, updated_at=NOW()
            WHERE email_id=$5
        """, (elapsed_time, alert_80_sent, escalated, current_assignee, email_id))
    else:
        cur.execute("""
            UPDATE emails
            SET elapsed_time=$1, alert_80_sent=$2, escalated=$3, updated_at=NOW()
            WHERE email_id=$4
        """, (elapsed_time, alert_80_sent, escalated, email_id))
    conn.commit()
    cur.close()


# ---------------------------------------------------------------------------
# Slack alert helper
# ---------------------------------------------------------------------------
def _send_slack_alert(channel: str, message: str) -> bool:
    """
    POST message to Slack channel via Bot Token.
    Returns True on success, False on failure.
    Rate limit: 1 msg/sec per channel (enforced by Slack — we don't throttle here).
    """
    token = getattr(settings, "SLACK_BOT_TOKEN", None)
    if not token:
        logger.error(json.dumps({"event": "slack_no_token_configured"}))
        return False

    try:
        resp = httpx.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
            },
            json={"channel": channel, "text": message, "mrkdwn": True},
            timeout=10,
        )
        data = resp.json()
        if data.get("ok"):
            logger.info(json.dumps({"event": "slack_alert_sent", "channel": channel}))
            return True
        else:
            logger.error(json.dumps({
                "event":   "slack_alert_failed",
                "channel": channel,
                "error":   data.get("error"),
            }))
            return False
    except Exception as exc:
        logger.error(json.dumps({"event": "slack_alert_exception", "error": str(exc)}))
        return False


def _send_slack_dm(user_id: str, message: str) -> bool:
    """Send a DM to a specific Slack user (Team Lead)."""
    token = getattr(settings, "SLACK_BOT_TOKEN", None)
    if not token or not user_id:
        return False

    try:
        # Open DM channel
        open_resp = httpx.post(
            "https://slack.com/api/conversations.open",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"users": user_id},
            timeout=10,
        )
        channel_id = open_resp.json().get("channel", {}).get("id")
        if not channel_id:
            return False
        return _send_slack_alert(channel_id, message)
    except Exception as exc:
        logger.error(json.dumps({"event": "slack_dm_failed", "error": str(exc)}))
        return False


# ---------------------------------------------------------------------------
# Gmail fallback alert (via existing mcp.py — MANDATORY not optional)
# ---------------------------------------------------------------------------
def _send_gmail_fallback_alert(
    subject: str,
    body:    str,
    to:      Optional[str] = None,
) -> bool:
    """
    Send email alert via email.gmail_send_email (existing mcp.py tool).
    Used ONLY when Slack fails — mandatory per design doc.
    Only log-and-skip if gmail also fails.
    """
    recipient = to or getattr(settings, "TEAM_LEAD_EMAIL", None)
    if not recipient:
        logger.error(json.dumps({
            "event": "gmail_fallback_no_recipient",
            "hint":  "Set TEAM_LEAD_EMAIL in settings",
        }))
        return False

    try:
        import asyncio
        from app.domains.email_ai import tools_email as email_tools
        asyncio.run(
            email_tools.gmail_send_email(
                to=recipient,
                subject=subject,
                body=body,
                thread_id=None,
            )
        )
        logger.info(json.dumps({
            "event":     "gmail_fallback_alert_sent",
            "recipient": recipient,
        }))
        return True
    except Exception as exc:
        # Only log here — both Slack AND gmail failed
        logger.error(json.dumps({
            "event": "gmail_fallback_alert_failed",
            "error": str(exc),
        }))
        return False


def _alert_with_fallback(
    slack_channel: str,
    slack_message: str,
    email_subject: str,
    email_body:    str,
    to:            Optional[str] = None,
) -> None:
    """
    Try Slack first. If Slack fails → send via gmail-mcp. If both fail → log.
    This is the MANDATORY fallback pattern from the design doc.
    """
    slack_ok = _send_slack_alert(slack_channel, slack_message)
    if not slack_ok:
        logger.warning(json.dumps({
            "event":    "slack_failed_trying_gmail_fallback",
            "channel":  slack_channel,
        }))
        gmail_ok = _send_gmail_fallback_alert(email_subject, email_body, to)
        if not gmail_ok:
            logger.error(json.dumps({
                "event":   "both_slack_and_gmail_failed",
                "channel": slack_channel,
                "subject": email_subject,
            }))


# ---------------------------------------------------------------------------
# Redis dedup helpers
# ---------------------------------------------------------------------------
def _is_alert_sent(redis: redis_lib.Redis, email_id: str) -> bool:
    """Check sla_alert_sent:{email_id} in Redis. Returns False if Redis fails (fail-open)."""
    try:
        return bool(redis.exists(f"sla_alert_sent:{email_id}"))
    except Exception as exc:
        logger.warning(json.dumps({"event": "redis_dedup_check_failed", "error": str(exc)}))
        return False  # fail-open: fire alert anyway


def _is_breach_sent(redis: redis_lib.Redis, email_id: str) -> bool:
    """Check sla_breach_sent:{email_id} in Redis."""
    try:
        return bool(redis.exists(f"sla_breach_sent:{email_id}"))
    except Exception as exc:
        logger.warning(json.dumps({"event": "redis_breach_check_failed", "error": str(exc)}))
        return False


def _mark_alert_sent(redis: redis_lib.Redis, email_id: str) -> None:
    """Set sla_alert_sent:{email_id} with TTL=1800s (30 min)."""
    try:
        redis.setex(f"sla_alert_sent:{email_id}", 1800, "1")
    except Exception as exc:
        logger.warning(json.dumps({"event": "redis_mark_alert_failed", "error": str(exc)}))


def _mark_breach_sent(redis: redis_lib.Redis, email_id: str) -> None:
    """Set sla_breach_sent:{email_id} with TTL=3600s (60 min)."""
    try:
        redis.setex(f"sla_breach_sent:{email_id}", 3600, "1")
    except Exception as exc:
        logger.warning(json.dumps({"event": "redis_mark_breach_failed", "error": str(exc)}))


# ---------------------------------------------------------------------------
# Core SLA check logic — called by Celery task
# ---------------------------------------------------------------------------
def _check_email_sla(
    email:  Dict[str, Any],
    redis:  redis_lib.Redis,
    conn,
) -> Dict[str, Any]:
    """
    Evaluate one email's SLA status. Returns a result dict for logging.

    elapsed_pct = (now - created_at) / (sla_deadline - created_at) * 100
    """
    email_id       = str(email["email_id"])
    sla_deadline   = email["sla_deadline"]
    created_at     = email["created_at"]
    assignee       = email.get("current_assignee", "Unassigned")
    case_ref       = email.get("case_reference", email_id[:8])
    sender         = email.get("sender", "unknown")
    subject        = email.get("subject", "(no subject)")
    alert_80_sent  = email.get("alert_80_sent", False)
    escalated      = email.get("escalated", False)

    now        = datetime.now(timezone.utc)

    # Ensure timezone-aware datetimes
    if sla_deadline.tzinfo is None:
        import pytz
        sla_deadline = pytz.utc.localize(sla_deadline)
    if created_at.tzinfo is None:
        import pytz
        created_at = pytz.utc.localize(created_at)

    total_window = (sla_deadline - created_at).total_seconds()
    elapsed_secs = (now - created_at).total_seconds()

    if total_window <= 0:
        return {"email_id": email_id, "skipped": True, "reason": "zero_sla_window"}

    elapsed_pct = (elapsed_secs / total_window) * 100

    result = {
        "email_id":    email_id,
        "elapsed_pct": round(elapsed_pct, 1),
        "action":      "none",
    }

    # ====================================================================
    # ST-E5-04 — 100% SLA BREACH (check first — higher priority)
    # ====================================================================
    if elapsed_pct >= 100 and not _is_breach_sent(redis, email_id):
        breach_msg = (
            f":fire: *SLA BREACH* :fire:\n"
            f"Case: `{case_ref}` | Assignee: {assignee}\n"
            f"From: {sender}\n"
            f"Subject: {subject}\n"
            f"Elapsed: *{round(elapsed_pct, 1)}%* of SLA window\n"
            f"SLA deadline was: {sla_deadline.strftime('%Y-%m-%d %H:%M UTC')}"
        )

        channel = getattr(settings, "SLACK_CHANNEL_SLA_ALERTS", "#sla-alerts")
        _alert_with_fallback(
            slack_channel=channel,
            slack_message=breach_msg,
            email_subject=f"[SLA BREACH] Case {case_ref}",
            email_body=(
                f"SLA breach on case {case_ref}.\n"
                f"Assignee: {assignee}\n"
                f"From: {sender}\n"
                f"Subject: {subject}\n"
                f"Elapsed: {round(elapsed_pct, 1)}% of SLA window\n"
                f"Deadline was: {sla_deadline}"
            ),
        )

        # DM Team Lead
        team_lead_id = getattr(settings, "SLACK_TEAM_LEAD_USER_ID", None)
        if team_lead_id:
            _send_slack_dm(
                user_id=team_lead_id,
                message=(
                    f":fire: SLA Breach — Case `{case_ref}` is past its deadline.\n"
                    f"Reassigning to Team Lead queue. Assignee was: {assignee}"
                ),
            )

        _mark_breach_sent(redis, email_id)

        # Reassign to Team Lead queue
        team_lead_queue = getattr(settings, "TEAM_LEAD_QUEUE", "Team Lead")
        _update_email_sla_fields(
            conn=conn,
            email_id=email_id,
            elapsed_time=elapsed_secs,
            alert_80_sent=True,
            escalated=True,
            current_assignee=team_lead_queue,
        )

        result.update({"action": "breach_escalated", "new_assignee": team_lead_queue})
        logger.warning(json.dumps({
            "event":       "sla_breach",
            "email_id":    email_id,
            "elapsed_pct": round(elapsed_pct, 1),
            "case_ref":    case_ref,
        }))

    # ====================================================================
    # ST-E5-03 — 80% SLA WARNING
    # ====================================================================
    elif elapsed_pct >= 80 and not _is_alert_sent(redis, email_id):
        warning_msg = (
            f":warning: *SLA Warning — 80% Elapsed* :warning:\n"
            f"Case: `{case_ref}` | Assignee: {assignee}\n"
            f"From: {sender}\n"
            f"Subject: {subject}\n"
            f"Elapsed: *{round(elapsed_pct, 1)}%* of SLA window\n"
            f"SLA deadline: {sla_deadline.strftime('%Y-%m-%d %H:%M UTC')}"
        )

        channel = getattr(settings, "SLACK_CHANNEL_SLA_ALERTS", "#sla-alerts")
        _alert_with_fallback(
            slack_channel=channel,
            slack_message=warning_msg,
            email_subject=f"[SLA Warning] Case {case_ref} at {round(elapsed_pct, 1)}%",
            email_body=(
                f"SLA warning: case {case_ref} has used {round(elapsed_pct, 1)}% of its window.\n"
                f"Assignee: {assignee}\n"
                f"Deadline: {sla_deadline}"
            ),
        )

        _mark_alert_sent(redis, email_id)
        _update_email_sla_fields(
            conn=conn,
            email_id=email_id,
            elapsed_time=elapsed_secs,
            alert_80_sent=True,
            escalated=False,
        )

        result.update({"action": "alert_80_sent"})
        logger.info(json.dumps({
            "event":       "sla_80pct_alert",
            "email_id":    email_id,
            "elapsed_pct": round(elapsed_pct, 1),
            "case_ref":    case_ref,
        }))

    else:
        # Just update elapsed_time
        _update_email_sla_fields(
            conn=conn,
            email_id=email_id,
            elapsed_time=elapsed_secs,
            alert_80_sent=alert_80_sent,
            escalated=escalated,
        )
        result["action"] = "elapsed_updated"

    return result


# ---------------------------------------------------------------------------
# Celery Task — ST-E5-02
# ---------------------------------------------------------------------------
@shared_task(
    name="sla_check_all_open_emails",   # locked name from spec
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,                     # re-queue on worker crash
)
def sla_check_all_open_emails(self) -> Dict[str, Any]:
    """
    Celery beat task: runs every 5 minutes.
    Queries all open emails, evaluates SLA status, fires alerts as needed.

    Returns summary dict logged by Celery.
    """
    run_start = time.monotonic()
    logger.info(json.dumps({"event": "sla_check_started", "at": datetime.now(timezone.utc).isoformat()}))

    # --- Postgres connection (Phase 1: psycopg2 sync for Celery context) ---
    import psycopg2
    import psycopg2.extras

    db_url = getattr(settings, "DATABASE_URL", "")
    # Convert asyncpg URL to psycopg2 format
    pg_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    conn = None
    for attempt in range(1, 4):
        try:
            conn = psycopg2.connect(pg_url, cursor_factory=psycopg2.extras.RealDictCursor)
            break
        except Exception as exc:
            logger.error(json.dumps({
                "event":   "sla_db_connect_failed",
                "attempt": attempt,
                "error":   str(exc),
            }))
            if attempt < 3:
                time.sleep(1)
            else:
                # DB down — skip this cycle, don't block
                logger.error(json.dumps({"event": "sla_check_aborted_no_db"}))
                raise self.retry(exc=exc, countdown=60)

    try:
        redis = _get_redis()
        emails = _get_open_emails(conn)

        summary = {
            "total_open":      len(emails),
            "alerts_80":       0,
            "breaches":        0,
            "elapsed_updated": 0,
            "errors":          0,
        }

        for email in emails:
            try:
                result = _check_email_sla(email, redis, conn)
                action = result.get("action", "none")
                if action == "alert_80_sent":
                    summary["alerts_80"] += 1
                elif action == "breach_escalated":
                    summary["breaches"] += 1
                elif action == "elapsed_updated":
                    summary["elapsed_updated"] += 1
            except Exception as exc:
                summary["errors"] += 1
                logger.error(json.dumps({
                    "event":    "sla_email_check_error",
                    "email_id": str(email.get("email_id")),
                    "error":    str(exc),
                }))
                
        # --- FIX 2: ST-E5-05 Redis dashboard snapshot ---
        try:
            # We need to construct the dataset for the dashboard.
            # We already have `emails` and we just evaluated them.
            # To get accurate `elapsed_pct` and `status` without repeating all logic:
            
            dashboard_data = []
            now = datetime.now(timezone.utc)
            
            for e in emails:
                sla_deadline = e["sla_deadline"]
                created_at   = e["created_at"]
                
                if sla_deadline.tzinfo is None:
                    import pytz
                    sla_deadline = pytz.utc.localize(sla_deadline)
                if created_at.tzinfo is None:
                    import pytz
                    created_at = pytz.utc.localize(created_at)

                total_window = (sla_deadline - created_at).total_seconds()
                elapsed_secs = (now - created_at).total_seconds()
                
                pct = 0.0
                if total_window > 0:
                    pct = (elapsed_secs / total_window) * 100
                
                status = "safe"
                if pct >= 100:
                    status = "breach"
                elif pct >= 80:
                    status = "at_risk"
                    
                dashboard_data.append({
                    "email_id":         str(e["email_id"]),
                    "elapsed_pct":      round(pct, 1),
                    "current_assignee": e.get("current_assignee"),
                    "sla_deadline":     sla_deadline.isoformat(),
                    "priority":         e.get("priority"),
                    "tenant_id":        e.get("tenant_id"),
                    "status":           status
                })

            redis.setex(
                "sla_dashboard_snapshot",
                360,
                json.dumps(dashboard_data)
            )
        except Exception as exc:
            logger.warning(json.dumps({"event": "redis_dashboard_snapshot_failed", "error": str(exc)}))

        elapsed_ms = round((time.monotonic() - run_start) * 1000)
        summary["elapsed_ms"] = elapsed_ms

        logger.info(json.dumps({"event": "sla_check_completed", **summary}))
        return summary

    finally:
        if conn:
            conn.close()


# ---------------------------------------------------------------------------
# Celery beat schedule helper — imported by main.py/celery_app.py
# ---------------------------------------------------------------------------
SLA_CELERY_BEAT_SCHEDULE = {
    "sla-check-every-5min": {
        "task":     "sla_check_all_open_emails",
        "schedule": 300.0,   # 300 seconds = 5 minutes exactly (locked)
    },
}
