import re
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Any

from .config import CONFIG, ROOT

DB = ROOT / "data" / "memory.db"


def _now() -> str:
    return datetime.utcnow().isoformat()


def init_db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB) as cx:
        cx.execute("""CREATE TABLE IF NOT EXISTS memory(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")
        cx.execute("""CREATE TABLE IF NOT EXISTS engine_sessions(
            session_id TEXT NOT NULL,
            engine TEXT NOT NULL,
            engine_session_id TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(session_id, engine)
        )""")
        cx.execute("""CREATE TABLE IF NOT EXISTS learned_memory(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope TEXT NOT NULL DEFAULT 'user',
            user_id TEXT NOT NULL DEFAULT 'default',
            kind TEXT NOT NULL DEFAULT 'preference',
            content TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'manual',
            confidence REAL NOT NULL DEFAULT 1.0,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")
        cx.execute("CREATE INDEX IF NOT EXISTS idx_learned_memory_user ON learned_memory(user_id, active)")
        cx.execute("""CREATE TABLE IF NOT EXISTS learning_feedback(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            ticket_id TEXT,
            rating INTEGER,
            correction TEXT,
            created_at TEXT NOT NULL
        )""")
        cx.commit()


def add(session_id: str, role: str, content: str):
    if not CONFIG["agent"].get("memory_enabled", True):
        return
    init_db()
    with sqlite3.connect(DB) as cx:
        cx.execute("INSERT INTO memory(session_id, role, content, created_at) VALUES(?,?,?,?)",
                   (session_id, role, content, _now()))
        cx.commit()


def recent(session_id: str, limit: int = 12):
    if not CONFIG["agent"].get("memory_enabled", True):
        return []
    init_db()
    with sqlite3.connect(DB) as cx:
        rows = cx.execute(
            "SELECT role, content FROM memory WHERE session_id=? ORDER BY id DESC LIMIT ?",
            (session_id, limit)
        ).fetchall()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) > 2}


def teach_memory(user_id: str, content: str, kind: str = "preference", scope: str = "user", source: str = "manual", confidence: float = 1.0) -> int:
    init_db()
    content = (content or "").strip()
    if not content:
        raise ValueError("content is required")
    if scope not in {"user", "global"}:
        raise ValueError("scope must be user or global")
    if kind not in {"preference", "correction", "workflow", "approved_example"}:
        kind = "preference"
    now = _now()
    with sqlite3.connect(DB) as cx:
        cur = cx.execute(
            "INSERT INTO learned_memory(scope,user_id,kind,content,source,confidence,active,created_at,updated_at) VALUES(?,?,?,?,?,?,1,?,?)",
            (scope, user_id or "default", kind, content, source, float(confidence), now, now),
        )
        cx.commit()
        return int(cur.lastrowid)


def deactivate_memory(memory_id: int) -> bool:
    init_db()
    with sqlite3.connect(DB) as cx:
        cur = cx.execute("UPDATE learned_memory SET active=0, updated_at=? WHERE id=?", (_now(), int(memory_id)))
        cx.commit()
        return cur.rowcount > 0


def list_learned(user_id: str, limit: int = 100) -> list[dict[str, Any]]:
    init_db()
    with sqlite3.connect(DB) as cx:
        rows = cx.execute(
            """SELECT id,scope,user_id,kind,content,source,confidence,created_at,updated_at
               FROM learned_memory
               WHERE active=1 AND (scope='global' OR user_id=?)
               ORDER BY id DESC LIMIT ?""",
            (user_id or "default", int(limit)),
        ).fetchall()
    keys = ["id","scope","user_id","kind","content","source","confidence","created_at","updated_at"]
    return [dict(zip(keys, row)) for row in rows]


def relevant_learned(user_id: str, query: str, limit: int = 6) -> list[dict[str, Any]]:
    memories = list_learned(user_id, limit=300)
    q = _tokens(query)
    ranked = []
    for m in memories:
        mt = _tokens(m["content"])
        overlap = len(q & mt)
        # Global approved workflows stay discoverable; direct overlap gets priority.
        bonus = 0.3 if m["scope"] == "global" else 0.0
        score = overlap + bonus + float(m.get("confidence") or 0) * 0.05
        if overlap > 0 or len(memories) <= limit:
            ranked.append((score, m))
    ranked.sort(key=lambda x: (-x[0], -int(x[1]["id"])))
    return [m for _, m in ranked[:limit]]


def build_learning_context(user_id: str, query: str, limit: int = 6) -> tuple[str, list[dict[str, Any]]]:
    items = relevant_learned(user_id, query, limit=limit)
    if not items:
        return "", []
    lines = [
        "LEARNED MEMORY — LOWER AUTHORITY THAN OFFICIAL POLICY",
        "Use these only when they do not conflict with the Ticket Matrix or verified company knowledge.",
    ]
    for m in items:
        lines.append(f"- [{m['kind']}] {m['content']} (scope={m['scope']}, source={m['source']})")
    return "\n".join(lines), items


def add_feedback(user_id: str, session_id: str, ticket_id: str | None = None, rating: int | None = None, correction: str | None = None) -> int:
    init_db()
    with sqlite3.connect(DB) as cx:
        cur = cx.execute(
            "INSERT INTO learning_feedback(user_id,session_id,ticket_id,rating,correction,created_at) VALUES(?,?,?,?,?,?)",
            (user_id or "default", session_id or "default", ticket_id, rating, correction, _now()),
        )
        cx.commit()
        return int(cur.lastrowid)


def get_engine_session(session_id: str, engine: str):
    init_db()
    with sqlite3.connect(DB) as cx:
        row = cx.execute(
            "SELECT engine_session_id FROM engine_sessions WHERE session_id=? AND engine=?",
            (session_id, engine),
        ).fetchone()
    return row[0] if row else None


def set_engine_session(session_id: str, engine: str, engine_session_id: str):
    init_db()
    with sqlite3.connect(DB) as cx:
        cx.execute("""INSERT INTO engine_sessions(session_id, engine, engine_session_id, updated_at)
               VALUES(?,?,?,?)
               ON CONFLICT(session_id, engine) DO UPDATE SET
                 engine_session_id=excluded.engine_session_id,
                 updated_at=excluded.updated_at""",
            (session_id, engine, engine_session_id, _now()),
        )
        cx.commit()
