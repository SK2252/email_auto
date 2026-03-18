"""
Pydantic v2 models for the Enterprise MCP Server.
Used across API, orchestrator, compliance, and audit layers.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, computed_field


# ─── Enums ────────────────────────────────────────────────────────────────────

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DataClassification(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class ToolStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    QUEUED = "QUEUED"
    TIMEOUT = "TIMEOUT"


class WorkflowStatus(str, Enum):
    STARTED = "STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ApiKeyStatus(str, Enum):
    ACTIVE = "active"
    ROTATING = "rotating"
    REVOKED = "revoked"
    EXPIRED = "expired"


# ─── Identity (from API key) ────────────────────────────────────────────────

class Identity(BaseModel):
    """Represents the authenticated caller from API key validation."""

    key_id: str
    owner: str
    scopes: List[str] = Field(default_factory=list)
    status: ApiKeyStatus = ApiKeyStatus.ACTIVE
    rate_limit: int = 60
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None


# ─── Risk Assessment ────────────────────────────────────────────────────────

class RiskFactor(BaseModel):
    factor: str
    weight: float
    value: float
    contribution: float  # weight * value


class RiskAssessment(BaseModel):
    """risk_level is derived from risk_score — single source of truth."""
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_factors: List[RiskFactor] = Field(default_factory=list)

    @computed_field
    @property
    def risk_level(self) -> RiskLevel:
        if self.risk_score >= 0.8:
            return RiskLevel.CRITICAL
        elif self.risk_score >= 0.6:
            return RiskLevel.HIGH
        elif self.risk_score >= 0.3:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW


# ─── Data Classification Result ────────────────────────────────────────────

class ClassificationResult(BaseModel):
    level: DataClassification
    keywords_detected: List[str] = Field(default_factory=list)
    pii_detected: bool = False
    phi_detected: bool = False


# ─── Tool Execution ────────────────────────────────────────────────────────

class ToolRequest(BaseModel):
    """Incoming tool call request."""

    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Result of a tool execution."""

    status: ToolStatus
    data: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    audit_id: Optional[str] = None
    job_id: Optional[str] = None  # For async/queued tools
    duration_ms: Optional[float] = None


# ─── Audit Entry ───────────────────────────────────────────────────────────

class AuditEntry(BaseModel):
    """Single audit log entry for ISO 42001 compliance."""

    audit_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tool_name: str
    action_type: str = "TOOL_CALL"

    # Identity
    key_id: Optional[str] = None
    owner: Optional[str] = None
    source_ip: Optional[str] = None
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None

    # Parameters (sanitized — no PII)
    parameters_sanitized: Dict[str, Any] = Field(default_factory=dict)

    # Result
    result_status: ToolStatus = ToolStatus.SUCCESS
    result_data: Optional[Dict[str, Any]] = None

    # Compliance
    risk_assessment: Optional[RiskAssessment] = None
    data_classification: Optional[ClassificationResult] = None

    # Performance
    execution_time_ms: Optional[float] = None

    # ISO 42001 clauses
    applicable_clauses: List[str] = Field(default_factory=list)
    compliance_status: str = "COMPLIANT"

    # Error (if any)
    error: Optional[Dict[str, Any]] = None


# ─── Workflow Tracking ────────────────────────────────────────────────────

class WorkflowEntry(BaseModel):
    """End-to-end workflow tracking record."""

    workflow_id: str
    correlation_id: str
    status: WorkflowStatus = WorkflowStatus.STARTED
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    tools_executed: List[AuditEntry] = Field(default_factory=list)
    summary: Optional[Dict[str, Any]] = None
    retention_until: Optional[datetime] = None


# ─── API Error Response ───────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """Standardized error response."""

    error: Dict[str, Any] = Field(
        ...,
        examples=[{
            "code": "E_AUTH_100",
            "message": "API key is required.",
        }],
    )
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None


# ─── Health Response ─────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    environment: Optional[str] = None
    checks: Optional[Dict[str, str]] = None
