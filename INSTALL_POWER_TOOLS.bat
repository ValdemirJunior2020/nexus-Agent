@echo off
setlocal
title Ollama Universal SuperAgent - Power Tools
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Run install.bat first.
  pause
  exit /b 1
)

echo ============================================================
echo OLLAMA SUPERAGENT - OPTIONAL POWER TOOLS
echo Browser Use + MCP + Agent Reach safe install
echo ============================================================
echo.

echo [1/4] Installing Browser Use and MCP SDK...
".venv\Scripts\python.exe" -m pip install -r requirements-power-tools.txt
if errorlevel 1 goto :fail

echo.
echo [2/4] Installing Browser Use Chromium...
if exist ".venv\Scripts\browser-use.exe" (
  ".venv\Scripts\browser-use.exe" install
) else (
  ".venv\Scripts\python.exe" -m browser_use install
)
if errorlevel 1 echo [WARN] Browser install command failed. Browser Use package is still installed.

echo.
echo [3/4] Installing Agent Reach Python package...
".venv\Scripts\python.exe" -m pip install "https://github.com/Panniantong/agent-reach/archive/main.zip"
if errorlevel 1 echo [WARN] Agent Reach package install failed. Other power tools remain usable.

echo.
echo [4/4] Running Agent Reach SAFE setup (no automatic system-package changes)...
if exist ".venv\Scripts\agent-reach.exe" (
  ".venv\Scripts\agent-reach.exe" install --env=auto --safe
  ".venv\Scripts\agent-reach.exe" doctor
) else (
  echo [WARN] agent-reach command not found in venv.
)

echo.
echo ============================================================
echo POWER TOOLS SETUP COMPLETE

echo Restart START_AGENT.bat after this window closes.
echo Check: http://127.0.0.1:8787/tools/status
echo ============================================================
pause
exit /b 0

:fail
echo [ERROR] Power tool dependency installation failed.
pause
exit /b 1
