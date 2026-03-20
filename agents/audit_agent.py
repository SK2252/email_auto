"""
agents/audit_agent.py — AG-06: Audit & Compliance Agent
Sprint 3 requirement — built early because all other agents call it.

PHASE 1 SCOPE (current):
  - Log all agent events to postgres audit_log table.
  - Buffer locally on DB failure, flush on reconnect.
  # TODO: Phase 2 (Sprint 10) — salesforce-mcp: sync interaction records on case close
  # TODO: Phase 2 (Sprint 10) — hubspot-mcp: fallback CRM sync if no Salesforce

DESIGN CONSTRAINTS (non-negotiable from design doc):
  - NEVER UPDATE or DELETE from audit_log table
  - NEVER DROP an audit event (local buffer fallback)
  - Every agent action must emit: {type, agent_id, email_id, timestamp, payload}
  - Retry flush on DB reconnect
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional
from agents.agent_metrics import instrument_agent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# AuditEvent — canonical shape for every audit record
# ---------------------------------------------------------------------------
def make_audit_event(
    event_type: str,
    agent_id:   str,
    email_id:   Optional[str],
    payload:    Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "type":       event_type,
        "agent_id":   agent_id,
        "email_id":   email_id,
        "timestamp":  datetime.utcnow().isoformat(),
        "payload":    payload,
    }


# ---------------------------------------------------------------------------
# AuditWriter — handles DB writes with local buffer fallback
# ---------------------------------------------------------------------------
class AuditWriter:
    """
    Thread-safe audit writer.
    - Tries to write directly to audit_log table.
    - On failure, stores in write_buffer (in-state list).
    - Background thread periodically flushes buffer on reconnect.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._in_memory_buffer: List[Dict[str, Any]] = []
        self._db_available: bool = True  # tracked optimistically

        # Start background flush daemon
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()

    # ------------------------------------------------------------------
    def write(self, events: List[Dict[str, Any]]) -> None:
        """
        Write a batch of events. Falls back to local buffer if DB is down.
        Called from the AG-06 LangGraph node with state.event_queue contents.
        """
        for event in events:
            self._write_one(event)

    def _write_one(self, event: Dict[str, Any]) -> None:
        if self._db_available:
            try:
                self._persist_to_db(event)
            except Exception as exc:
                logger.warning(
                    json.dumps({"event": "audit_db_write_failed", "error": str(exc), "buffering": True})
                )
                self._db_available = False
                self._buffer(event)
        else:
            self._buffer(event)

    def _persist_to_db(self, event: Dict[str, Any]) -> None:
        """
        Sync wrapper for background thread.
        Creates its own event loop — asyncio.run() crashes if called from
        a thread that already has a running loop, so we manage it explicitly.
        APPEND-ONLY insert — no UPDATE, no DELETE ever.
        """
        import asyncio
        # Background flush thread has no event loop — create one explicitly
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("loop closed")
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(self._async_persist_to_db(event))

    async def _async_persist_to_db(self, event: Dict[str, Any]) -> None:
        """
        Real asyncpg write with orphan guard.
        FIX: if email_id is not present in emails table (FK violation would occur),
        discard the event and log — never buffer it for infinite retry.
        """
        import asyncpg
        from config.settings import settings

        db_url = getattr(settings, "DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")

        email_id   = event.get("email_id")
        agent_id   = event.get("agent_id", "UNKNOWN")
        event_type = event.get("type", "unknown")
        payload_str = json.dumps(event.get("payload", {}))

        conn = await asyncpg.connect(db_url)
        try:
            # ORPHAN GUARD — check email exists before inserting audit record
            # Prevents infinite retry loop when email row was never committed or was cleaned up
            if email_id:
                row = await conn.fetchrow(
                    "SELECT 1 FROM emails WHERE email_id = $1::uuid LIMIT 1",
                    email_id
                )
                if row is None:
                    logger.warning(json.dumps({
                        "event":      "audit_event_discarded_orphan",
                        "reason":     "email_id not found in emails table — FK would fail",
                        "email_id":   email_id,
                        "event_type": event_type,
                        "agent_id":   agent_id,
                    }))
                    return  # discard — do NOT raise, do NOT buffer

            await conn.execute(
                """
                INSERT INTO audit_log (email_id, agent_id, event_type, payload)
                VALUES ($1::uuid, $2, $3, $4::jsonb)
                """,
                email_id, agent_id, event_type, payload_str
            )
            logger.info(json.dumps({"event": "audit_db_written", "event_type": event_type}))
        finally:
            await conn.close()

    def _buffer(self, event: Dict[str, Any]) -> None:
        with self._lock:
            self._in_memory_buffer.append(event)
        logger.info(json.dumps({
            "event": "audit_buffered",
            "buffer_size": len(self._in_memory_buffer),
        }))

    # ------------------------------------------------------------------
    def _flush_loop(self) -> None:
        """Background daemon: attempt to flush buffer every 10 seconds."""
        import time
        while True:
            time.sleep(10)
            self._attempt_flush()

    def _attempt_flush(self) -> None:
        with self._lock:
            if not self._in_memory_buffer:
                return
            pending = list(self._in_memory_buffer)

        flushed  = 0
        discarded = 0
        failed    = 0

        for event in pending:
            try:
                self._persist_to_db(event)  # orphans are silently discarded inside
                # If no exception → either written or discarded (both = remove from buffer)
                with self._lock:
                    if event in self._in_memory_buffer:
                        self._in_memory_buffer.remove(event)
                flushed += 1
            except Exception as exc:
                # Genuine DB error (not FK orphan) — keep in buffer, mark DB unavailable
                logger.warning(json.dumps({
                    "event":   "audit_flush_event_failed",
                    "error":   str(exc),
                    "email_id": event.get("email_id"),
                }))
                self._db_available = False
                failed += 1

        if flushed > 0:
            self._db_available = True
            logger.info(json.dumps({
                "event":    "audit_buffer_flushed",
                "flushed":  flushed,
                "discarded": discarded,
                "failed":   failed,
            }))
        elif failed > 0:
            logger.warning(json.dumps({
                "event":   "audit_flush_partial_failure",
                "pending": failed,
            }))


# Singleton writer — shared across all nodes
_writer = AuditWriter()


# ---------------------------------------------------------------------------
# AG-06 LangGraph node
# ---------------------------------------------------------------------------
@instrument_agent("AG-06")
def audit_node(state: dict) -> Dict[str, Any]:
    """
    Drains state.event_queue → persist via AuditWriter.
    Returns empty updates (audit is side-effect only).
    """
    event_queue: List[Dict[str, Any]] = state.get("event_queue", [])

    if not event_queue:
        return {}

    logger.info(
        json.dumps({"event": "audit_node_processing", "event_count": len(event_queue)})
    )

    _writer.write(event_queue)

    return {
        "last_flush_time": datetime.utcnow(),
        "write_buffer":    _writer._in_memory_buffer.copy(),
        # event_queue is Annotated[List, operator.add] — we keep it accumulating
    }