"""
agents/intake_agent.py — AG-01: Intake Agent
Sprint 1 focus: Gmail polling + Outlook delta + schema normalization + auto-ACK.
Gmail OAuth is DONE. Graph auth is IN PROGRESS.
This module starts from ST-E1-01 (polling loop), NOT from OAuth setup.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from config.settings import settings
from state.shared_state import AgentState
from mcp_tools.gmail_client import gmail_client
from utils.case_id_generator import generate_case_id
from utils.domain_loader import get_domain_config
from utils.retry_utils import DeadLetterError, retry_with_backoff, send_to_dead_letter_queue

import asyncpg

logger = logging.getLogger(__name__)


async def is_duplicate(external_id: str) -> bool:
    """Check if an email with this external_id already exists in the database."""
    db_url = getattr(settings, "DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    try:
        conn = await asyncpg.connect(db_url)
        try:
            row = await conn.fetchrow("SELECT 1 FROM emails WHERE external_id = $1 LIMIT 1", external_id)
            return row is not None
        finally:
            await conn.close()
    except Exception as e:
        logger.error(json.dumps({"event": "dedup_check_failed", "external_id": external_id, "error": str(e)}))
        return False


async def poll_and_ingest():
    """ST-E1-01: Real polling loop for Gmail."""
    from agents.orchestrator import run_pipeline

    logger.info(json.dumps({"event": "gmail_poll_started"}))
    try:
        result = await gmail_client.poll_inbox()
        if result.get("status") != "OK":
            logger.error(json.dumps({"event": "gmail_poll_failed", "error": result.get("error")}))
            return

        threads = result.get("data", {}).get("threads", [])
        for thread_meta in threads:
            thread_id = thread_meta["thread_id"]

            # Fetch full thread to get messages
            thread_resp = await gmail_client.fetch_thread(thread_id=thread_id)
            messages = thread_resp.get("data", {}).get("messages", [])
            if not messages:
                continue

            # Take the LAST message in the thread
            last_message = messages[-1]
            message_id = last_message.get("id")

            if not message_id:
                logger.error(json.dumps({"event": "intake_no_message_id", "thread_id": thread_id}))
                continue

            # Dedup guard
            if await is_duplicate(message_id):
                logger.info(json.dumps({"event": "intake_skip_duplicate", "message_id": message_id}))
                continue

            # Fetch full message content
            msg_resp = await gmail_client.fetch_message(message_id=message_id)
            if msg_resp.get("status") != "OK":
                logger.error(json.dumps({"event": "fetch_message_failed", "message_id": message_id}))
                continue

            msg_data = msg_resp.get("data", {})

            # Normalized raw_email structure for LangGraph state
            raw_email = {
                "email_id":    msg_data.get("id"),
                "thread_id":   msg_data.get("threadId"),
                "sender":      msg_data.get("headers", {}).get("from"),
                "recipient":   msg_data.get("headers", {}).get("to"),
                "subject":     msg_data.get("headers", {}).get("subject"),
                "received_at": msg_data.get("headers", {}).get("date"),
                "body":        msg_data.get("body"),
                "attachments": msg_data.get("attachments", []),
                "label_ids":   msg_data.get("labelIds", []),
                "truncated":   msg_data.get("bodyTruncated", False),
                "source":      "gmail"
            }

            logger.info(json.dumps({"event": "ingesting_message", "message_id": message_id, "thread_id": thread_id}))
            # Trigger LangGraph orchestrator
            await run_pipeline(raw_email, source="gmail")

    except Exception as e:
        logger.error(json.dumps({"event": "poll_loop_exception", "error": str(e)}))


# ---------------------------------------------------------------------------
# Normaliser: converts raw Gmail/Outlook/Zendesk/Freshdesk payloads
# into a single canonical EmailSchema dict.
# ---------------------------------------------------------------------------

class EmailNormaliser:
    """
    ST-E1-04 — Normalise any source email to a unified schema.
    Schema: {email_id, source, sender, subject, body, timestamp,
             attachments: List[str], thread_id}
    """

    def normalize_message(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        ST-E1-04 — Map normalized raw_email (from client) to system canonical parsed email.
        """
        import uuid
        return {
            "email_id":     str(uuid.uuid4()),
            "external_id":  raw.get("email_id") or raw.get("external_id") or str(uuid.uuid4()),
            "source":       raw.get("source", "gmail"),
            "sender":       raw.get("sender", "unknown"),
            "subject":      raw.get("subject", ""),
            "body":         raw.get("body", ""),
            "received_at":  raw.get("received_at") or datetime.utcnow().isoformat(),
            "attachments":  [a.get("filename") if isinstance(a, dict) else a for a in raw.get("attachments", [])],
            "thread_id":    raw.get("thread_id", ""),
        }


# ---------------------------------------------------------------------------
# ACK Engine — ST-E1-05
# ---------------------------------------------------------------------------

class AckEngine:
    """
    Sends an auto-acknowledgement via the same channel the email came from.
    Case reference format: CASE-{YYYYMMDD}-{uuid[:6]}
    """

    def send(self, parsed_email: Dict[str, Any], case_id: str) -> bool:
        source   = parsed_email["source"]
        to       = parsed_email["sender"]
        subject  = f"Re: {parsed_email['subject']} [{case_id}]"
        body_txt = (
            f"Thank you for reaching out. Your case has been logged.\n"
            f"Case Reference: {case_id}\n\n"
            f"Our team will respond within the SLA window. Please quote the case "
            f"reference in any follow-up communications."
        )
        logger.info(json.dumps({"event": "ack_send_attempt", "source": source, "to": to, "case_id": case_id}))

        if source == "gmail":
            return self._send_gmail(to, subject, body_txt, parsed_email.get("thread_id"))
        elif source == "outlook":
            return self._send_outlook(to, subject, body_txt, parsed_email.get("thread_id"))
        else:
            # Zendesk / Freshdesk have their own reply APIs — stub for Sprint 1
            logger.info(json.dumps({"event": "ack_skipped_api_reply", "source": source}))
            return True

    @retry_with_backoff(retries=3, on_exhaust="dlq")
    def _send_gmail(self, to: str, subject: str, body: str, thread_id: Optional[str] = None) -> bool:
        """Step 3: Real ACK via GmailClient."""
        import asyncio
        asyncio.run(gmail_client.send_reply(to=to, subject=subject, body=body, thread_id=thread_id))
        logger.info(json.dumps({"event": "gmail_ack_sent", "to": to, "thread_id": thread_id}))
        return True

    @retry_with_backoff(retries=3, on_exhaust="dlq")
    def _send_outlook(self, to: str, subject: str, body: str) -> bool:
        # Graph API: POST /me/sendMail with JSON body
        logger.info(json.dumps({"event": "outlook_ack_sent", "to": to}))
        return True


# ---------------------------------------------------------------------------
# Attachment Handler — ST-E1-06
# ---------------------------------------------------------------------------

class AttachmentHandler:
    """
    Downloads and stores attachments to the configured storage path.
    filesystem-mcp / Azure Blob stub.
    """

    def download_and_store(self, email_id: str, attachment_names: List[str]) -> List[str]:
        """Returns list of storage paths."""
        paths = []
        for name in attachment_names:
            safe_name = name.replace("/", "_")
            local_path = os.path.join(settings.ATTACHMENT_STORAGE_PATH, email_id, safe_name)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            # In production: download via Gmail API / Graph /attachments, write bytes
            logger.info(json.dumps({"event": "attachment_stored", "path": local_path}))
            paths.append(local_path)
        return paths


# ---------------------------------------------------------------------------
# AG-01: Intake Agent Node
# ---------------------------------------------------------------------------

normaliser = EmailNormaliser()
ack_engine  = AckEngine()
att_handler = AttachmentHandler()


async def intake_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node function for AG-01.
    Receives raw_email + source tag in state; returns parsed_email,
    attachment_paths, ack_sent, case_reference, domain_config, and
    initial event_queue entry.
    """
    raw = state.get("raw_email") or {}
    logger.info(json.dumps({"event": "intake_started", "external_id": raw.get("email_id", "unknown")}))

    # ---- Load domain config for this tenant (injected for all downstream agents) ----
    tenant_id = raw.get("tenant_id") or state.get("tenant_id") or "default"
    try:
        domain_cfg = get_domain_config(tenant_id)
    except Exception as exc:
        logger.warning(json.dumps({"event": "domain_load_failed", "tenant_id": tenant_id, "error": str(exc)}))
        domain_cfg = None

    # --- ST-E1-04: Normalise (Source-Agnostic) ---
    try:
        parsed = normaliser.normalize_message(raw)
    except Exception as exc:
        logger.error(json.dumps({"event": "normalisation_failed", "error": str(exc)}))
        return {"error": str(exc), "retry_count": state.get("retry_count", 0) + 1}

    # --- ST-E1-06: Attachments ---
    att_filenames = parsed.get("attachments", [])
    att_paths: List[str] = []
    if att_filenames:
        try:
            att_paths = att_handler.download_and_store(parsed["email_id"], att_filenames)
        except Exception as exc:
            logger.warning(json.dumps({"event": "attachment_download_failed", "error": str(exc)}))
            # Non-fatal — continue without attachments

    # --- ST-E1-05: Case ID + ACK ---
    case_id  = generate_case_id()
    ack_sent = False
    try:
        ack_sent = ack_engine.send(parsed, case_id)
    except DeadLetterError as exc:
        # ACK failure goes to DLQ + Slack alert, does NOT block ingestion
        send_to_dead_letter_queue({"case_id": case_id, "email_id": parsed["email_id"]}, str(exc))

    # --- ST-E1-07: Audit event ---
    audit_event = {
        "type":      "email_ingested",
        "agent_id":  "AG-01",
        "email_id":  parsed["email_id"],
        "timestamp": datetime.utcnow().isoformat(),
        "payload": {
            "source":          parsed["source"],
            "sender":          parsed["sender"],
            "case_reference":  case_id,
            "attachment_count": len(att_paths),
        },
    }

    # --- Phase 5: INSERT to PostgreSQL emails table ---
    db_url = getattr(settings, "DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    try:
        conn = await asyncpg.connect(db_url)
        try:
            await conn.execute(
                """
                INSERT INTO emails (
                    email_id, external_id, source, tenant_id, sender, subject, body, 
                    thread_id, case_reference, ack_sent, attachment_paths, current_step
                ) VALUES (
                    $1::uuid, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb, 'classification'
                )
                """,
                parsed["email_id"],
                parsed.get("external_id", parsed["email_id"]),
                parsed["source"],
                tenant_id if tenant_id != "default" else None,
                parsed["sender"],
                parsed["subject"],
                parsed["body"],
                parsed["thread_id"],
                case_id,
                ack_sent,
                json.dumps(att_paths)
            )
        finally:
            await conn.close()
    except Exception as exc:
        logger.error(json.dumps({"event": "db_insert_failed", "error": str(exc), "email_id": parsed["email_id"]}))

    logger.info(json.dumps({"event": "intake_completed", "case_reference": case_id}))

    return {
        "raw_email":         raw,
        "parsed_email":      parsed,
        "email_id":          parsed["email_id"], # pass system ID downstream
        "email_text":        parsed.get("body", ""),
        "attachment_paths":  att_paths,
        "ack_sent":          ack_sent,
        "case_reference":    case_id,
        "tenant_id":         tenant_id,
        "domain_config":     domain_cfg,
        "current_step":      "classification",
        "agent_statuses":    {**state.get("agent_statuses", {}), "AG-01": "completed"},
        "event_queue":       [audit_event],
        "error":             None,
    }
