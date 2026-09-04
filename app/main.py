import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models import AgentRequest, AgentResponse, OpenAIChatRequest, LearningTeachRequest, LearningFeedbackRequest, ZendeskTicketRequest
from .orchestrator import SuperAgent
from .local_llm import LocalLLMClient
from .config import CONFIG
from .tools.registry import status as tools_status
from .tools.mcp_adapter import mcp_list_tools, mcp_call_tool
from .tools.browser_use_adapter import browser_task
from .tools.agent_reach_adapter import agent_reach_doctor
from .engines.deerflow import status as deerflow_status, run as deerflow_run
from .memory import get_engine_session, set_engine_session, teach_memory, list_learned, deactivate_memory, add_feedback
from .knowledge import knowledge_status, search_ticket_matrix, load_ticket_matrix
from .error_logging import setup_logging, record_issue, friendly_issue_text, issue_count

setup_logging()

app = FastAPI(title="NEXUS Agent", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
agent = SuperAgent()
local_llm = LocalLLMClient()


@app.exception_handler(Exception)
async def nexus_unhandled_exception_handler(request: Request, exc: Exception):
    incident_id = record_issue(
        "api.unhandled",
        exc,
        context={"method": request.method, "path": request.url.path},
    )
    return JSONResponse(
        status_code=500,
        content={"detail": friendly_issue_text(incident_id), "incident_id": incident_id},
    )


@app.get("/")
async def root():
    return {
        "name": "NEXUS Agent",
        "version": "3.0.0",
        "status": "online",
        "default_model": local_llm.default_model(),
        "engines": ["local_llm", "nexus", "deerflow"],
        "agent_endpoint": "/agent/run",
        "engine_status": "/engines/status",
        "openai_endpoint": "/v1/chat/completions",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    llm = await local_llm.status()
    deer = await deerflow_status()
    active = llm.get("active")
    return {
        "ok": bool(active),
        "local_llm": llm,
        "llama_cpp": llm.get("providers", {}).get("llama_cpp", {}).get("available", False),
        "ollama": llm.get("providers", {}).get("ollama", {}).get("available", False),
        "models": llm.get("providers", {}).get(active or "", {}).get("models", []),
        "deerflow": deer,
    }


@app.get("/engines/status")
async def engines_status():
    llm = await local_llm.status()
    return {
        "local_llm": llm,
        "nexus": {"available": bool(llm.get("active")), "requires": "llama.cpp or Ollama"},
        "deerflow": await deerflow_status(),
    }


@app.get("/v1/models")
async def models():
    try:
        data = await local_llm.models()
        provider = local_llm.last_provider
        return {"object": "list", "data": [{"id": m.get("name"), "object": "model", "owned_by": provider} for m in data.get("models", [])]}
    except Exception as e:
        incident_id = record_issue("api.models", e)
        raise HTTPException(503, friendly_issue_text(incident_id))


@app.get("/llm/status")
async def local_llm_status_endpoint():
    return await local_llm.status()


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
            user_id=req.user_id,
            ticket_id=req.ticket_id,
            allow_learning=req.allow_learning,
        )
    except Exception as e:
        incident_id = record_issue(
            "agent.run",
            e,
            context={
                "session_id": req.session_id,
                "user_id": req.user_id,
                "ticket_id": req.ticket_id,
                "engine": req.engine,
                "mode": req.mode,
                "model": req.model,
            },
        )
        raise HTTPException(500, detail=friendly_issue_text(incident_id))


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
        incident_id = record_issue("openai.chat", e, context={"model": req.model})
        raise HTTPException(500, detail=friendly_issue_text(incident_id))

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
    model = str(payload.get("model") or local_llm.default_model())
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


@app.get("/knowledge/status")
async def knowledge_status_endpoint():
    return knowledge_status()


@app.get("/knowledge/ticket-matrix")
async def ticket_matrix_endpoint(q: str = "", limit: int = 5):
    if q.strip():
        return {"query": q, "matches": search_ticket_matrix(q, limit=max(1, min(limit, 20)))}
    return load_ticket_matrix()


@app.post("/learning/teach")
async def learning_teach_endpoint(req: LearningTeachRequest):
    memory_id = teach_memory(
        user_id=req.user_id,
        content=req.content,
        kind=req.kind,
        scope=req.scope,
        source=req.source,
        confidence=req.confidence,
    )
    return {"ok": True, "memory_id": memory_id}


@app.get("/learning/memories/{user_id}")
async def learning_memories_endpoint(user_id: str, limit: int = 100):
    return {"user_id": user_id, "memories": list_learned(user_id, limit=max(1, min(limit, 500)))}


@app.delete("/learning/memories/{memory_id}")
async def learning_forget_endpoint(memory_id: int):
    return {"ok": deactivate_memory(memory_id), "memory_id": memory_id}


@app.post("/learning/feedback")
async def learning_feedback_endpoint(req: LearningFeedbackRequest):
    feedback_id = add_feedback(req.user_id, req.session_id, req.ticket_id, req.rating, req.correction)
    memory_id = None
    if req.teach_correction and req.correction and req.correction.strip():
        memory_id = teach_memory(
            user_id=req.user_id,
            content=req.correction.strip(),
            kind="correction",
            scope="user",
            source=f"feedback:{feedback_id}",
            confidence=1.0,
        )
    return {"ok": True, "feedback_id": feedback_id, "memory_id": memory_id}


@app.post("/logs/client")
async def client_issue_endpoint(payload: dict):
    incident_id = record_issue(
        str(payload.get("component") or "client"),
        message=str(payload.get("error") or "Client-reported issue"),
        context={
            "ticket_id": payload.get("ticket_id"),
            "session_id": payload.get("session_id"),
            "source": payload.get("source"),
        },
    )
    return {"ok": True, "incident_id": incident_id, "message": friendly_issue_text(incident_id)}


@app.get("/logs/status")
async def logs_status_endpoint():
    return {
        "enabled": True,
        "issue_count": issue_count(),
        "message": friendly_issue_text(),
        "export": "Run EXPORT_NEXUS_LOGS.bat on the NEXUS server to create a ZIP report.",
    }



def _zendesk_context(req: ZendeskTicketRequest) -> str:
    parts = [
        "ZENDESK TICKET CONTEXT",
        f"Ticket ID: {req.ticket_id}",
        f"Subject: {req.subject}",
        f"Requester: {req.requester}",
        f"Status: {req.status}",
        f"Priority: {req.priority}",
        f"Brand: {req.brand}",
        f"Group: {req.group}",
        f"Assignee: {req.assignee}",
        f"Tags: {', '.join(req.tags)}",
    ]
    if req.reservation_context:
        parts.append("RESERVATION / PLATFORM CONTEXT:\n" + req.reservation_context)
    if req.public_comments:
        parts.append("PUBLIC COMMENTS:\n" + "\n---\n".join(req.public_comments[-20:]))
    if req.internal_comments:
        parts.append("INTERNAL COMMENTS:\n" + "\n---\n".join(req.internal_comments[-20:]))
    parts.append(
        "IMPORTANT: historical ticket comments describe what people did; they are not automatically policy. "
        "The authoritative Ticket Matrix supplied by NEXUS has higher precedence."
    )
    return "\n\n".join(parts)


@app.post("/zendesk/analyze", response_model=AgentResponse)
async def zendesk_analyze_endpoint(req: ZendeskTicketRequest):
    try:
        context = _zendesk_context(req)
        prompt = (
            req.instruction
            + "\n\nReturn a practical agent-facing answer with: concern, matched Ticket Matrix rule, required next actions, "
              "what not to do, escalation/ticket/refund/VIPRES requirements when applicable, and a concise suggested internal note."
        )
        return await agent.run(
            prompt=prompt,
            model=req.model,
            session_id=f"zendesk-{req.ticket_id}",
            user_id=req.user_id,
            ticket_id=req.ticket_id,
            mode=req.mode,
            context=context,
            allow_tools=req.allow_tools,
            allow_learning=False,
            engine=req.engine,
            deerflow_mode=req.deerflow_mode,
        )
    except Exception as e:
        incident_id = record_issue(
            "zendesk.analyze",
            e,
            context={
                "ticket_id": req.ticket_id,
                "user_id": req.user_id,
                "engine": req.engine,
                "mode": req.mode,
                "model": req.model,
            },
        )
        raise HTTPException(500, detail=friendly_issue_text(incident_id))
