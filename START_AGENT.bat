@echo off
setlocal
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
title NEXUS Local AI SuperAgent
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Agent is not installed yet.
  echo Running installer...
  call install.bat
  if errorlevel 1 (
    echo.
    echo [ERROR] NEXUS installation did not complete.
    pause
    exit /b 1
  )
)

echo Checking llama.cpp...
curl -s http://127.0.0.1:8080/health >nul 2>nul
if errorlevel 1 (
  echo [ERROR] llama.cpp is not running on http://127.0.0.1:8080
  echo Start llama.cpp first, then run START_AGENT.bat again.
  echo.
  echo Example:
  echo llama-server -m "models\nexus-model.gguf" -c 8192 -ngl 20 --host 127.0.0.1 --port 8080
  pause
  exit /b 1
)

echo [OK] llama.cpp is online.
echo.
echo ============================================================
echo NEXUS LOCAL AI SUPERAGENT
 echo LLM  : llama.cpp http://127.0.0.1:8080
 echo API  : http://127.0.0.1:8787
 echo DOCS : http://127.0.0.1:8787/docs
 echo Stop : Ctrl+C
 echo ============================================================
echo.
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8787
pause
