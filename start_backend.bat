@echo off
echo ========================================================
echo Starting AutoApply AI Backend (FastAPI on Port 8000)...
echo ========================================================
cd /d "%~dp0\backend"
python -m uvicorn app.main:app --reload --port 8000
pause

