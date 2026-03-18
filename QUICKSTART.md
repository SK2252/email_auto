# ⚡ Quick Start Guide - 5 Minutes to Running

Get the AI Inbox Management System up and running in 5 minutes.

## Option 1: Interactive Command Runner (Easiest) ✨

```powershell
# 1. Navigate to project
cd D:\email_auto

# 2. Run the interactive command runner
.\run_commands.ps1

# 3. Follow the menu prompts:
#    1.1 - Create venv
#    1.2 - Activate venv
#    1.3 - Install dependencies
#    1.4 - Initialize database
#    2.1 - Start Redis
#    2.3 - Start Celery worker
#    2.4 - Start MCP server
#    2.5 - Start polling loop
```

## Option 2: Manual Commands (Step-by-Step)

### Terminal 1: Setup
```powershell
cd D:\email_auto
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python init_db.py
```

### Terminal 2: Infrastructure
```powershell
docker-compose up -d
```

### Terminal 3: Celery & SLA Monitoring
```powershell
cd D:\email_auto
.\.venv\Scripts\Activate.ps1
celery -A main.celery_app worker -B -l info
```

### Terminal 4: MCP Server
```powershell
cd D:\email_auto
.\.venv\Scripts\Activate.ps1
python run_mcp_server.py
```

### Terminal 5: Main Application
```powershell
cd D:\email_auto
.\.venv\Scripts\Activate.ps1
python main.py
```

### Terminal 6 (Optional): UI Development
```powershell
cd D:\email_auto\ui
npm install
npm run dev
```

---

## ✅ Verify Everything is Running

### Check MCP Server
```powershell
# Should return 22+ available tools
curl http://localhost:9000/tools -s | ConvertFrom-Json | ForEach-Object { $_.tools.Count }
```

### Check Redis
```powershell
redis-cli ping
# Expected: PONG
```

### Check Celery Workers
```powershell
celery -A main.celery_app inspect active
# Should show worker status
```

### Verify Database Connection
```powershell
$env:DATABASE_URL
# Should show your PostgreSQL connection string
```

---

## 🔑 Required Environment Variables

Create `.env` file in project root with **at minimum**:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/email_db
CELERY_BROKER_URL=redis://localhost:6379/0
GROQ_API_KEY=your_api_key_here
```

---

## 🚨 Common Quick Fixes

**Is Redis failing to start?**
```powershell
docker ps                    # Check if running
docker-compose restart       # Restart
docker logs email_auto_redis # Check logs
```

**Is venv not activating?**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\.venv\Scripts\Activate.ps1
```

**Is a port already in use?**
```powershell
# Find process using port 9000
netstat -ano | findstr :9000
# Kill process (replace PID)
taskkill /PID <PID> /F
```

---

## 📊 System Architecture at a Glance

```
Email Source (Gmail/Outlook)
         ↓
    [AG-01: Intake] → Normalize, Case ID
         ↓
  [AG-02: Classification] → Category, Priority, SLA
         ↓
  [AG-03: Routing] ↔ [AG-05: SLA] (Parallel)
         ↓
 [AG-04: Response] → PII Check, Auto-Send
         ↓
[AG-06: Audit] → Append Logs
         ↓
  PostgreSQL + Slack + Email Response
```

---

## 🎯 Next Steps

1. **Check logs**: Monitor all terminals for errors
2. **Test intake**: Send test email to configured Gmail account
3. **Debug if needed**: Run `python debug_full_pipeline.py`
4. **Review docs**: Read full [COMMANDS.md](COMMANDS.md) for advanced options
5. **Explore UI**: Launch frontend at http://localhost:5173

---

## 💡 Pro Tips

- Keep a **terminal multiplexer** (Windows Terminal tabs) open for all 6 services
- Use `run_commands.ps1` menu to run any command without remembering syntax
- Check logs in real-time with `Get-Content -Path logfile.txt -Wait`
- Use `Redis Desktop Manager` GUI for visual Redis monitoring
- Enable debug mode in config/settings.py for detailed logging

---

## ❌ Troubleshooting

| Issue | Solution |
|-------|----------|
| "Module not found" | Re-activate venv: `.\.venv\Scripts\Activate.ps1` |
| "Connection refused" | Start Redis: `docker-compose up -d` |
| "Port already in use" | Check with `netstat -ano \| findstr :9000` |
| "Database error" | Run `python init_db.py` to initialize |
| "Permission denied" | Run PowerShell as Administrator |

---

**Ready to test full pipeline?**
```powershell
python debug_full_pipeline.py
```

**Questions? See full documentation in [COMMANDS.md](COMMANDS.md)**
