"""
Prometheus metrics definitions for the Enterprise MCP Server.
All counters, histograms, and gauges are defined here centrally.
"""

from prometheus_client import Counter, Gauge, Histogram, Info

# --- Server Info ---
server_info = Info(
    "mcp_server",
    "MCP server version and environment information",
)

# --- HTTP Request Metrics ---
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests received",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# --- MCP Tool Metrics ---
tool_executions_total = Counter(
    "mcp_tool_executions_total",
    "Total MCP tool executions",
    ["tool_name", "status"],
)

tool_execution_duration_seconds = Histogram(
    "mcp_tool_execution_duration_seconds",
    "MCP tool execution duration in seconds",
    ["tool_name"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

# --- Session Metrics ---
active_sessions = Gauge(
    "mcp_active_sessions",
    "Number of active MCP sessions",
)

# --- ISO 42001 Compliance Metrics ---
risk_assessments_total = Counter(
    "iso42001_risk_assessments_total",
    "Total risk assessments performed",
    ["risk_level"],
)

data_classifications_total = Counter(
    "iso42001_data_classifications_total",
    "Total data classifications performed",
    ["classification"],
)

pii_detections_total = Counter(
    "iso42001_pii_detections_total",
    "Total PII detections",
    ["pii_type"],
)

audit_logs_total = Counter(
    "iso42001_audit_logs_total",
    "Total audit log entries written",
    ["destination"],  # firestore, local
)

# --- Infrastructure Metrics ---
circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half-open)",
    ["service"],
)

job_queue_depth = Gauge(
    "job_queue_depth",
    "Number of pending jobs in the async queue",
)

# --- Security Metrics ---
api_key_validations = Counter(
    "api_key_validations_total",
    "Total API key validation attempts",
    ["result"],  # success, missing, invalid, expired_or_revoked
)

rbac_checks = Counter(
    "rbac_checks_total",
    "Total RBAC authorization checks",
    ["tool_name", "result"],  # granted, denied
)


def init_server_info(version: str, environment: str, python_version: str) -> None:
    """Set static server info metrics on startup."""
    server_info.info({
        "version": version,
        "environment": environment,
        "python_version": python_version,
    })
