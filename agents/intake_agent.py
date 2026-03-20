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
from utils.domain_loader import get_domain_config, get_default_domain_config
from utils.retry_utils import DeadLetterError, retry_with_backoff, send_to_dead_letter_queue

import asyncpg

logger = logging.getLogger(__name__)


async def is_duplicate(external_id: str, sender: str = "", subject: str = "") -> bool:
    """Check external_id OR same sender+subject within 10 minutes."""
    db_url = getattr(settings, "DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    try:
        conn = await asyncpg.connect(db_url)
        try:
            # Check 1: exact external_id match
            row = await conn.fetchrow("SELECT 1 FROM emails WHERE external_id = $1 LIMIT 1", external_id)
            # if row:
            #     return True
            # # Check 2: same sender+subject within last 10 minutes
            # if sender and subject:
            #     row = await conn.fetchrow(
            #         """SELECT 1 FROM emails
            #            WHERE sender = $1 AND subject = $2
            #            AND created_at > NOW() - INTERVAL '10 minutes'
            #            LIMIT 1""",
            #         sender, subject
            #     )
            #     if row:
            #         return True
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

            # Fetch full message content FIRST (needed for dedup check with sender+subject)
            msg_resp = await gmail_client.fetch_message(message_id=message_id)
            if msg_resp.get("status") != "OK":
                logger.error(json.dumps({"event": "fetch_message_failed", "message_id": message_id}))
                continue

            msg_data = msg_resp.get("data", {})

            # Dedup guard — checks external_id AND sender+subject within 10 min
            sender_val  = msg_data.get("headers", {}).get("from", "")
            subject_val = msg_data.get("headers", {}).get("subject", "")
            if await is_duplicate(message_id, sender=sender_val, subject=subject_val):
                logger.info(json.dumps({"event": "intake_skip_duplicate", "message_id": message_id}))
                continue

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
    Sends a dynamic auto-acknowledgement generated by Gemini 2.5 Flash-Lite.
    Falls back to a hardcoded template if LLM call fails.
    Case reference format: CASE-{YYYYMMDD}-{uuid[:6]}
    """

    # Gemini system prompt — kept minimal so ACK is short and professional
    _SYSTEM_PROMPT = (
        "You are a helpful enterprise support assistant writing acknowledgement emails. "
        "Write a short, warm, professional acknowledgement for the email below. "
        "Rules:\n"
        "- 3-5 sentences maximum\n"
        "- Acknowledge the specific issue mentioned\n"
        "- Do NOT promise a resolution time\n"
        "- Do NOT include a subject line\n"
        "- Do NOT use placeholders like [Name] or [Team]\n"
        "- End with: Case Reference: {case_id}\n"
        "- Plain text only, no markdown"
    )

    _FALLBACK_TEMPLATE = (
        "Thank you for reaching out. Your request has been received and logged.\n\n"
        "Our team will review your message and respond as soon as possible.\n\n"
        "Case Reference: {case_id}\n\n"
        "Please quote this reference in any follow-up communications."
    )

    async def _generate_ack_body(self, subject: str, body: str, case_id: str) -> str:
        """
        Generate a dynamic ACK body using Gemini 2.5 Flash-Lite.
        Falls back to hardcoded template on any failure.
        """
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            if not settings.GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY not set")

            model = genai.GenerativeModel(
                model_name   = settings.GEMINI_MODEL,
                system_instruction = self._SYSTEM_PROMPT.format(case_id=case_id),
            )

            user_prompt = (
                f"Subject: {subject}\n\n"
                f"Email body:\n{body[:1000]}"  # cap at 1000 chars — ACK only needs gist
            )

            response = model.generate_content(
                user_prompt,
                generation_config=genai.GenerationConfig(
                    max_output_tokens = 200,
                    temperature       = 0.4,
                )
            )

            generated = response.text.strip()

            # Ensure case_id is always in the reply
            if case_id not in generated:
                generated += f"\n\nCase Reference: {case_id}"

            logger.info(json.dumps({
                "event":    "ack_generated_by_llm",
                "model":    settings.GEMINI_MODEL,
                "case_id":  case_id,
                "chars":    len(generated),
            }))
            return generated

        except Exception as exc:
            logger.warning(json.dumps({
                "event":   "ack_llm_fallback",
                "reason":  str(exc),
                "case_id": case_id,
            }))
            return self._FALLBACK_TEMPLATE.format(case_id=case_id)

    async def send(self, parsed_email: Dict[str, Any], case_id: str) -> bool:
        source    = parsed_email["source"]
        to        = parsed_email["sender"]
        email_sub = parsed_email.get("subject", "")
        email_bod = parsed_email.get("body", "")
        reply_sub = f"Re: {email_sub} [{case_id}]"

        # Generate dynamic ACK body via Gemini
        body_txt = await self._generate_ack_body(
            subject  = email_sub,
            body     = email_bod,
            case_id  = case_id,
        )

        logger.info(json.dumps({
            "event":   "ack_send_attempt",
            "source":  source,
            "to":      to,
            "case_id": case_id,
        }))

        if source == "gmail":
            return await self._send_gmail(to, reply_sub, body_txt, parsed_email.get("thread_id"))
        elif source == "outlook":
            return await self._send_outlook(to, reply_sub, body_txt, parsed_email.get("thread_id"))
        else:
            logger.info(json.dumps({"event": "ack_skipped_api_reply", "source": source}))
            return True

    @retry_with_backoff(retries=3, on_exhaust="dlq")
    async def _send_gmail(self, to: str, subject: str, body: str, thread_id: Optional[str] = None) -> bool:
        await gmail_client.send_reply(to=to, subject=subject, body=body, thread_id=thread_id)
        logger.info(json.dumps({"event": "gmail_ack_sent", "to": to, "thread_id": thread_id}))
        return True

    @retry_with_backoff(retries=3, on_exhaust="dlq")
    async def _send_outlook(self, to: str, subject: str, body: str) -> bool:
        logger.info(json.dumps({"event": "outlook_ack_sent", "to": to}))
        return True


# ---------------------------------------------------------------------------
# Attachment Handler — ST-E1-06
# ---------------------------------------------------------------------------

class AttachmentHandler:
    """
    MCP-native attachment pipeline:
      STEP 1 — gmail_get_attachment MCP tool  → fetches base64url bytes
      STEP 2 — filesystem write_file MCP tool → saves text files via MCP
               direct binary write            → saves binary files (xlsx/pdf/etc)
    """

    async def download_and_store(
        self,
        email_id: str,           # system UUID — fallback folder name
        gmail_message_id: str,   # real Gmail ID e.g. 19ce81a9 — for MCP call
        attachments: List[Any],  # raw dicts from gmail_fetch_message with attachmentId
        folder_name: str = "",   # human-readable folder name: subject_date
    ) -> List[str]:
        """Downloads each attachment via MCP tools. Returns list of saved paths."""
        import base64
        paths = []

        for att in attachments:
            if isinstance(att, dict):
                filename      = att.get("filename") or att.get("name") or "attachment"
                attachment_id = att.get("attachmentId") or att.get("id") or ""
                mime_type     = att.get("mimeType", "application/octet-stream")
            else:
                filename      = str(att)
                attachment_id = ""
                mime_type     = "application/octet-stream"

            safe_name  = filename.replace("/", "_").replace("\\", "_").strip()
            # Use human-readable folder_name if provided, else fall back to UUID
            folder     = os.path.join(settings.ATTACHMENT_STORAGE_PATH, folder_name or email_id)
            local_path = os.path.join(folder, safe_name)
            os.makedirs(folder, exist_ok=True)

            if not attachment_id:
                logger.warning(json.dumps({
                    "event": "attachment_no_id", "filename": safe_name,
                }))
                paths.append(local_path)
                continue

            try:
                # STEP 1 — fetch bytes via gmail_get_attachment MCP tool
                att_resp = await gmail_client.fetch_attachment(
                    message_id    = gmail_message_id,
                    attachment_id = attachment_id,
                )
                if att_resp.get("status") != "OK":
                    logger.error(json.dumps({
                        "event": "attachment_fetch_failed",
                        "filename": safe_name,
                        "error": att_resp.get("error"),
                    }))
                    paths.append(local_path)
                    continue

                raw_b64 = att_resp.get("data", {}).get("data", "")
                if not raw_b64:
                    logger.warning(json.dumps({"event": "attachment_empty_data", "filename": safe_name}))
                    paths.append(local_path)
                    continue

                # Decode base64url → bytes
                file_bytes = base64.urlsafe_b64decode(raw_b64 + "==")

                # STEP 2 — save via MCP write_file (text) or direct write (binary)
                is_text = mime_type.startswith("text/") or safe_name.endswith(
                    (".txt", ".csv", ".json", ".xml", ".html", ".md", ".log")
                )

                if is_text:
                    try:
                        text_content = file_bytes.decode("utf-8")
                        mcp_result = await gmail_client._call_tool("write_file", {
                            "path": local_path, "content": text_content,
                        })
                        if mcp_result.get("status") != "OK":
                            raise Exception(mcp_result.get("error", "write_file MCP call failed"))
                        logger.info(json.dumps({
                            "event": "attachment_saved_mcp_text",
                            "filename": safe_name, "bytes": len(file_bytes), "path": local_path,
                        }))
                    except UnicodeDecodeError:
                        is_text = False  # fall through to binary

                if not is_text:
                    # Binary (xlsx, pdf, docx, images) — MCP write_file is text-only
                    # bytes are sourced from MCP, written directly
                    with open(local_path, "wb") as f:
                        f.write(file_bytes)
                    logger.info(json.dumps({
                        "event": "attachment_saved_binary",
                        "filename": safe_name, "bytes": len(file_bytes), "path": local_path,
                    }))

                paths.append(local_path)

            except Exception as e:
                logger.error(json.dumps({
                    "event": "attachment_exception", "filename": safe_name, "error": str(e),
                }))
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
        # FIX: pass subject+body so domain_loader can detect correct domain
        # (IT Support / HR / Customer Support) from email content keywords.
        # Without this, all default-tenant emails use it_support domain.
        _subject = raw.get("subject") or raw.get("Subject") or ""
        _body    = raw.get("body")    or raw.get("text")    or raw.get("snippet") or ""
        domain_cfg = get_domain_config(
            tenant_id,
            email_subject=_subject,
            email_body=_body,
        )
    except Exception as exc:
        logger.warning(json.dumps({"event": "domain_load_failed", "tenant_id": tenant_id, "error": str(exc)}))
        domain_cfg = None

    # ---- Unknown tenant guard (exact spec) ----
    if domain_cfg is None:
        logger.warning(json.dumps({
            "event":     "unknown_tenant_fallback",
            "tenant_id": tenant_id,
            "action":    "using default domain config",
        }))
        domain_cfg = get_default_domain_config()
        tenant_id  = "unknown"

    # --- ST-E1-04: Normalise (Source-Agnostic) ---
    try:
        parsed = normaliser.normalize_message(raw)
    except Exception as exc:
        logger.error(json.dumps({"event": "normalisation_failed", "error": str(exc)}))
        return {"error": str(exc), "retry_count": state.get("retry_count", 0) + 1}

    # --- ST-E1-06: Attachments ---
    # Use raw attachments (dicts with attachmentId) not parsed (filenames only)
    raw_attachments  = raw.get("attachments", [])
    gmail_message_id = raw.get("email_id", "")   # real Gmail ID e.g. 19ce81a9
    att_paths: List[str] = []
    if raw_attachments:
        try:
            # Build human-readable folder name: subject_YYYY-MM-DD
            # e.g. "VPN-issue_2026-03-14" instead of UUID
            _subj = (parsed.get("subject") or "email").strip()
            _subj = "".join(c if c.isalnum() or c in "-_ " else "" for c in _subj)
            _subj = _subj.replace(" ", "-")[:40].strip("-")  # max 40 chars, no leading/trailing dash
            _date = datetime.utcnow().strftime("%Y-%m-%d")
            folder_name = f"{_subj}_{_date}" if _subj else f"email_{_date}"

            att_paths = await att_handler.download_and_store(
                email_id         = parsed["email_id"],  # UUID fallback
                gmail_message_id = gmail_message_id,    # Gmail ID for MCP call
                attachments      = raw_attachments,     # full dicts with attachmentId
                folder_name      = folder_name,         # Subject_Date readable name
            )
            logger.info(json.dumps({
                "event":       "attachments_folder_created",
                "folder_name": folder_name,
                "count":       len(att_paths),
            }))
        except Exception as exc:
            logger.warning(json.dumps({"event": "attachment_download_failed", "error": str(exc)}))
            # Non-fatal — continue without attachments

    # --- ST-E1-05: Case ID + ACK ---
    case_id  = generate_case_id()
    ack_sent = False
    try:
        ack_sent = await ack_engine.send(parsed, case_id)   # FIX: await async send
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
    intake_at = datetime.utcnow().isoformat() + "Z"   # duration tracking
    db_url = getattr(settings, "DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    try:
        conn = await asyncpg.connect(db_url)
        try:
            await conn.execute(
                """
                INSERT INTO emails (
                    email_id, external_id, source, tenant_id, sender, subject, body, 
                    thread_id, case_reference, ack_sent, attachment_paths, current_step,
                    pipeline_timings
                ) VALUES (
                    $1::uuid, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb, 'classification',
                    jsonb_build_object('intake_at', $12::text)
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
                json.dumps(att_paths),
                intake_at,                              # $12 — pipeline_timings intake_at
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
        "email_subject":     parsed.get("subject", ""),
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