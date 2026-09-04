@echo off
setlocal
title NEXUS Local AI SuperAgent Installer
cd /d "%~dp0"

echo ============================================================
echo   NEXUS LOCAL AI SUPERAGENT - INSTALL
echo   Primary local model server: llama.cpp
echo ============================================================
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python launcher "py" was not found.
  echo Install Python 3.11 or 3.12, then run this file again.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creating Python environment...
  py -3 -m venv .venv 2>nul
  if errorlevel 1 py -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Could not create the Python virtual environment.
    pause
    exit /b 1
  )
) else (
  echo [1/3] Python environment already exists.
)

echo [2/3] Updating pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
  echo [ERROR] pip upgrade failed.
  pause
  exit /b 1
)

echo [3/3] Installing NEXUS dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] Dependency installation failed.
  pause
  exit /b 1
)

echo.
echo Checking llama.cpp server on http://127.0.0.1:8080 ...
curl -s http://127.0.0.1:8080/health >nul 2>nul
if errorlevel 1 (
  echo [WARN] llama.cpp is not running yet.
  echo Start it first with START_LLAMA_CPP.bat or your llama-server command.
) else (
  echo [OK] llama.cpp is running.
)

echo.
echo ============================================================
echo INSTALL COMPLETE
echo Run START_AGENT.bat
echo API : http://127.0.0.1:8787
echo Docs: http://127.0.0.1:8787/docs
echo ============================================================
exit /b 0
