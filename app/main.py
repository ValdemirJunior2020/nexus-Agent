import time
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import AgentRequest, AgentResponse, OpenAIChatRequest
from .orchestrator import SuperAgent
from .ollama_client import OllamaClient
from .config import CONFIG
from .tools.registry import status as tools_status
from .tools.mcp_adapter import mcp_list_tools, mcp_call_tool
from .tools.browser_use_adapter import browser_task
from .tools.agent_reach_adapter import agent_reach_doctor
from .engines.deerflow import status as deerflow_status, run as deerflow_run
from .memory import get_engine_session, set_engine_session

app = FastAPI(title="NEXUS Agent", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
agent = SuperAgent()
ollama = OllamaClient()


@app.get("/")
async def root():
    return {
        "name": "NEXUS Agent",
        "version": "3.0.0",
        "status": "online",
        "default_model": CONFIG["ollama"]["default_model"],
        "engines": ["ollama", "nexus", "deerflow"],
        "agent_endpoint": "/agent/run",
        "engine_status": "/engines/status",
        "openai_endpoint": "/v1/chat/completions",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    try:
        models = await ollama.models()
        deer = await deerflow_status()
        return {
            "ok": True,
            "ollama": True,
            "models": [m.get("name") for m in models.get("models", [])],
            "deerflow": deer,
        }
    except Exception as e:
        return {"ok": False, "ollama": False, "error": str(e), "deerflow": await deerflow_status()}


@app.get("/engines/status")
async def engines_status():
    ollama_ok = False
    ollama_models = []
    try:
        data = await ollama.models()
        ollama_models = [m.get("name") for m in data.get("models", [])]
        ollama_ok = True
    except Exception:
        pass
    return {
        "ollama": {"available": ollama_ok, "models": ollama_models},
        "nexus": {"available": ollama_ok, "requires": "Ollama"},
        "deerflow": await deerflow_status(),
    }


@app.get("/v1/models")
async def models():
    try:
        data = await ollama.models()
        return {"object": "list", "data": [{"id": m.get("name"), "object": "model", "owned_by": "ollama"} for m in data.get("models", [])]}
    except Exception as e:
        raise HTTPException(503, str(e))


@app.post("/agent/run", response_model=AgentResponse)
async def run_agent(req: AgentRequest):
    try:
        return await agent.run(
            prompt=req.prompt,
            model=req.model,
            session_id=req.session_id,
            mode=req.mode,
            context=req.context,
            allow_tools=req.allow_tools,
            engine=req.engine,
            deerflow_mode=req.deerflow_mode,
        )
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.post("/v1/chat/completions")
async def openai_chat(req: OpenAIChatRequest):
    if req.stream:
        raise HTTPException(400, "Streaming is not enabled in NEXUS v3. Use stream=false.")
    user_text = "\n".join(m.content for m in req.messages if m.role == "user")
    context = "\n".join(f"{m.role}: {m.content}" for m in req.messages[:-1])
    try:
        result = await agent.run(
            prompt=user_text or req.messages[-1].content,
            model=req.model,
            session_id="openai-" + str(uuid.uuid4()),
            mode="auto",
            context=context,
            engine="auto",
        )
    except Exception as e:
        raise HTTPException(500, detail=str(e))

    return {
        "id": "chatcmpl-" + uuid.uuid4().hex,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": result["model"],
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": result["answer"]},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "agent_metadata": result["metadata"],
    }


@app.get("/tools/status")
async def tools_status_endpoint():
    return await tools_status()


@app.get("/tools/mcp/{server}/tools")
async def mcp_tools_endpoint(server: str):
    return await mcp_list_tools(server)


@app.post("/tools/mcp/{server}/call/{tool_name}")
async def mcp_call_endpoint(server: str, tool_name: str, arguments: dict):
    return await mcp_call_tool(server, tool_name, arguments)


@app.post("/tools/browser")
async def browser_endpoint(payload: dict):
    task = str(payload.get("task", ""))
    model = str(payload.get("model") or CONFIG["ollama"]["default_model"])
    return await browser_task(task, model)


@app.get("/tools/agent-reach/doctor")
async def reach_doctor_endpoint():
    return await agent_reach_doctor()


@app.get("/engines/deerflow/status")
async def deerflow_status_endpoint():
    return await deerflow_status()


@app.post("/engines/deerflow/run")
async def deerflow_run_endpoint(payload: dict):
    prompt = str(payload.get("prompt", "")).strip()
    if not prompt:
        raise HTTPException(400, "prompt is required")
    session_id = str(payload.get("session_id") or "default")
    mode = str(payload.get("mode") or CONFIG.get("deerflow", {}).get("default_mode", "ultra"))
    model = payload.get("model")
    thread_id = get_engine_session(session_id, "deerflow")
    result = await deerflow_run(prompt, session_id, thread_id=thread_id, model=model, mode=mode)
    if result.get("ok") and result.get("thread_id"):
        set_engine_session(session_id, "deerflow", str(result["thread_id"]))
    return result
