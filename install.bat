@echo off
setlocal
title Ollama Universal SuperAgent Installer
cd /d "%~dp0"

echo ============================================================
echo   OLLAMA UNIVERSAL SUPERAGENT - INSTALL
echo ============================================================
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python launcher "py" was not found.
  echo Install Python 3.11 or 3.12, then run this file again.
  pause
  exit /b 1
)

where ollama >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Ollama was not found in PATH.
  echo Install Ollama first, then run this installer again.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/4] Creating Python environment...
  py -3 -m venv .venv 2>nul
  if errorlevel 1 py -m venv .venv
)

echo [2/4] Updating pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip

echo [3/4] Installing agent dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] Dependency installation failed.
  pause
  exit /b 1
)

echo [4/4] Checking Ollama...
curl -s http://127.0.0.1:11434/api/tags >nul 2>nul
if errorlevel 1 (
  echo Ollama is installed but not responding. Starting it...
  start "" /min ollama serve
  timeout /t 3 /nobreak >nul
)

echo.
echo ============================================================
echo INSTALL COMPLETE
echo Run START_AGENT.bat
echo API: http://127.0.0.1:8787
echo Docs: http://127.0.0.1:8787/docs
echo ============================================================
pause
