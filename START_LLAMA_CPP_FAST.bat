@echo off
setlocal EnableExtensions
title NEXUS llama.cpp Fast GPU
cd /d "%~dp0"
set "SERVER=%~dp0runtime\llama.cpp\llama-server.exe"
if not exist "%SERVER%" set "SERVER=%~dp0runtime\llama.cpp\llama-server"
set "MODEL=%~dp0models\nexus-model.gguf"
if not exist "%SERVER%" (echo [ERROR] Missing runtime\llama.cpp\llama-server.exe & pause & exit /b 1)
if not exist "%MODEL%" (echo [ERROR] Missing models\nexus-model.gguf & pause & exit /b 1)
REM Fast profile: many layers on GPU. Uses substantially more VRAM.
"%SERVER%" -m "%MODEL%" --alias nexus-local --host 127.0.0.1 --port 8080 --n-gpu-layers 999 --ctx-size 8192 --threads 8 --parallel 1
pause
