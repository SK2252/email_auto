"""
SQLAlchemy ORM models — Security layer only.
Audit models (AuditLog, AuditPartition, ComplianceReport) deferred to Phase 5.
"""

import enum
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Computed,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ─── Base ─────────────────────────────────────────────────────────────────────


class Base(DeclarativeBase):
    """DeclarativeBase for all ORM models."""

    pass


# ─── Enums ────────────────────────────────────────────────────────────────────


class ApiKeyStatusEnum(str, enum.Enum):
    """FSM: active → rotating → revoked. expired is set by cron."""

    ACTIVE = "active"
    ROTATING = "rotating"
    REVOKED = "revoked"
    EXPIRED = "expired"


class FollowUpTaskStatus(str, enum.Enum):
    PENDING = "pending"
    REMINDED = "reminded"
    RESOLVED = "resolved"


class FollowUpTaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FollowUpTaskCategory(str, enum.Enum):
    ACTION_REQUIRED = "action_required"
    AWAITING_REPLY = "awaiting_reply"
    FOLLOW_UP = "follow_up"


# ─── API Key ──────────────────────────────────────────────────────────────────


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    key_prefix: Mapped[str] = mapped_column(String(8), nullable=False)
    key_hash: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True
    )
    key_secret_hash: Mapped[Optional[str]] = mapped_column(String(128))
    owner: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text)
    environment: Mapped[str] = mapped_column(
        String(20), nullable=False, default="development"
    )
    rate_limit: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60
    )
    status: Mapped[ApiKeyStatusEnum] = mapped_column(
        Enum(ApiKeyStatusEnum, name="api_key_status", create_type=False),
        nullable=False,
        default=ApiKeyStatusEnum.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # For notifications
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    revoked_reason: Mapped[Optional[str]] = mapped_column(Text)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    last_used_ip: Mapped[Optional[str]] = mapped_column(INET)
    rotation_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("api_keys.id")
    )
    rotation_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict
    )

    # Relationships
    permissions: Mapped[List["ApiKeyPermission"]] = relationship(
        back_populates="api_key", cascade="all, delete-orphan"
    )

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Key is valid if active (or within rotation grace window) and not expired."""
        if self.status == ApiKeyStatusEnum.ACTIVE and not self.is_expired:
            return True
        if (
            self.status == ApiKeyStatusEnum.ROTATING
            and self.rotation_expires_at
        ):
            return datetime.now(timezone.utc) < self.rotation_expires_at
        return False


# ─── Permissions ──────────────────────────────────────────────────────────────


class ApiKeyPermission(Base):
    __tablename__ = "api_key_permissions"
    __table_args__ = (UniqueConstraint("api_key_id", "scope"),)

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    api_key_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("api_keys.id", ondelete="CASCADE"),
        index=True,
    )
    scope: Mapped[str] = mapped_column(String(50), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )
    granted_by: Mapped[Optional[str]] = mapped_column(String(255))

    api_key: Mapped["ApiKey"] = relationship(back_populates="permissions")


# ─── Tool Permissions (Scope → Tool Mapping) ──────────────────────────────────


class ToolPermission(Base):
    """Maps scopes to allowed tool names for RBAC enforcement."""

    __tablename__ = "tool_permissions"
    __table_args__ = (UniqueConstraint("scope", "tool_name"),)

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    scope: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )


# ─── Usage Tracking (Partitioned) ────────────────────────────────────────────


class ApiKeyUsage(Base):
    """Partitioned by month. 90-day rolling retention."""

    __tablename__ = "api_key_usage"
    __table_args__ = (
        Index("idx_usage_key_time", "api_key_id", "created_at"),
        {"postgresql_partition_by": "RANGE (created_at)"},
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), default=lambda: str(uuid4())
    )
    api_key_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False
    )
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    tool_name: Mapped[Optional[str]] = mapped_column(String(100))
    source_ip: Mapped[Optional[str]] = mapped_column(INET)
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response_time_ms: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )

    __mapper_args__ = {"primary_key": [id, created_at]}


# ─── Follow-up Tasks ──────────────────────────────────────────────────────────


class FollowUpTask(Base):
    """Track emails needing follow-up with reminder scheduling."""

    __tablename__ = "follow_up_tasks"
    __table_args__ = (
        Index("ix_follow_up_user_active", "user_id", "is_active"),
        Index("ix_follow_up_remind_at", "remind_at"),
    )

    # Primary Key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )

    # Identity
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # API key owner
    gmail_user_id: Mapped[str] = mapped_column(String(255), nullable=False)        # Gmail account being accessed

    # Email Details
    thread_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    sender: Mapped[str] = mapped_column(String(255), nullable=False)
    snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Classification
    category: Mapped[FollowUpTaskCategory] = mapped_column(
        Enum(FollowUpTaskCategory, name="follow_up_category", create_type=False),
        default=FollowUpTaskCategory.AWAITING_REPLY,
        nullable=False,
    )
    priority: Mapped[FollowUpTaskPriority] = mapped_column(
        Enum(FollowUpTaskPriority, name="follow_up_priority", create_type=False),
        default=FollowUpTaskPriority.MEDIUM,
        nullable=False,
    )

    # Scheduling
    remind_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    status: Mapped[FollowUpTaskStatus] = mapped_column(
        Enum(FollowUpTaskStatus, name="follow_up_status", create_type=False),
        default=FollowUpTaskStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Reminder Tracking
    reminder_sent_count: Mapped[int] = mapped_column(Integer, default=0)
    last_reminder_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Lifecycle
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )

    # Audit
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        onupdate=text("NOW()"),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<FollowUpTask {self.id}: {self.sender} - {self.subject[:40] if self.subject else 'None'}>"

    def mark_resolved(self):
        """Mark follow-up as resolved."""
        self.status = FollowUpTaskStatus.RESOLVED
        self.resolved_at = datetime.now(timezone.utc)
        self.is_active = False


# ─── Notifications ────────────────────────────────────────────────────────────


class InAppNotification(Base):
    """In-app notifications for users. Partitioned by created_at."""

    __tablename__ = "in_app_notifications"
    __table_args__ = (
        Index("idx_notification_user_read", "user_id", "is_read"),
        {"postgresql_partition_by": "RANGE (created_at)"},
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # follow_up_reminder, etc.
    action_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )

    __mapper_args__ = {"primary_key": [id, created_at]}
