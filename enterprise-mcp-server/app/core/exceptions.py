"""
Standardized error codes for the Enterprise MCP Server.
All error responses use these codes for consistent client handling.
"""


class ErrorCode:
    """Error code constants grouped by category."""

    # --- Authentication (1xx) ---
    AUTH_MISSING_KEY = "E_AUTH_100"
    AUTH_INVALID_KEY = "E_AUTH_101"
    AUTH_EXPIRED_KEY = "E_AUTH_102"
    AUTH_REVOKED_KEY = "E_AUTH_103"
    AUTH_INVALID_SIGNATURE = "E_AUTH_104"
    AUTH_TIMESTAMP_EXPIRED = "E_AUTH_105"

    # --- Authorization (2xx) ---
    AUTHZ_INSUFFICIENT_SCOPE = "E_AUTHZ_200"
    AUTHZ_TOOL_NOT_ALLOWED = "E_AUTHZ_201"

    # --- MCP Protocol (3xx) ---
    MCP_INVALID_REQUEST = "E_MCP_300"
    MCP_SESSION_NOT_FOUND = "E_MCP_301"
    MCP_SESSION_EXPIRED = "E_MCP_302"
    MCP_SESSION_LIMIT = "E_MCP_303"
    MCP_TOOL_NOT_FOUND = "E_MCP_304"
    MCP_INVALID_PARAMS = "E_MCP_305"

    # --- Tool Execution (4xx) ---
    TOOL_EXECUTION_FAILED = "E_TOOL_400"
    TOOL_TIMEOUT = "E_TOOL_401"
    TOOL_FILE_NOT_FOUND = "E_TOOL_402"
    TOOL_INVALID_INPUT = "E_TOOL_403"
    TOOL_QUEUED = "I_TOOL_404"  # Info, not error — job was queued

    # --- Infrastructure (5xx) ---
    INFRA_REDIS_ERROR = "E_INFRA_500"
    INFRA_FIRESTORE_ERROR = "E_INFRA_501"
    INFRA_CIRCUIT_OPEN = "E_INFRA_502"
    INFRA_RATE_LIMITED = "E_INFRA_503"
    INFRA_QUEUE_FULL = "E_INFRA_504"

    # --- Compliance (6xx) ---
    COMPLIANCE_RISK_BLOCKED = "E_COMP_600"
    COMPLIANCE_AUDIT_FAILED = "E_COMP_601"


# Human-readable descriptions
ERROR_MESSAGES = {
    ErrorCode.AUTH_MISSING_KEY: "API key is required. Set the X-API-Key header.",
    ErrorCode.AUTH_INVALID_KEY: "Invalid API key.",
    ErrorCode.AUTH_EXPIRED_KEY: "API key has expired.",
    ErrorCode.AUTH_REVOKED_KEY: "API key has been revoked.",
    ErrorCode.AUTH_INVALID_SIGNATURE: "HMAC signature verification failed.",
    ErrorCode.AUTH_TIMESTAMP_EXPIRED: "Request timestamp is outside the allowed tolerance.",
    ErrorCode.AUTHZ_INSUFFICIENT_SCOPE: "API key does not have the required scope for this tool.",
    ErrorCode.AUTHZ_TOOL_NOT_ALLOWED: "Tool access denied for this API key.",
    ErrorCode.MCP_INVALID_REQUEST: "Invalid MCP JSON-RPC request.",
    ErrorCode.MCP_SESSION_NOT_FOUND: "MCP session not found. Send an initialize request first.",
    ErrorCode.MCP_SESSION_EXPIRED: "MCP session has expired.",
    ErrorCode.MCP_SESSION_LIMIT: "Maximum sessions per API key exceeded.",
    ErrorCode.MCP_TOOL_NOT_FOUND: "Requested tool does not exist.",
    ErrorCode.MCP_INVALID_PARAMS: "Invalid parameters for the requested tool.",
    ErrorCode.TOOL_EXECUTION_FAILED: "Tool execution failed.",
    ErrorCode.TOOL_TIMEOUT: "Tool execution timed out.",
    ErrorCode.TOOL_FILE_NOT_FOUND: "Requested file not found.",
    ErrorCode.TOOL_INVALID_INPUT: "Invalid input data for the tool.",
    ErrorCode.TOOL_QUEUED: "Tool execution queued. Poll for results.",
    ErrorCode.INFRA_REDIS_ERROR: "Redis connection error.",
    ErrorCode.INFRA_FIRESTORE_ERROR: "Firestore connection error.",
    ErrorCode.INFRA_CIRCUIT_OPEN: "Service temporarily unavailable (circuit breaker open).",
    ErrorCode.INFRA_RATE_LIMITED: "Rate limit exceeded. Retry after the indicated time.",
    ErrorCode.INFRA_QUEUE_FULL: "Job queue is full. Try again later.",
    ErrorCode.COMPLIANCE_RISK_BLOCKED: "Operation blocked due to high risk assessment.",
    ErrorCode.COMPLIANCE_AUDIT_FAILED: "Failed to write audit log.",
}


def get_error_message(code: str) -> str:
    """Get human-readable message for an error code."""
    return ERROR_MESSAGES.get(code, f"Unknown error: {code}")
