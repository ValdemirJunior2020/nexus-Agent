@echo off
setlocal EnableExtensions
title NEXUS llama.cpp Balanced VRAM + RAM
cd /d "%~dp0"

set "SERVER=%~dp0runtime\llama.cpp\llama-server.exe"
if not exist "%SERVER%" set "SERVER=%~dp0runtime\llama.cpp\llama-server"
set "MODEL=%~dp0models\nexus-model.gguf"

if not exist "%SERVER%" (
  echo [ERROR] llama.cpp server was not found.
  echo.
  echo Put llama-server.exe and its required DLL files in:
  echo   %~dp0runtime\llama.cpp\
  echo.
  echo Then run this file again.
  pause
  exit /b 1
)

if not exist "%MODEL%" (
  echo [ERROR] GGUF model was not found.
  echo.
  echo Put your GGUF model here and rename it to:
  echo   %MODEL%
  echo.
  echo Recommended for this PC: a Q4_K_M or Q5_K_M instruct model.
  pause
  exit /b 1
)

REM Balanced profile: some model layers on GPU, remaining layers in system RAM.
REM Lower --n-gpu-layers if you want less VRAM. Raise it for more speed.
set "GPU_LAYERS=20"
set "CTX=8192"
set "THREADS=8"
set "PARALLEL=1"

echo ============================================================
echo NEXUS llama.cpp - BALANCED VRAM / RAM
 echo Model      : %MODEL%
echo GPU layers  : %GPU_LAYERS%
echo Context     : %CTX%
echo API         : http://127.0.0.1:8080
echo ============================================================
echo.

"%SERVER%" -m "%MODEL%" --alias nexus-local --host 127.0.0.1 --port 8080 --n-gpu-layers %GPU_LAYERS% --ctx-size %CTX% --threads %THREADS% --parallel %PARALLEL%
pause
