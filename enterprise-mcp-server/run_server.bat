@echo off
echo ===================================================
echo Starting Enterprise MCP Server Architecture
echo ===================================================

echo [1/3] Starting Celery Worker...
start "Celery Worker" cmd /c "cd /d "%~dp0" && call ..\..\venv\Scripts\activate.bat && celery -A app.core.celery_app worker --loglevel=info -P solo"

echo [2/3] Starting Celery Beat Scheduler (15-second loop)...
start "Celery Beat" cmd /c "cd /d "%~dp0" && call ..\..\venv\Scripts\activate.bat && celery -A app.core.celery_app beat --loglevel=info"

echo [3/3] Starting FastAPI Backend on Port 9000...
echo.
echo The API is now running. Press Ctrl+C in this window to stop it.
call ..\..\venv\Scripts\activate.bat
uvicorn app.api.main:app --port 9000 --reload
