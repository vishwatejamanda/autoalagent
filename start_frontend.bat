@echo off
echo ========================================================
echo Starting AutoApply AI Frontend (Next.js on Port 3000)...
echo ========================================================
set PATH=C:\Program Files\nodejs;%PATH%
cd /d "%~dp0\frontend"
npm run dev
pause

