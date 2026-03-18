# Email Auto Codebase: Recent Features & Capabilities Analysis

**Analysis Date**: March 16, 2026  
**Focus**: Features and capabilities suitable for README documentation

---

## 1. MCP Server Functionality

### Description
Enterprise-grade Model Context Protocol (MCP) server exposing 22+ REST API tools for AI-driven email management, file operations, and document processing across filesystem, email, and document domains.

### Location
- **Server Entry**: `mcp_launcher.py`, `run_mcp_server.py`  
- **Server Implementation**: `enterprise-mcp-server/app/mcp_server.py`  
- **Port**: 9000 (localhost)  
- **API Docs**: `http://localhost:9000/docs`

### Key Capabilities

#### Email Tools (16 core + 4 automation)
- **Message Management**: List, fetch, search, send emails; fetch profiles
- **Thread Operations**: List, fetch, search threads; retrieve unanswered messages; thread summarization
- **Draft Handling**: Create drafts, generate reply suggestions, list/delete drafts
- **Automation Features**: 
  - Auto-label messages (AI-powered categorization)
  - Suggest followups (AI conversation continuation)
  - Archive/move to folder operations
  - **Attachment Download** (Phase 5B): Extract raw attachment bytes via `gmail_get_attachment` tool

#### Filesystem Tools (5)
- List directories and search files
- Get file metadata and read file contents
- Write files (for document generation)

#### Document Tools (5)
- Generate grouped Excel files from structured data
- Generate notices with PDF attachments
- Merge folder hierarchies
- Validate document requests
- Run document workflows

#### Job Orchestrator Tools (2)
- Submit background jobs
- Monitor job status and progress

### Recent Additions
- **Gmail Attachment Support**: New `gmail_get_attachment` tool enables attachment extraction (base64url encoding)
- **Patch System**: `patch_mcp_server.py` and `patch_tools_email.py` safely register new tools without manual edits

---

## 2. New Agents & Agent Capabilities

### Orchestration Architecture
Seven specialized agents orchestrated via **LangGraph StateGraph**, executing in sequence with parallel execution where possible:

| Agent | Code | Purpose | Status |
|-------|------|---------|--------|
| **AG-01** | `intake_agent.py` | Gmail/Outlook polling, ID generation, auto-ACK | Production |
| **AG-02** | `classification_agent.py` | Category, priority, SLA, sentiment analysis | Production |
| **AG-03** | `routing_agent.py` | Rule-based deterministic team assignment | Production |
| **AG-04** | `response_agent.py` | Template/freeform drafting, auto-send gating | Production |
| **AG-05** | `sla_agent.py` | SLA timer + Celery Beat scheduling | Production |
| **AG-06** | `audit_agent.py` | Event drain & append-only PostgreSQL logging | Production |
| **AG-07** | *(analytics_agent)* | Analytics aggregations | Phase 4 (Planned) |

### Recent Capabilities

#### AG-01: Intake Agent (Polling & Normalization)
- Real-time Gmail inbox polling (configurable interval, default 30s)
- Duplicate detection via external ID and sender+subject fingerprinting (10-min window)
- Case ID generation (`CASE-YYYYMMDD-{uuid[:6]}`)
- Thread context retrieval (fetches full conversation history)
- Automatic acknowledgement (ACK) for supporters
- Domain-based configuration loading

#### AG-02: Classification Agent (Batched LLM)
- Groq API integration (Llama 3.3 70b, 30 RPM rate limit)
- Per-email classification: category, priority (High/Medium/Low), SLA determination
- Sentiment analysis (-1.0 to +1.0 scoring)
- Strict rate-limiting via token bucket (in-process, Redis-ready architecture)

#### AG-03: Routing Agent (Deterministic Matrix)
- Rule-based team assignment (IT, HR, Billing, Legal, Healthcare, Education, Ecommerce)
- Fallback to Gemini Flash-Lite LLM if rule matching fails
- Team lead escalation after 2 LLM failures
- New Event Loop Pattern (fixes `asyncio.get_event_loop()` deprecation)

#### AG-04: Response Agent (PII-Guarded)
- **Auto-Send Gate** (exact design doc conditions):
  - Confidence ≥ 0.90
  - Sentiment ≥ -0.3
  - Non-Healthcare, Non-Legal domains
  - PII scan passes
- **Two Paths**:
  - Auto-send: LLM fills canned templates (no freewrite)
  - Human review: Gemini drafts freely; analyst edits before send
- Hard-block PII detection with compliance alerts to Slack `#compliance-alerts`

#### AG-05: SLA Agent (Celery + Redis)
- Runs on 5-minute Celery Beat schedule
- Computes elapsed SLA windows
- Warnings at 80% breach → Slack `#sla-alerts` channel
- Full breach (100%) → Team Lead DM + reassignment
- Redis deduplication prevents duplicate notifications

#### AG-06: Audit & Compliance Agent
- Async event drain from `event_queue` across state
- Append-only PostgreSQL logging
- In-memory failsafe buffer (auto-flushes on DB reconnection)
- Full compliance audit trail

### Parallel Execution
- AG-03 (Routing) and AG-05 (SLA) execute in parallel post-classification via LangGraph `Send()` branching

---

## 3. UI/Frontend Functionality

### Architecture
React + TypeScript frontend integrated with AI Inbox Management backend.

### Location
- **UI Root**: `ui/` directory
- **AI Studio Link**: https://ai.studio/apps/drive/169t5An7GXs9wtDbJsHJN7mOHLBtHipQr
- **Build Tool**: Vite
- **Dependencies**: Node.js

### Key Components

#### EmailInbox Component (`EmailInbox.tsx`)
- Main inbox view with real-time SSE (Server-Sent Events) updates
- Paginated email list with filtering
- Status tracking across agent pipeline stages

#### ChatInterface Component (`ChatInterface.tsx`)
- AI chat interface for email-related queries
- Gemini direct integration (currently)
- Query suggestions and followup generation

#### Sidebar Component (`Sidebar.tsx`)
- Navigation and session management
- Tenant context switching

#### Service Layer
- **orchestratorService.ts**: Backend communication service
- Current backend endpoint: port 8001 (configurable)

### Integration Plan (Phase 2)
The codebase includes `UI_INTEGRATION_PLAN.md` detailing planned REST API endpoints:

#### Required Backend Endpoints
- `GET /api/v1/emails` — Paginated email list with filtering
  - Query parameters: page, limit, status, priority, category, tenant_id, date_from, date_to, search
  - Returns email metadata + classification results + routing decisions + SLA info
  
- **Status**: Currently in MCP server foundation; REST layer under development
- **Database**: PostgreSQL with tables: `emails`, `audit_log`, `attachments`, `tenants`, `analytics_snapshots`

---

## 4. Debugging & Testing Utilities

### Debug Scripts (8 total)

| Script | Purpose | Scope |
|--------|---------|-------|
| `debug_full_pipeline.py` | End-to-end label pipeline test | Fetch → Classify → Label → Verify |
| `debug_labels.py` | Gmail label diagnostic | API connectivity, label enumeration |
| `debug_orchestrator_pipeline.py` | LangGraph orchestrator execution | Full agent pipeline with real email |
| `debug_polling_loop.py` | Intake agent polling verification | Gmail polling loop functionality |
| N/A | *Analytics/Insight debugging* | Not yet observed in codebase |

### Test Suite (5 total)

| Test File | Coverage |
|-----------|----------|
| `test_label_system.py` | Comprehensive label pipeline (bootstrap, apply, full orchestrator, polling) |
| `test_supabase.py` | PostgreSQL/Supabase database connectivity |
| `test_unknown_tenant.py` | Tenant routing & fallback behavior |
| `test_pii_scanner.py` | *(Not yet located; exists per references)* |
| `test_lm_models.py` | *(Not yet located; exists per references)* |

### Debug Output Features
- UTF-8 console encoding fix for Windows (`sys.stdout.buffer` wrapping)
- Structured JSON logging for all pipeline stages
- Label cache inspection (`_label_cache`, `_managed_label_ids`)
- Error traceback capturing and formatting

---

## 5. Recent Tooling Additions

### Patch & Deploy System

#### `patch_mcp_server.py`
- **Purpose**: Auto-register `gmail_get_attachment` tool in MCP server
- **Idempotency**: Safe to run multiple times (checks for existing registration)
- **Location Strategy**: Searches multiple candidate paths before prompting manual edit
- **Output**: Confirms tool registration or provides fallback instructions

#### `patch_tools_email.py`
- **Purpose**: Append new email tools to `tools_email.py` module
- **Implementation**: Inserts `gmail_get_attachment` function with full docstring
- **Safety**: Idempotent (skips if function already exists)
- **Scope**: Base64url attachment handling

#### `fixdeploy.py`
- **Purpose**: Batch deployment of verified fixes to production files
- **Deployment Manifest**: 6-file deploy list (see below)
- **Verification Checks**: Post-deploy validation via AST parsing
  - Example: Ensures no `asyncio.run()` inside class methods
  - Validates event loop creation pattern (`asyncio.new_event_loop()`)
  - Confirms parameter naming (`message_ids` as list, `folder_label` correct)

### Deployment Files
```
gmail_client.py          → mcp_tools/
routing_agent.py         → agents/
orchestrator.py          → agents/
gmail_label_manager.py   → utils/
intake_agent.py          → agents/
audit_agent.py           → agents/
```

### Database & Init Scripts
- `db/schema.sql` — PostgreSQL schema initialization
- `init_db.py` — Database table creation and seed logic

---

## 6. LLM Client Capabilities

### Location
`mcp_tools/llm_client.py`

### Abstraction Layer
Unified LLM provider interface supporting three free-tier providers:

#### Supported Providers

| Provider | Model | API Style | Rate Limit |
|----------|-------|-----------|-----------|
| **Groq** | Llama 3.3 70b Versatile | OpenAI-compatible | 30 RPM (classification agent) |
| **Gemini** | Gemini 2.5 Flash-Lite | Google GenAI SDK | Custom (routing fallback, response drafts) |
| **Mistral** | Mistral Small Latest | OpenAI-compatible | *(Configurable)* |

### Key Features

#### Rate Limiting
- **Sliding-window implementation** with per-provider token buckets
- In-process simplification (Redis-ready for multi-worker deployments)
- Automatic wait/block when RPM quota exhausted
- JSON-formatted throttle warnings

#### LLM Configuration
- **Swap provider via `settings.py` only** — no hardcoding in agent files
- **Temperature control** (default 0.2 for deterministic responses)
- **Max tokens** configuration per call (default 1024)
- **Request timeouts** (30s default)

#### OpenAI-Compatible Abstraction
- `_call_openai_compat()` function for Groq/Mistral
- Headers construction with Bearer token
- Payload formatting (model, messages, temperature, max_tokens)
- HTTP error handling via httpx

#### Gemini SDK Integration
- Direct Google genai library calls
- Custom prompt formatting
- Streaming/non-streaming modes

### Configuration
Settings pulled from `config/settings.py`:
- `GROQ_API_KEY`
- `GEMINI_API_KEY`
- `MISTRAL_API_KEY`

---

## 7. Gmail Label Management Features

### Location
`utils/gmail_label_manager.py`

### 2-Level Classification System
**Level 1 (7 Categories)**: Billing, IT Support, HR, Complaint, Query, Escalation, Other  
**Level 2 (4 Priorities)**: High, Medium, Low

### Label Mapping & Legacy Aliases

#### Category Mapping
Includes 60+ legacy aliases (stale LLM response names) mapped to canonical categories:
- `inquiry` → Query
- `technical_issue` → IT Support
- `refund` → Billing
- `leave` → HR
- `negative_feedback` → Complaint
- *(...and 55 more)*

#### Auto-Correction Features
- Typo tolerance: `tech_support`, `technical_support` → IT Support
- Domain-specific IT: `password_reset`, `hardware_issue`, `network_issue` → IT Support
- Billing variations: `payment_issue`, `invoice_issue`, `charge_issue` → Billing
- HR variations: `employee_issue`, `workplace_issue` → HR

### Bootstrap & Idempotency

#### `bootstrap_labels()`
- Creates 28 managed labels (7 categories × 4 priorities)
- Caches labels in `_label_cache` dictionary
- Stores managed label IDs in `_managed_label_ids` list
- **Duplicate prevention**: Checks existing Gmail labels before creating
- **Redis-backed**: Stores label cache keys for multi-worker consistency

#### Duplicate Prevention (Sprint 10)
- Robust ID collision detection
- Cross-worker deduplication via Redis
- Idempotent label creation (safe to run repeatedly)

### Application Functions

#### `apply_classification_label()`
- Maps LLM classification output to Gmail label
- Resolves legacy aliases automatically
- Handles missing/invalid categories (fallback to "Other")
- Async Gmail API integration

#### In-Process Caching
- `_label_cache`: Maps display names → Gmail label IDs
- `_managed_label_ids`: List of all created label IDs
- Fast lookup without repeated API calls

---

## 8. Case ID Generation & Utilities

### Location
`utils/case_id_generator.py`

### Case ID Format
```
CASE-{YYYYMMDD}-{UUID[:6]}
Example: CASE-20260314-a1b2c3
```

### Characteristics
- **Date Component**: ISO format `YYYYMMDD` for chronological sorting
- **UUID Component**: First 6 characters of Python UUID v4
- **Deterministic**: Same email generates same case ID (no randomization per call)
- **Human-Readable**: Sortable and easy to reference in support conversations

### Integration Points
- **AG-01 (Intake Agent)**: Generates case ID for each ingested email
- **Audit Trail**: Case ID links emails across all agent stages
- **UI Display**: Shows case reference in inbox view
- **Slack/Email**: Referenced in notifications and alert messages

### Additional Utilities

#### Domain Loader (`utils/domain_loader.py`)
- Loads domain/industry configurations from `config/domains/`
- Gets SLA rules per domain
- Determines auto-send permissions per domain (e.g., disallows Healthcare/Legal)

#### PII Scanner (`utils/pii_scanner.py`)
- Hard-blocks response generation if PII detected
- Detects: SSN, credit card, passport, medical records, etc.
- Compliance alert to Slack on detection

#### Retry Utils (`utils/retry_utils.py`)
- `retry_with_backoff()` for transient failures
- Dead letter queue support for unrecoverable errors
- Exponential backoff with jitter

---

## Summary Table: Recent Additions

| Feature | Component | Status | Maturity |
|---------|-----------|--------|----------|
| **Attachment Download** | `gmail_get_attachment` MCP tool | Sprint 5B | Beta |
| **Label Auto-Correction** | 60+ legacy alias mappings | Sprint 10 | Production |
| **Parallel Agent Execution** | AG-03 + AG-05 branching | Sprint 9 | Production |
| **PII Hard-Block** | Response Agent gating | Sprint 7-8 | Production |
| **Celery Beat SLA** | Background SLA monitoring | Sprint 9 | Production |
| **MCP Patch System** | Auto-registration tools | Recent | Production |
| **UI Integration Layer** | orchastrator Service + API plan | Phase 2 | Design |
| **Rate-Limited LLM** | Groq 30 RPM abstraction | Sprint 2 | Production |

---

## Recommended README Updates

### Sections to Add/Expand
1. **MCP Server Tools** - Document all 22+ tools with usage examples
2. **Agent Pipeline** - Expand AG-01 through AG-06 capabilities matrix
3. **Label Management** - Detail 7-category + 4-priority system
4. **Debugging Guide** - Document debug_*.py scripts and expected outputs
5. **LLM Configuration** - Provider switching instructions
6. **UI Integration** - Link to `UI_INTEGRATION_PLAN.md` for Phase 2 integration

### Key Links to Reference
- API Docs: `http://localhost:9000/docs` (when server running)
- UI Studio: https://ai.studio/apps/drive/169t5An7GXs9wtDbJsHJN7mOHLBtHipQr
- Database Schema: `db/schema.sql`
- Configuration: `config/settings.py`
