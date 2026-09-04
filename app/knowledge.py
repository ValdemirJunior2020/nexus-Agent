import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import CONFIG, ROOT

KNOWLEDGE_DIR = ROOT / "knowledge"
TICKET_MATRIX_PATH = KNOWLEDGE_DIR / "ticket_matrix.json"


SUPPORT_HINTS = {
    "zendesk", "ticket", "guest", "customer", "reservation", "itinerary", "hotel",
    "refund", "voucher", "cancel", "cancellation", "rebook", "booking", "occupancy",
    "checkin", "checkout", "property", "room", "rate", "charge", "billing", "supervisor",
    "vipres", "refund queue", "matrix", "agent", "internal note", "macro", "escalation"
}

def should_use_ticket_matrix(query: str, force: bool = False) -> bool:
    if force:
        return True
    text = (query or "").lower()
    return any(hint in text for hint in SUPPORT_HINTS)


def _tokens(text: str) -> set[str]:
    raw = [t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) > 2]
    out: set[str] = set()
    for t in raw:
        out.add(t)
        # Lightweight normalization for common support-language variants.
        if len(t) > 4 and t.endswith("ies"):
            out.add(t[:-3] + "y")
        elif len(t) > 4 and t.endswith("es"):
            out.add(t[:-2])
        elif len(t) > 3 and t.endswith("s"):
            out.add(t[:-1])
        if len(t) > 6 and t.endswith("ing"):
            out.add(t[:-3])
        if len(t) > 5 and t.endswith("ed"):
            out.add(t[:-2])
    return out


@lru_cache(maxsize=1)
def load_ticket_matrix() -> dict[str, Any]:
    if not TICKET_MATRIX_PATH.exists():
        return {"source": None, "sheet": "Ticket Matrix", "sections": []}
    return json.loads(TICKET_MATRIX_PATH.read_text(encoding="utf-8"))


def all_ticket_rules() -> list[dict[str, Any]]:
    data = load_ticket_matrix()
    out: list[dict[str, Any]] = []
    for section in data.get("sections", []):
        section_name = str(section.get("name") or "")
        for row in section.get("rows", []):
            item = dict(row)
            item["section"] = section_name
            out.append(item)
    return out


def search_ticket_matrix(query: str, limit: int = 5) -> list[dict[str, Any]]:
    if not CONFIG.get("knowledge", {}).get("ticket_matrix_enabled", True):
        return []
    q = _tokens(query)
    if not q:
        return []
    ranked: list[tuple[float, dict[str, Any]]] = []
    for item in all_ticket_rules():
        issue_tokens = _tokens(str(item.get("issue") or ""))
        instruction_tokens = _tokens(str(item.get("instructions") or ""))
        section_tokens = _tokens(str(item.get("section") or ""))
        exact_bonus = 0.0
        issue_l = str(item.get("issue") or "").lower()
        query_l = (query or "").lower()
        if issue_l and issue_l in query_l:
            exact_bonus = 8.0
        score = (
            5.0 * len(q & issue_tokens)
            + 1.4 * len(q & instruction_tokens)
            + 1.0 * len(q & section_tokens)
            + exact_bonus
        )
        if score > 0:
            ranked.append((score, item))
    ranked.sort(key=lambda x: (-x[0], int(x[1].get("row") or 9999)))
    return [dict(item, match_score=round(score, 2)) for score, item in ranked[:max(1, limit)]]


def build_ticket_matrix_context(query: str, limit: int | None = None, force: bool = False) -> tuple[str, list[dict[str, Any]]]:
    cfg = CONFIG.get("knowledge", {})
    if not should_use_ticket_matrix(query, force=force):
        return "", []
    limit = int(limit or cfg.get("ticket_matrix_top_k", 4))
    matches = search_ticket_matrix(query, limit=limit)
    if not matches:
        return "", []
    data = load_ticket_matrix()
    lines = [
        "AUTHORITATIVE COMPANY KNOWLEDGE — TICKET MATRIX",
        f"Source: {data.get('source')} | Sheet: {data.get('sheet')}",
        "These rules are authoritative. Do not replace them with learned memory or historical examples.",
        "EVIDENCE RULE: state only what the matched fields explicitly support. Do not invent prohibitions, requirements, or approvals from blank/absent fields.",
        "If a field does not require an action, phrase it as 'the matched rule does not indicate that this action is required' rather than 'do not do it'.",
    ]
    note = str(data.get("note") or "").strip()
    if note:
        lines.append(f"Global note: {note}")
    for i, m in enumerate(matches, 1):
        lines.append(
            f"\n[MATRIX MATCH {i}]\n"
            f"Section: {m.get('section')}\n"
            f"Issue: {m.get('issue')}\n"
            f"Instructions: {m.get('instructions')}\n"
            f"Slack: {m.get('slack')}\n"
            f"Refund Queue: {m.get('refund_queue')}\n"
            f"Create a Ticket: {m.get('create_ticket')}\n"
            f"Supervisor: {m.get('supervisor')}\n"
            f"VIPRES: {m.get('vipres')}"
        )
    return "\n".join(lines), matches


def knowledge_status() -> dict[str, Any]:
    data = load_ticket_matrix()
    rules = all_ticket_rules()
    return {
        "ticket_matrix_enabled": CONFIG.get("knowledge", {}).get("ticket_matrix_enabled", True),
        "source": data.get("source"),
        "sheet": data.get("sheet"),
        "sections": len(data.get("sections", [])),
        "rules": len(rules),
    }
