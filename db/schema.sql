-- =============================================================================
-- AI Inbox Management System — PostgreSQL DDL
-- Sprint 1 Foundation Schema
-- =============================================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- EMAILS TABLE — Core intake record, one row per inbound email
-- =============================================================================
CREATE TABLE IF NOT EXISTS emails (
    -- Identity
    email_id        UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id     VARCHAR(255) UNIQUE NOT NULL,  -- Gmail/Outlook message ID
    source          VARCHAR(50)  NOT NULL          -- 'gmail', 'outlook', 'zendesk', 'freshdesk'
        CHECK (source IN ('gmail', 'outlook', 'zendesk', 'freshdesk')),

    -- Multi-tenant
    tenant_id       VARCHAR(100) REFERENCES tenants(tenant_id),  -- owning tenant

    -- Email content
    sender          VARCHAR(255) NOT NULL,

    subject         TEXT,
    body            TEXT,
    thread_id       VARCHAR(255),
    received_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    -- Intake metadata
    case_reference  VARCHAR(50)  UNIQUE,            -- CASE-{YYYYMMDD}-{uuid[:6]}
    ack_sent        BOOLEAN      DEFAULT FALSE,
    attachment_paths JSONB       DEFAULT '[]',

    -- Classification (AG-02)
    classification_result JSONB,                   -- {category, priority, sla_bucket}
    sentiment_score       DOUBLE PRECISION,
    confidence            DOUBLE PRECISION,
    low_confidence_flag   BOOLEAN DEFAULT FALSE,

    -- Routing (AG-03)
    routing_decision  VARCHAR(100),
    assignment_id     VARCHAR(100),

    -- Response (AG-04)
    draft             TEXT,
    tone_score        DOUBLE PRECISION,
    pii_scan_result   JSONB,                       -- {is_safe, detected_types, ...}
    analyst_edits     TEXT,

    -- SLA (AG-05)
    sla_deadline        TIMESTAMPTZ,
    elapsed_time        DOUBLE PRECISION,
    alert_80_sent       BOOLEAN DEFAULT FALSE,
    escalated           BOOLEAN DEFAULT FALSE,
    current_assignee    VARCHAR(255),

    -- Orchestration tracking
    current_step        VARCHAR(50)  DEFAULT 'intake',
    agent_statuses      JSONB        DEFAULT '{}',  -- {agent_id: status}
    retry_count         SMALLINT     DEFAULT 0,

    -- Timestamps
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- ATTACHMENTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS attachments (
    attachment_id   UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_id        UUID        NOT NULL REFERENCES emails(email_id) ON DELETE CASCADE,
    tenant_id       VARCHAR(100) REFERENCES tenants(tenant_id),
    filename        VARCHAR(255) NOT NULL,
    content_type    VARCHAR(100),
    storage_path    TEXT        NOT NULL,
    size_bytes      BIGINT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- AUDIT_LOG TABLE — Append-only, NEVER UPDATE/DELETE (AG-06 guarantee)
-- =============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    log_id      UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_id    UUID        REFERENCES emails(email_id),  -- nullable: some events are system-level
    tenant_id   VARCHAR(100) REFERENCES tenants(tenant_id),
    agent_id    VARCHAR(10) NOT NULL,                      -- 'AG-01' .. 'AG-07'
    event_type  VARCHAR(100) NOT NULL,                     -- 'email_ingested', 'classified', etc.
    payload     JSONB       NOT NULL DEFAULT '{}',
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- No updated_at — this table is append-only
);

-- =============================================================================
-- AUDIT_BUFFER TABLE — Local fallback when DB is unavailable (AG-06)
-- Rows here are flushed to audit_log on reconnect, then deleted.
-- =============================================================================
CREATE TABLE IF NOT EXISTS audit_buffer (
    buffer_id   UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id   VARCHAR(100) REFERENCES tenants(tenant_id),
    payload     JSONB       NOT NULL,               -- same schema as audit_log row
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    flushed     BOOLEAN     DEFAULT FALSE            -- mark True before DELETE on flush
);

-- =============================================================================
-- TENANTS TABLE — Multi-domain / Multi-tenant registry
-- =============================================================================
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id           VARCHAR(100)  PRIMARY KEY,            -- e.g. 'acme_hospital'
    domain_id           VARCHAR(50)   NOT NULL                -- e.g. 'healthcare'
        CHECK (domain_id IN (
            'healthcare', 'it_support', 'billing', 'hr',
            'legal', 'ecommerce', 'education'
        )),
    name                VARCHAR(255)  NOT NULL,               -- 'ACME Hospital Group'
    config_overrides    JSONB         NOT NULL DEFAULT '{}',  -- per-tenant overrides merged
                                                              -- on top of base domain config
    active              BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- ANALYTICS_SNAPSHOTS TABLE — AG-07 KPI snapshots
-- =============================================================================
CREATE TABLE IF NOT EXISTS analytics_snapshots (
    snapshot_id     UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       VARCHAR(100) REFERENCES tenants(tenant_id),
    kpi_snapshot    JSONB       NOT NULL DEFAULT '{}',
    trend_data      JSONB       NOT NULL DEFAULT '{}',
    insight_text    TEXT,
    report_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- INDEXES
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_emails_source        ON emails(source);
CREATE INDEX IF NOT EXISTS idx_emails_current_step  ON emails(current_step);
CREATE INDEX IF NOT EXISTS idx_emails_sender        ON emails(sender);
CREATE INDEX IF NOT EXISTS idx_emails_received_at   ON emails(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_attachments_email_id ON attachments(email_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_email_id   ON audit_log(email_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_agent_id   ON audit_log(agent_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp  ON audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_buffer_flushed ON audit_buffer(flushed);

-- =============================================================================
-- TRIGGER: auto-update updated_at on emails
-- =============================================================================
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_emails_updated_at ON emails;
CREATE TRIGGER trg_emails_updated_at
    BEFORE UPDATE ON emails
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
