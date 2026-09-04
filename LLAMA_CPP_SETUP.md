# NEXUS + llama.cpp — balanced VRAM/RAM mode

NEXUS now supports **llama.cpp as the primary local model server**, with Ollama retained as an optional fallback.

## Why this was added

llama.cpp can split model work between GPU VRAM and normal system RAM. The startup profiles control this with `--n-gpu-layers` and use an 8K context by default to avoid the 32K-context VRAM pressure seen with the previous Ollama setup.

## Folder layout

- `runtime/llama.cpp/llama-server.exe` — llama.cpp Windows server binary
- `models/nexus-model.gguf` — your GGUF model

The large binaries/models are intentionally not bundled.

## Start order

1. `START_LLAMA_CPP.bat` — balanced profile (recommended)
2. `START_AGENT.bat` — starts NEXUS API

Other profiles:

- `START_LLAMA_CPP_LOW_VRAM.bat` — only 8 GPU layers; more CPU/RAM, lower VRAM
- `START_LLAMA_CPP_FAST.bat` — maximum GPU offload; fastest but highest VRAM use

## Main settings

`config.json`:

- `llm.provider = llama_cpp`
- `llm.fallback_provider = ollama`
- `llama_cpp.context_tokens = 8192`
- `llama_cpp.gpu_layers = 20`

The batch launchers are the authoritative process settings for context/GPU layers when starting llama.cpp locally.

## Tuning

If VRAM is still too high, lower `--n-gpu-layers` in the balanced BAT from 20 to 16, 12, or 8. If there is plenty of free VRAM and you want more speed, increase it.

NEXUS can check the active backend at:

`GET http://127.0.0.1:8787/llm/status`
