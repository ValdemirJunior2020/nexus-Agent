from typing import Any, Optional, Literal
from pydantic import BaseModel, Field

class ChatMessage(BaseModel):
    role: Literal["system","user","assistant","tool"] = "user"
    content: str

class AgentRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    session_id: str = "default"
    mode: Literal["auto","fast","deep","research","code","qa","document"] = "auto"
    context: Optional[str] = None
    allow_tools: bool = True

class AgentStep(BaseModel):
    agent: str
    task: str
    result: str = ""
    score: float = 0.0

class AgentResponse(BaseModel):
    answer: str
    model: str
    session_id: str
    agents_used: list[str] = Field(default_factory=list)
    rounds: int = 1
    verified: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

class OpenAIChatRequest(BaseModel):
    model: Optional[str] = None
    messages: list[ChatMessage]
    temperature: Optional[float] = None
    stream: bool = False
