from typing import Any, Optional, Literal
from pydantic import BaseModel, Field

class ChatMessage(BaseModel):
    role: Literal["system","user","assistant","tool"] = "user"
    content: str

class AgentRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    session_id: str = "default"
    user_id: str = "default"
    ticket_id: Optional[str] = None
    mode: Literal["auto","fast","deep","research","code","qa","document"] = "auto"
    engine: Literal["auto","ollama","nexus","deerflow"] = "auto"
    deerflow_mode: Literal["flash","standard","pro","ultra"] = "ultra"
    context: Optional[str] = None
    allow_tools: bool = True
    allow_learning: bool = True

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

class LearningTeachRequest(BaseModel):
    user_id: str = "default"
    content: str
    kind: Literal["preference","correction","workflow","approved_example"] = "preference"
    scope: Literal["user","global"] = "user"
    source: str = "manual"
    confidence: float = 1.0

class LearningFeedbackRequest(BaseModel):
    user_id: str = "default"
    session_id: str = "default"
    ticket_id: Optional[str] = None
    rating: Optional[int] = None
    correction: Optional[str] = None
    teach_correction: bool = True

class ZendeskTicketRequest(BaseModel):
    ticket_id: str
    user_id: str = "default"
    subject: str = ""
    requester: str = ""
    status: str = ""
    priority: str = ""
    brand: str = ""
    group: str = ""
    assignee: str = ""
    tags: list[str] = Field(default_factory=list)
    public_comments: list[str] = Field(default_factory=list)
    internal_comments: list[str] = Field(default_factory=list)
    reservation_context: Optional[str] = None
    instruction: str = "Analyze this Zendesk ticket and recommend the next best action according to company policy."
    model: Optional[str] = None
    mode: Literal["auto","deep","qa","document"] = "auto"
    engine: Literal["auto","nexus","deerflow"] = "nexus"
    deerflow_mode: Literal["flash","standard","pro","ultra"] = "pro"
    allow_tools: bool = True
