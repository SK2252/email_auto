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
        Sync wrapper: INSERT INTO audit_log (email_id, agent_id, event_type, payload) VALUES (...)
        This is an APPEND-ONLY insert — no UPDATE, no DELETE ever.
        """
        import asyncio
        asyncio.run(self._async_persist_to_db(event))

    async def _async_persist_to_db(self, event: Dict[str, Any]) -> None:
        """Real asyncpg write."""
        import asyncpg
        from config.settings import settings

        db_url = getattr(settings, "DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
        
        # event might have email_id as string, but the DB expects UUID. asyncpg handles string to UUID auto-cast
        # if the column is UUID, but it's safer to let Postgres cast it if needed.
        email_id = event.get("email_id")
        agent_id = event.get("agent_id", "UNKNOWN")
        event_type = event.get("type", "unknown")
        payload_str = json.dumps(event.get("payload", {}))
        
        conn = await asyncpg.connect(db_url)
        try:
            # We cast $1::uuid to ensure asyncpg passes it correctly to the UUID column if email_id is provided
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

        try:
            for event in pending:
                self._persist_to_db(event)  # raises on failure

            # All written — clear buffer
            with self._lock:
                # Remove only the events we successfully flushed
                for event in pending:
                    if event in self._in_memory_buffer:
                        self._in_memory_buffer.remove(event)

            self._db_available = True
            logger.info(
                json.dumps({"event": "audit_buffer_flushed", "events_flushed": len(pending)})
            )

        except Exception as exc:
            logger.warning(
                json.dumps({"event": "audit_flush_failed", "error": str(exc), "pending": len(pending)})
            )
            self._db_available = False


# Singleton writer — shared across all nodes
_writer = AuditWriter()


# ---------------------------------------------------------------------------
# AG-06 LangGraph node
# ---------------------------------------------------------------------------
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
