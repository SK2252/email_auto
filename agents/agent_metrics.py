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
from typing import Any, Dict

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
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            import mlflow
            start = time.monotonic()

            state = args[0] if args and isinstance(args[0], dict) else {}
            email_id = (
                state.get("email_id") or
                (state.get("parsed_email") or {}).get("email_id", "unknown")
            )

            try:
                _ensure_initialized()

                # SPAN = feeds the Overview/Traces tab
                with mlflow.start_span(
                    name=agent_id,
                    span_type="AGENT",
                    attributes={
                        "email_id": email_id,
                        "agent_id": agent_id,
                    }
                ) as span:

                    # RUN = feeds the Runs tab (existing)
                    with mlflow.start_run(
                        run_name=f"{agent_id}_{email_id[:8]}",
                        tags={"agent_id": agent_id, "email_id": email_id},
                    ):
                        result = await func(*args, **kwargs)
                        elapsed = (time.monotonic() - start) * 1000

                        mlflow.log_metric("execution_time_ms", elapsed)
                        mlflow.log_metric("success", 1)
                        mlflow.log_param("agent_id", agent_id)
                        mlflow.log_param("email_id", email_id)

                        # AG-02 specific metrics
                        if agent_id == "AG-02" and isinstance(result, dict):
                            clf = result.get("classification_result") or {}
                            confidence = clf.get("confidence") or result.get("confidence")
                            category   = clf.get("category")   or result.get("category", "")
                            if confidence:
                                mlflow.log_metric("confidence", float(confidence))
                            mlflow.log_param("category",   category)
                            mlflow.log_param("model_used", "llama-3.3-70b-versatile")

                            # Feed span attributes for Overview tab
                            span.set_attribute("confidence",  confidence or 0.0)
                            span.set_attribute("category",    category)
                            span.set_attribute("model",       "llama-3.3-70b-versatile")
                            span.set_attribute("provider",    "groq")

                        elif agent_id == "AG-01" and isinstance(result, dict):
                            span.set_attribute("ack_sent", result.get("ack_sent", False))

                        elif agent_id == "AG-03" and isinstance(result, dict):
                            rd = result.get("routing_decision") or {}
                            span.set_attribute("team", str(rd.get("team", "unknown")))

                        span.set_attribute("execution_time_ms", elapsed)
                        span.set_attribute("success", True)

                        return result

            except Exception as exc:
                elapsed = (time.monotonic() - start) * 1000
                log_agent_metric(
                    agent_id, email_id, elapsed, False,
                    error_type=type(exc).__name__,
                )
                raise

        return wrapper
    return decorator