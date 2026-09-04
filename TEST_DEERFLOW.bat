@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo   NEXUS V3 - DEERFLOW ENGINE TEST
echo ============================================================
echo.
echo [1/2] Checking engine status...
curl -s http://127.0.0.1:8787/engines/status
echo.
echo.
echo [2/2] Sending an explicit DeerFlow test...
curl -s -X POST http://127.0.0.1:8787/agent/run ^
  -H "Content-Type: application/json" ^
  -d "{\"prompt\":\"Explain in a short paragraph what engine handled this request.\",\"session_id\":\"deerflow-test\",\"engine\":\"deerflow\",\"deerflow_mode\":\"standard\"}"
echo.
pause
