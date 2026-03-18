"""Create security tables

Revision ID: 001
Revises: None
Create Date: 2026-02-16

Creates:
  - api_key_status enum
  - api_keys table
  - api_key_permissions table
  - tool_permissions table (with seed data)
  - api_key_usage table (partitioned)
  - DB roles (mcp_app_role, mcp_readonly_role, mcp_admin_role)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Extensions ────────────────────────────────────────────────────────
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # ── Enum ──────────────────────────────────────────────────────────────
    api_key_status = postgresql.ENUM(
        "active", "rotating", "revoked", "expired",
        name="api_key_status",
        create_type=False,
    )
    op.execute("CREATE TYPE api_key_status AS ENUM ('active', 'rotating', 'revoked', 'expired')")

    # ── api_keys ──────────────────────────────────────────────────────────
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("key_prefix", sa.String(8), nullable=False),
        sa.Column("key_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("key_secret_hash", sa.String(128), nullable=True),
        sa.Column("owner", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("environment", sa.String(20), nullable=False, server_default="development"),
        sa.Column("rate_limit", sa.Integer, nullable=False, server_default="60"),
        sa.Column("status", api_key_status, nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.Text, nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_ip", postgresql.INET, nullable=True),
        sa.Column("rotation_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("api_keys.id"), nullable=True),
        sa.Column("rotation_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB, server_default="{}"),
        sa.CheckConstraint(
            "(status = 'rotating' AND rotation_id IS NOT NULL AND rotation_expires_at IS NOT NULL) "
            "OR (status != 'rotating')",
            name="chk_rotation",
        ),
        sa.CheckConstraint(
            "environment IN ('development', 'staging', 'production')",
            name="chk_environment",
        ),
    )
    op.create_index("idx_api_keys_hash", "api_keys", ["key_hash"])
    op.create_index("idx_api_keys_owner", "api_keys", ["owner"])
    op.create_index("idx_api_keys_status", "api_keys", ["status"])

    # ── api_key_permissions ───────────────────────────────────────────────
    op.create_table(
        "api_key_permissions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("api_key_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scope", sa.String(50), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("granted_by", sa.String(255), nullable=True),
        sa.UniqueConstraint("api_key_id", "scope"),
    )
    op.create_index("idx_permissions_key", "api_key_permissions", ["api_key_id"])

    # ── tool_permissions ──────────────────────────────────────────────────
    op.create_table(
        "tool_permissions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("scope", sa.String(50), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("scope", "tool_name"),
    )
    op.create_index("idx_tool_perms_scope", "tool_permissions", ["scope"])

    # Seed default tool→scope mappings
    op.execute("""
        INSERT INTO tool_permissions (id, scope, tool_name, description) VALUES
        (uuid_generate_v4(), 'search',   'search_files',        'File search in allowed directories'),
        (uuid_generate_v4(), 'document', 'read_excel',          'Read Excel files'),
        (uuid_generate_v4(), 'document', 'merge_template',      'Merge Word templates'),
        (uuid_generate_v4(), 'document', 'convert_to_pdf',      'Convert documents to PDF'),
        (uuid_generate_v4(), 'document', 'validate_input_data', 'Validate input data files'),
        (uuid_generate_v4(), 'email',    'send_email',          'Send email via Outlook'),
        (uuid_generate_v4(), 'email',    'list_recipes',        'List email templates')
    """)

    # ── api_key_usage (partitioned) ───────────────────────────────────────
    op.execute("""
        CREATE TABLE api_key_usage (
            id          UUID DEFAULT uuid_generate_v4(),
            api_key_id  UUID NOT NULL,
            endpoint    VARCHAR(255) NOT NULL,
            tool_name   VARCHAR(100),
            source_ip   INET,
            user_agent  TEXT,
            status_code INTEGER NOT NULL,
            response_time_ms DOUBLE PRECISION,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (id, created_at)
        ) PARTITION BY RANGE (created_at)
    """)
    op.create_index("idx_usage_key_time", "api_key_usage", ["api_key_id", "created_at"])

    # Create initial partitions (current + next 2 months)
    op.execute("""
        CREATE TABLE api_key_usage_2026_02
            PARTITION OF api_key_usage
            FOR VALUES FROM ('2026-02-01') TO ('2026-03-01')
    """)
    op.execute("""
        CREATE TABLE api_key_usage_2026_03
            PARTITION OF api_key_usage
            FOR VALUES FROM ('2026-03-01') TO ('2026-04-01')
    """)
    op.execute("""
        CREATE TABLE api_key_usage_2026_04
            PARTITION OF api_key_usage
            FOR VALUES FROM ('2026-04-01') TO ('2026-05-01')
    """)

    # ── DB Roles ──────────────────────────────────────────────────────────
    # Use DO block to avoid errors if roles already exist
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'mcp_app_role') THEN
                CREATE ROLE mcp_app_role;
            END IF;
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'mcp_readonly_role') THEN
                CREATE ROLE mcp_readonly_role;
            END IF;
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'mcp_admin_role') THEN
                CREATE ROLE mcp_admin_role;
            END IF;
        END
        $$
    """)

    # Grant permissions
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON api_keys TO mcp_app_role")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON api_key_permissions TO mcp_app_role")
    op.execute("GRANT SELECT ON tool_permissions TO mcp_app_role")
    op.execute("GRANT INSERT, SELECT ON api_key_usage TO mcp_app_role")

    op.execute("GRANT SELECT ON api_keys TO mcp_readonly_role")
    op.execute("GRANT SELECT ON api_key_permissions TO mcp_readonly_role")
    op.execute("GRANT SELECT ON tool_permissions TO mcp_readonly_role")
    op.execute("GRANT SELECT ON api_key_usage TO mcp_readonly_role")

    op.execute("GRANT ALL ON api_keys TO mcp_admin_role")
    op.execute("GRANT ALL ON api_key_permissions TO mcp_admin_role")
    op.execute("GRANT ALL ON tool_permissions TO mcp_admin_role")
    op.execute("GRANT ALL ON api_key_usage TO mcp_admin_role")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS api_key_usage CASCADE")
    op.execute("DROP TABLE IF EXISTS tool_permissions CASCADE")
    op.execute("DROP TABLE IF EXISTS api_key_permissions CASCADE")
    op.execute("DROP TABLE IF EXISTS api_keys CASCADE")
    op.execute("DROP TYPE IF EXISTS api_key_status")
