@echo off
echo Testing Ollama Universal SuperAgent...
curl -X POST http://127.0.0.1:8787/agent/run ^
  -H "Content-Type: application/json" ^
  -d "{\"prompt\":\"Explain in one paragraph what you can do and verify your answer before returning it.\",\"mode\":\"deep\",\"session_id\":\"test\"}"
echo.
pause
