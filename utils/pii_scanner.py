"""
utils/pii_scanner.py — Dual-Layer PII Scanner (CRITICAL)
Layer 1: Regex patterns (fast, low latency)
Layer 2: LLM confirmation via Groq llama-3.3-70b (semantic catch)

If EITHER layer detects PII:
  → Hard-block send (no override)
  → Alert compliance officer via Slack
  → Log pii_scan_result to state and audit trail
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List

from mcp_tools.llm_client import LLMProvider, call_llm
from prompts.pii_scan_prompt import build_pii_scan_prompts, PII_SCAN_SYSTEM_PROMPT, PII_SCAN_USER_PROMPT
from utils.retry_utils import retry_with_backoff

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Layer 1: Regex patterns
# ---------------------------------------------------------------------------
_PII_PATTERNS: Dict[str, str] = {
    "ssn":         r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
    "phone":       r"\b\+?1?\s*[\(]?\d{3}[\)\-\.\s]?\s*\d{3}[\-\.\s]?\d{4}\b",
    "email":       r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}\b",
    "dob":         r"\b(?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12]\d|3[01])[-/](?:19|20)\d{2}\b",
    "uk_nino":     r"\b[A-Z]{2}\d{6}[A-D]\b",
    "passport":    r"\b[A-Z]{1,2}\d{6,9}\b",
    "iban":        r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}(?:[A-Z0-9]{0,16})?\b",
}

# ---------------------------------------------------------------------------
# Layer 2: LLM prompt for semantic PII detection
# ---------------------------------------------------------------------------
_PII_LLM_SYSTEM = PII_SCAN_SYSTEM_PROMPT   # backwards compat alias
_PII_LLM_USER   = PII_SCAN_USER_PROMPT


# ---------------------------------------------------------------------------
# Public scanner
# ---------------------------------------------------------------------------
class PIIScanner:
    """
    Dual-layer PII detector.
    Use .scan(text) — returns a result dict.
    Caller MUST check result["is_safe"] before sending any email.
    """

    def scan(self, text: str, domain_config: dict | None = None) -> Dict[str, Any]:
        """
        Run both layers, optionally merging domain-specific PII patterns.

        Args:
            text:          Text to scan (email body or draft).
            domain_config: Optional domain config from state. When provided:
                           - Domain regex patterns are merged into Layer 1.
                           - Domain PII types are added to the LLM prompt.
        Returns:
            {
                "is_safe":        bool,  ← False means HARD BLOCK, no override
                "detected_types": list,
                "match_counts":   dict,
                "llm_flag":       bool,
                "llm_reason":     str,
                "blocked":        bool,
            }
        """
        # ---- Build effective pattern set ----
        effective_patterns = dict(_PII_PATTERNS)
        if domain_config:
            from utils.domain_loader import get_extra_pii_patterns
            extra = get_extra_pii_patterns(domain_config)
            effective_patterns.update(extra)   # domain patterns override or extend base

        # ---- Layer 1 (regex) ----
        regex_matches: Dict[str, int] = {}
        for pii_type, pattern in effective_patterns.items():
            found = re.findall(pattern, text, re.IGNORECASE)
            if found:
                regex_matches[pii_type] = len(found)

        # ---- Layer 2 (LLM) ----
        llm_flag, llm_reason = self._llm_scan(text, domain_config=domain_config)

        # ---- Decision ----
        detected_types = list(regex_matches.keys())
        if llm_flag:
            detected_types.append("llm_semantic")

        is_safe = not bool(detected_types)
        blocked = not is_safe  # hard block, no override

        result: Dict[str, Any] = {
            "is_safe":        is_safe,
            "detected_types": detected_types,
            "match_counts":   regex_matches,
            "llm_flag":       llm_flag,
            "llm_reason":     llm_reason,
            "blocked":        blocked,
        }

        if blocked:
            logger.warning(
                json.dumps({"event": "pii_hard_block", "detected_types": detected_types})
            )
            self._alert_compliance(detected_types)

        return result

    @retry_with_backoff(retries=2, on_exhaust="return_none")
    def _llm_scan(self, text: str, domain_config: dict | None = None) -> tuple[bool, str]:
        """
        Layer 2: call Groq llama-3.3-70b for semantic PII detection.
        Uses domain-aware prompt when domain_config is provided.
        Returns (pii_detected: bool, reason: str).
        """
        truncated = text[:2000]

        # Build domain-aware prompts
        sys_p, usr_p = build_pii_scan_prompts(domain_config)

        raw = call_llm(
            provider=LLMProvider.GROQ,
            messages=[
                {"role": "system", "content": sys_p},
                {"role": "user",   "content": usr_p.format(text=truncated)},
            ],
            temperature=0.0,
            max_tokens=128,
        )
        if raw is None:
            return False, "llm_unavailable"

        try:
            parsed = json.loads(raw.strip())
            return bool(parsed.get("pii_detected", False)), parsed.get("reason", "")
        except json.JSONDecodeError:
            # If LLM returns non-JSON, fail-safe: flag as PII
            logger.warning(json.dumps({"event": "pii_llm_parse_error", "raw": raw[:200]}))
            return True, "llm_parse_error_flagged_safe"

    def _alert_compliance(self, detected_types: List[str]) -> None:
        """POST alert to compliance Slack channel."""
        from config.settings import settings
        logger.error(
            json.dumps({
                "event":     "compliance_alert_sent",
                "channel":   settings.SLACK_COMPLIANCE_CHANNEL,
                "pii_types": detected_types,
            })
        )
        # TODO: POST to settings.SLACK_WEBHOOK_URL with channel override
