# AI Inbox Management System

A production-grade Multi-Agent AI system designed to intelligently manage high-volume customer support and enterprise inboxes. Powered by LangGraph, Groq, Gemini, and Mistral.

## Architecture & Flow

The system orchestrates a pipeline of specialized agents built on LangGraph, processing each incoming email through a unified schema.

1.  **AG-01 Intake Agent:** Polls sources (Gmail, Outlook, Zendesk, Freshdesk), normalizes email structures, generates case IDs, logs `email_ingested` audit events, and handles automatic acknowledgements securely.
2.  **AG-02 Classification Agent:** Uses a batched Groq (Llama 3.3 70b) call to perform category classification, priority assignment, SLA determination, and sentiment analysis within a strict 30 RPM limit constraint.
3.  **AG-03 Routing Agent:** Executes a deterministic rule-based matrix to assign tickets to appropriate teams (IT, HR, Billing, etc.). Falls back to a resilient Gemini Flash-Lite LLM step when rules fail, with team lead escalations after 2 failures.
4.  **AG-04 Response Agent:** Generates template-constrained or free-form responses based on an Auto-Send Gate logic (Confidence > 0.90, Sentiment > -0.3, strictly non-Healthcare/non-Legal domains). Enforces a hard block on PII (via `utils/pii_scanner.py`) before ever generating or sending a draft.
5.  **AG-05 SLA Agent (Celery):** Runs independently via a 5-minute Celery beat schedule to compute elapsed SLA windows. Dispatches warnings to a specific Slack `#sla-alerts` channel at 80%, and reassigns the email with a Team Lead DM at 100% breach. Uses Redis for deduplication.
6.  **AG-06 Audit & Compliance Agent:** A universally injected node that drains `event_queue` tracking variables across the LangGraph state. Writes append-only logs directly to PostgreSQL with an in-memory failsafe buffer that flushes automatically upon database reconnection.
7.  **AG-07 Analytics Agent (Phase 4):** Processes insights and aggregations against the PostgreSQL database.

## Parallel Execution & Optimization

The system employs advanced parallelization for performance:
- **AG-03 Routing** and **AG-05 SLA** run concurrently post-classification (after AG-02 completes).
- **Duplicate detection** (AG-01) uses external ID fingerprinting combined with sender/subject hashing to prevent redundant ingestion.
- **PII enforcement** (AG-04) applies categorical domain gating: Auto-send is strictly blocked for Healthcare and Legal domains regardless of confidence scores.

## MCP Server & Tools Suite

The system includes a production-ready **Model Context Protocol (MCP) server** running on port 9000, providing 22+ integrated tools:

### Gmail Tools (20)
- **Core Operations (10):** `gmail_list_messages`, `gmail_get_message`, `gmail_search_messages`, `gmail_send_message`, `gmail_move_message`, `gmail_archive_message`, `gmail_mark_read`, `gmail_get_labels`, `gmail_modify_labels`, `gmail_get_attachment`
- **Automation Tools (10):** Auto-reply setup, label management, vacation settings, filter creation, and batch operations

### Filesystem & Document Tools
- Safe file system access with configurable path restrictions
- Document parsing and processing utilities

### Key Features
- **Attachment Handling:** Base64url encoded retrieval with automatic decoding support
- **Rate Limiting:** Groq API constrained to 30 RPM with sliding-window enforcement
- **Safe Registration:** Idempotent MCP tool registration with validation layer

### Running the MCP Server
```bash
python run_mcp_server.py
# Server runs on http://localhost:9000
```

## Gmail Label Management

The system maintains a comprehensive label taxonomy:
- **28 Dynamic Labels:** Organized as 7 categories (Billing, HR, IT, Legal, Healthcare, Education, Ecommerce) × 4 priority levels (Critical, High, Medium, Low)
- **60+ Legacy Alias Mappings:** Robust deduplication for stale LLM responses that reference outdated label names
- **Redis Cache:** Sprint 10 deduplication layer prevents duplicate label assignments

Access via `utils/gmail_label_manager.py` for label creation, validation, and mapping operations.

## Case ID System

All tickets are tracked using a globally unique, sortable identifier:
```
Format: CASE-YYYYMMDD-{UUID[:6]}
Example: CASE-20260316-a7f2e1
```

Benefits:
- Human-readable and debuggable
- Chronologically sortable for historical queries
- Consistent across all agent stages and audit logs

## User Interface (Phase 2)

A React + Vite frontend is included with components for:
- **Email Inbox:** Display and filtering of managed emails
- **Chat Interface:** Direct interaction with the agent pipeline
- **Status Dashboard:** Real-time pipeline execution and SLA monitoring

The UI is integrated with the MCP server foundation and awaits REST API endpoint implementation for full functionality. Build and serve via:
```bash
cd ui
npm install
npm run dev
```

## Debugging & Testing

Comprehensive suite of debug and test utilities:

### Debug Scripts
- `debug_full_pipeline.py` — Trace complete email-to-response flow
- `debug_orchestrator_pipeline.py` — Test multi-agent orchestration
- `debug_polling_loop.py` — Verify Gmail polling and intake
- `debug_labels.py` — Validate label creation and application

### Test Suites
- `test_supabase.py` — Database connectivity
- `test_label_system.py` — Label taxonomy and aliases
- `test_unknown_tenant.py` — Multi-tenant routing edge cases

All test scripts include UTF-8 encoding fixes for Windows environments and structured JSON logging.

## LLM Provider Configuration

The system supports swappable LLM providers (Groq, Gemini, Mistral) configured once in `config/settings.py`:

```python
# config/settings.py
LLM_PROVIDER = "groq"  # or "gemini", "mistral"
GROQ_API_KEY = "..."
GEMINI_API_KEY = "..."
MISTRAL_API_KEY = "..."
GROQ_RATE_LIMIT = 30  # requests per minute
```

Provider configuration is centralized—no hardcoding in agent code.

## Deployment & Tooling

### Deployment Tool
`fixdeploy.py` — Batch deployment with AST verification:
- Validates no `asyncio.run()` calls within class methods
- Checks event loop patterns for compatibility
- Idempotent tool registration system

### Patch System
Safe updates to MCP tools via `patch_tools_email.py` and `patch_mcp_server.py` with built-in validation.

## Prerequisites & Setup

Requires Python 3.10+ (recommend 3.11+).

1.  **Clone down the application**
2.  **Create your Python Virtual Environment**:
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    ```
3.  **Install requirements**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Database Configuration**:
    Install, run, and configure local PostgreSQL and Redis instances. The backend defaults to `redis://localhost:6379/0` and standard pg credentials natively inside the `.env`.

5.  **Environment Variables**:
    Create `.env` using `.env.example` (or existing `config/settings.py` structure).
    Key exports needed:
    *   `DATABASE_URL` (e.g. `postgresql+asyncpg://user:pass@localhost:5432/email_db`)
    *   `CELERY_BROKER_URL`
    *   `GROQ_API_KEY`, `GEMINI_API_KEY`, `MISTRAL_API_KEY`
    *   `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_*`
    *   `TEAM_LEAD_EMAIL`

## Local Development

*   **Celery Workers**:
    Run standard command: `celery -A main.celery_app worker -B -l info`
*   **Postgres Initialization**:
    Run `db/schema.sql` to initialize `emails`, `audit_log`, `attachments`, `tenants`, and `audit_buffer` tables.

## Phase 1 Limitations / Technical Debt

This represents the MVP release (up through Sprint 9 of the design doc).
*   **External Ticketing**: CRM APIs (Salesforce, HubSpot, ServiceNow, Jira, Freshdesk) are abstracted away (Phase 2).
*   **Email Clients Wrapper**: OAuth exists and `mcp.py` bridges the APIs natively, but a continuous polling logic loop (the primary `main.py` entrypoint) and the REST endpoint definitions have not been fully constructed yet.

## License

Internal Enterprise Deployment. Not for public distribution.
