@echo off
setlocal
cd /d "%~dp0"
echo.
echo ============================================================
echo   NEXUS - EXPORT ERROR LOGS FOR JUNIOR
echo ============================================================
echo.

if exist ".venv\Scripts\python.exe" (
  set "PY=.venv\Scripts\python.exe"
) else (
  set "PY=python"
)

%PY% -c "from app.error_logging import export_logs; print(export_logs())"
if errorlevel 1 (
  echo.
  echo [ERROR] Could not export the NEXUS logs.
  pause
  exit /b 1
)

echo.
echo Done. Send the NEXUS_ERROR_REPORT_*.zip file to Junior for review.
echo.
pause
