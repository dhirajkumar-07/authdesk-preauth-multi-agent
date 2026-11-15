@echo off
echo Starting AuthDesk Server on http://127.0.0.1:8000 ...
cd /d "%~dp0"
if exist "authdesk-kit\app\main.py" (
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --app-dir "authdesk-kit"
) else (
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
)
pause

