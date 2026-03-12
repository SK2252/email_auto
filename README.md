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
