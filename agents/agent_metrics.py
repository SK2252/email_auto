"""
agents/agent_metrics.py — MLflow Agent Instrumentation
Thin wrapper decorator for all 7 agents.

DESIGN RULES:
  - <5ms overhead per agent call
  - Never crashes the agent — all MLflow errors are caught silently
  - No parent run required — each agent creates its own run
  - Works even if MLflow server is down (graceful degradation)
"""
from __future__ import annotations

import time
import logging
import functools
import asyncio
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy MLflow import — does NOT crash at import if MLflow server is down
# ---------------------------------------------------------------------------
def _get_mlflow():
    try:
        import mlflow
        return mlflow
    except ImportError:
        logger.warning("mlflow not installed — instrumentation disabled")
        return None


def _setup_mlflow_once():
    """Set tracking URI once. Lazy — called only when first metric is logged."""
    try:
        import mlflow
        from config.settings import settings
        uri = getattr(settings, "MLFLOW_TRACKING_URI", "http://localhost:5000")
        mlflow.set_tracking_uri(uri)
        mlflow.set_experiment("email_ai_system")
    except Exception as exc:
        logger.warning(f"MLflow setup skipped: {exc}")


_mlflow_initialized = False


def _ensure_initialized():
    global _mlflow_initialized
    if not _mlflow_initialized:
        _setup_mlflow_once()
        _mlflow_initialized = True


# ---------------------------------------------------------------------------
# CORE METRIC LOGGER
# ---------------------------------------------------------------------------
def log_agent_metric(
    agent_id: str,
    email_id: str,
    execution_time_ms: float,
    success: bool,
    **kwargs,
) -> None:
    """
    Log agent metrics to MLflow. Silent on any failure.
    Overhead target: <5ms
    """
    try:
        mlflow = _get_mlflow()
        if not mlflow:
            return

        _ensure_initialized()

        # Each agent call = its own run (no parent run required)
        with mlflow.start_run(
            run_name=f"{agent_id}_{email_id[:8] if email_id != 'unknown' else 'unknown'}",
            tags={
                "agent_id":  agent_id,
                "email_id":  email_id,
            },
        ):
            # Core metrics (all agents)
            mlflow.log_metric("execution_time_ms", round(execution_time_ms, 2))
            mlflow.log_metric("success",           1 if success else 0)
            mlflow.log_param("agent_id",           agent_id)
            mlflow.log_param("email_id",           email_id)

            # Optional extra metrics/params
            for key, value in kwargs.items():
                if value is None:
                    continue
                if isinstance(value, (int, float)):
                    mlflow.log_metric(key, float(value))
                elif isinstance(value, bool):
                    mlflow.log_metric(key, 1.0 if value else 0.0)
                else:
                    mlflow.log_param(key, str(value)[:250])  # MLflow param limit

    except Exception as exc:
        # NEVER let MLflow crash the agent pipeline
        logger.debug(f"MLflow log skipped for {agent_id}: {exc}")


# ---------------------------------------------------------------------------
# DECORATOR
# ---------------------------------------------------------------------------
def instrument_agent(agent_id: str):
    """
    Decorator for both sync and async functions.
    Supports LangGraph nodes (async) and Celery tasks (sync).
    """
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                import mlflow
                start = time.monotonic()

                state = args[0] if args and isinstance(args[0], dict) else {}
                email_id = (
                    state.get("email_id") or
                    (state.get("parsed_email") or {}).get("email_id", "unknown")
                )

                try:
                    _ensure_initialized()
                    with mlflow.start_span(
                        name=agent_id,
                        span_type="AGENT",
                        attributes={"email_id": email_id, "agent_id": agent_id}
                    ) as span:
                        with mlflow.start_run(
                            run_name=f"{agent_id}_{email_id[:8]}",
                            tags={"agent_id": agent_id, "email_id": email_id},
                        ):
                            result = await func(*args, **kwargs)
                            _log_metrics_to_mlflow(agent_id, email_id, start, result, span)
                            return result
                except Exception as exc:
                    _handle_instrumentation_error(agent_id, email_id, start, exc)
                    raise
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                import mlflow
                start = time.monotonic()

                # Determine if first arg is state or celery task instance (self)
                first_arg = args[0] if args else None
                state = {}
                if isinstance(first_arg, dict):
                    state = first_arg
                elif hasattr(first_arg, 'request'): # Celery Task Instance
                    # Try to find state in other args
                    for arg in args[1:]:
                        if isinstance(arg, dict):
                            state = arg
                            break
                
                email_id = (
                    state.get("email_id") or
                    (state.get("parsed_email") or {}).get("email_id", "unknown")
                )

                try:
                    _ensure_initialized()
                    with mlflow.start_span(
                        name=agent_id,
                        span_type="AGENT",
                        attributes={"email_id": email_id, "agent_id": agent_id}
                    ) as span:
                        with mlflow.start_run(
                            run_name=f"{agent_id}_{email_id[:8]}",
                            tags={"agent_id": agent_id, "email_id": email_id},
                        ):
                            result = func(*args, **kwargs)
                            _log_metrics_to_mlflow(agent_id, email_id, start, result, span)
                            return result
                except Exception as exc:
                    _handle_instrumentation_error(agent_id, email_id, start, exc)
                    raise
            return sync_wrapper
    return decorator


def _log_metrics_to_mlflow(agent_id: str, email_id: str, start_time: float, result: Any, span: Any) -> None:
    """Shared helper to log metrics and update span attributes."""
    try:
        import mlflow
        elapsed = (time.monotonic() - start_time) * 1000
        
        mlflow.log_metric("execution_time_ms", round(elapsed, 2))
        mlflow.log_metric("success", 1)
        mlflow.log_param("agent_id", agent_id)
        mlflow.log_param("email_id", email_id)

        # Agent-specific metrics
        if agent_id == "AG-02" and isinstance(result, dict):
            clf = result.get("classification_result") or {}
            confidence = clf.get("confidence") or result.get("confidence")
            category   = clf.get("category")   or result.get("category", "")
            if confidence:
                mlflow.log_metric("confidence", float(confidence))
            mlflow.log_param("category",   category)
            span.set_attribute("confidence", confidence or 0.0)
            span.set_attribute("category",   category)

        elif agent_id == "AG-03" and isinstance(result, dict):
            rd = result.get("routing_decision") or {}
            span.set_attribute("team", str(rd.get("team", "unknown")))

        span.set_attribute("execution_time_ms", elapsed)
        span.set_attribute("success", True)
    except Exception as exc:
        logger.debug(f"Metrics logging failed: {exc}")


def _handle_instrumentation_error(agent_id: str, email_id: str, start_time: float, exc: Exception) -> None:
    """Shared helper to log failures."""
    elapsed = (time.monotonic() - start_time) * 1000
    log_agent_metric(
        agent_id, email_id, elapsed, False,
        error_type=type(exc).__name__,
    )