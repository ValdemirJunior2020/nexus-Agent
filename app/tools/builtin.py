from pathlib import Path
import urllib.parse
import httpx
from ..config import CONFIG, ROOT

def _workspace():
    p = Path(CONFIG["tools"].get("workspace_root","./workspace"))
    if not p.is_absolute():
        p = ROOT / p
    p.mkdir(parents=True, exist_ok=True)
    return p.resolve()

def _safe_path(path: str):
    base = _workspace()
    target = (base / path).resolve()
    if base not in target.parents and target != base:
        raise ValueError("Path escapes workspace.")
    return target

async def web_fetch(url: str):
    if not CONFIG["tools"].get("web_fetch_enabled", True):
        return {"error":"web_fetch disabled"}
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http","https"):
        return {"error":"Only http/https URLs are allowed"}
    async with httpx.AsyncClient(timeout=30, follow_redirects=True,
                                 headers={"User-Agent":"Ollama-SuperAgent/1.0"}) as c:
        r = await c.get(url)
        text = r.text[:120000]
        return {"status":r.status_code,"url":str(r.url),"content":text}

def list_files(path: str = "."):
    if not CONFIG["tools"].get("filesystem_enabled", True):
        return {"error":"filesystem disabled"}
    p = _safe_path(path)
    if not p.exists():
        return {"error":"not found"}
    if p.is_file():
        return {"files":[p.name]}
    return {"files":[x.name for x in sorted(p.iterdir())][:500]}

def read_file(path: str):
    if not CONFIG["tools"].get("filesystem_enabled", True):
        return {"error":"filesystem disabled"}
    p = _safe_path(path)
    if not p.is_file():
        return {"error":"not a file"}
    return {"path":str(p.relative_to(_workspace())), "content":p.read_text(encoding="utf-8", errors="replace")[:200000]}

def write_file(path: str, content: str):
    if not CONFIG["tools"].get("filesystem_enabled", True):
        return {"error":"filesystem disabled"}
    p = _safe_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"ok":True,"path":str(p.relative_to(_workspace()))}
