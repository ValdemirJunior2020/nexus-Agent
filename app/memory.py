import sqlite3
from pathlib import Path
from datetime import datetime
from .config import CONFIG, ROOT

DB = ROOT / "data" / "memory.db"

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
        cx.commit()

def add(session_id: str, role: str, content: str):
    if not CONFIG["agent"].get("memory_enabled", True):
        return
    init_db()
    with sqlite3.connect(DB) as cx:
        cx.execute("INSERT INTO memory(session_id, role, content, created_at) VALUES(?,?,?,?)",
                   (session_id, role, content, datetime.utcnow().isoformat()))
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
    return [{"role":r[0], "content":r[1]} for r in reversed(rows)]
