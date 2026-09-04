@echo off
setlocal
title Ollama Universal SuperAgent
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Agent is not installed yet.
  echo Running installer...
  call install.bat
)

curl -s http://127.0.0.1:11434/api/tags >nul 2>nul
if errorlevel 1 (
  echo Starting Ollama...
  start "" /min ollama serve
  timeout /t 3 /nobreak >nul
)

echo.
echo ============================================================
echo OLLAMA UNIVERSAL SUPERAGENT
echo API  : http://127.0.0.1:8787
echo DOCS : http://127.0.0.1:8787/docs
echo Stop : Ctrl+C
echo ============================================================
echo.
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8787
pause
