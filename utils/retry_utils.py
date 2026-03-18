"""
utils/retry_utils.py — Shared Retry Logic
Used by all agents and MCP clients for transient-error resilience.
"""
from __future__ import annotations

import functools
import json
import logging
import time
from typing import Any, Callable, Tuple, Type

logger = logging.getLogger(__name__)


class DeadLetterError(Exception):
    """Raised after all retries exhausted — caller should route to DLQ."""


def retry_with_backoff(
    retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_exhaust: str = "raise",   # "raise" | "dlq" | "return_none"
):
    """
    Decorator: retry with exponential backoff + jitter.

    Args:
        retries:    Maximum number of retry attempts (not counting first call).
        base_delay: Initial delay in seconds; doubles each retry.
        max_delay:  Cap on delay between retries.
        exceptions: Tuple of exceptions to catch and retry on.
        on_exhaust: Action when retries exhausted:
                    "raise"       → re-raise the last exception
                    "dlq"         → raise DeadLetterError (caller sends to DLQ)
                    "return_none" → swallow and return None

    Example:
        @retry_with_backoff(retries=3, on_exhaust="dlq")
        def risky_api_call(): ...
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None
            for attempt in range(retries + 1):
                try:
                    return func(*args, **kwargs)

                except exceptions as exc:
                    last_exc = exc
                    if attempt == retries:
                        break  # exhausted — exit loop

                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(
                        json.dumps({
                            "event": "retry_attempt",
                            "function": func.__qualname__,
                            "attempt": attempt + 1,
                            "max_retries": retries,
                            "delay_seconds": delay,
                            "error": str(exc),
                        })
                    )
                    time.sleep(delay)

            # All retries exhausted
            logger.error(
                json.dumps({
                    "event": "retry_exhausted",
                    "function": func.__qualname__,
                    "error": str(last_exc),
                })
            )

            if on_exhaust == "dlq":
                raise DeadLetterError(
                    f"{func.__qualname__} failed after {retries} retries: {last_exc}"
                ) from (last_exc if last_exc is not None else Exception())
            elif on_exhaust == "return_none":
                return None
            else:
                raise last_exc if last_exc is not None else Exception("Retries exhausted without exception")

        from typing import cast
        return cast(Callable[..., Any], wrapper)
    return decorator


def send_to_dead_letter_queue(payload: dict, reason: str) -> None:
    """
    Placeholder for DLQ integration.
    In production: write to a 'dead_letter' Postgres table or an SQS queue.
    Sends a Slack alert after writing.
    """
    logger.error(
        json.dumps({
            "event": "dead_letter_queued",
            "reason": reason,
            "payload_preview": {k: str(v)[:80] for k, v in payload.items()},  # type: ignore
        })
    )
    # TODO Sprint 1: persist to dead_letter table; POST to SLACK_WEBHOOK_URL
