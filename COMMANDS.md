# Quick Command Reference - AI Inbox Management System

All commands should be run from the project root directory: `D:\email_auto`

---

## 🚀 Initial Setup

### 1. Create Python Virtual Environment
```bash
python -m venv .venv
```

### 2. Activate Virtual Environment
**Windows (PowerShell):**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
.venv\Scripts\activate.bat
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Initialize Database
Run the schema setup script:
```bash
python init_db.py
```

Or manually initialize PostgreSQL:
```bash
psql -U postgres -d email_db -f db/schema.sql
```

---

## 🔧 Running Services

### Start Redis (Docker)
```bash
docker-compose up -d
```

Stop Redis:
```bash
docker-compose down
```

### Start Celery Worker with Beat (SLA Monitoring)
```bash
celery -A main.celery_app worker -B -l info
```

Individual commands:
- **Worker only:** `celery -A main.celery_app worker -l info`
- **Beat scheduler only:** `celery -A main.celery_app beat -l info`

### Start MCP Server (Port 9000)
```bash
python run_mcp_server.py
```

### Start Main Polling Loop
```bash
python main.py
```

### Start FastAPI Backend (if separate endpoint needed)
```bash
python mcp_launcher.py
```

---

## 🎨 Frontend (React UI)

### Navigate to UI Directory
```bash
cd ui
```

### Install Node Dependencies
```bash
npm install
```

### Development Server (Vite)
```bash
npm run dev
```

### Build for Production
```bash
npm run build
```

---

## 🧪 Testing & Debugging

### Run Full Pipeline Debug
```bash
python debug_full_pipeline.py
```

### Debug Orchestrator Pipeline
```bash
python debug_orchestrator_pipeline.py
```

### Debug Polling Loop
```bash
python debug_polling_loop.py
```

### Debug Label System
```bash
python debug_labels.py
```

### Test Supabase Connection
```bash
python test_supabase.py
```

### Test Label System
```bash
python test_label_system.py
```

### Test Unknown Tenant Routing
```bash
python test_unknown_tenant.py
```

---

## 📊 Database Operations

### Initialize Database
```bash
python init_db.py
```

### Run Alembic Migrations (if in enterprise-mcp-server)
```bash
cd enterprise-mcp-server
alembic upgrade head
```

---

## 🔌 Deployment & Patching

### Deploy with Validation
```bash
python fixdeploy.py
```

### Patch MCP Server Tools
```bash
python patch_mcp_server.py
```

### Patch Email Tools
```bash
python patch_tools_email.py
```

---

## 👀 Monitoring & Logs

### View Celery Beat Schedule
```bash
celery -A main.celery_app inspect scheduled
```

### View Active Celery Tasks
```bash
celery -A main.celery_app inspect active
```

### View Celery Stats
```bash
celery -A main.celery_app inspect stats
```

### Check Redis Connection
```bash
redis-cli ping
```

### Monitor Redis Keys
```bash
redis-cli KEYS '*'
```

---

## 🔑 Environment Configuration

Create `.env` file in project root with:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/email_db
CELERY_BROKER_URL=redis://localhost:6379/0

# LLM Providers
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
MISTRAL_API_KEY=your_mistral_key

# Slack Integration
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_CHANNEL_SLA_ALERTS=#sla-alerts
SLACK_CHANNEL_ESCALATION=#escalation

# Email Configuration
TEAM_LEAD_EMAIL=teamlead@company.com
GMAIL_CREDENTIALS_PATH=credentials/gmail_credentials.json

# Gmail API (for local testing)
GMAIL_TOKEN_PATH=credentials/gmail_token.json

# MCP Server
MCP_SERVER_PORT=9000

# System
LOG_LEVEL=INFO
ENVIRONMENT=development
```

---

## 📝 Project Structure Quick Reference

| Directory | Purpose |
|-----------|---------|
| `agents/` | LangGraph agents (AG-01 through AG-07) |
| `config/` | Settings and domain configurations |
| `mcp_tools/` | MCP server tools and integrations |
| `utils/` | Utility functions (labels, PII, case ID) |
| `prompts/` | LLM prompt templates |
| `db/` | Database schema and migrations |
| `credentials/` | OAuth tokens and API credentials |
| `ui/` | React + Vite frontend |
| `enterprise-mcp-server/` | Enterprise MCP implementation |

---

## 🚨 Common Issues & Solutions

### Redis Connection Failed
```bash
# Ensure Redis is running
docker-compose up -d
# Verify connection
redis-cli ping
```

### Database Connection Error
```bash
# Check PostgreSQL is running and accessible
# Verify DATABASE_URL in .env
# Initialize database if needed
python init_db.py
```

### MCP Server Port Already in Use
```bash
# Change port in config/settings.py or use:
python run_mcp_server.py --port 9001
```

### Virtual Environment Not Activated
```bash
# Reactivate venv
.\.venv\Scripts\Activate.ps1
# Verify with:
pip --version
```

---

## 🎯 Typical Development Workflow

```bash
# 1. Activate environment
.\.venv\Scripts\Activate.ps1

# 2. Start infrastructure (Redis)
docker-compose up -d

# 3. Start Celery worker with beat (in separate terminal)
celery -A main.celery_app worker -B -l info

# 4. Start MCP server (in separate terminal)
python run_mcp_server.py

# 5. Start main polling loop (in separate terminal)
python main.py

# 6. (Optional) Start UI dev server
cd ui && npm run dev

# 7. Debug/test as needed
python debug_full_pipeline.py
```

---

## ✅ Verification Checklist

- [ ] Virtual environment activated
- [ ] Dependencies installed (`pip list | grep -E "fastapi|langgraph|celery"`)
- [ ] PostgreSQL database initialized
- [ ] Redis running (`redis-cli ping` returns `PONG`)
- [ ] Environment variables loaded (`.env` file exists)
- [ ] MCP server accessible on http://localhost:9000
- [ ] Celery worker started with beat scheduler
- [ ] Main polling loop running without errors

---

**Last Updated:** March 17, 2026  
**Environment:** Windows PowerShell  
**Python Version:** 3.10+
