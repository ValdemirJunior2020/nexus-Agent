import asyncio
import json
import shutil
import urllib.parse
from typing import Any
import httpx
from ..config import CONFIG

async def _run(argv: list[str], timeout: int = 60) -> dict[str, Any]:
    proc = await asyncio.create_subprocess_exec(
        *argv,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return {"ok": False, "error": "command timed out"}
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": out.decode("utf-8", errors="replace")[:120000],
        "stderr": err.decode("utf-8", errors="replace")[:30000],
    }

async def agent_reach_status() -> dict[str, Any]:
    return {
        "enabled": CONFIG.get("tools", {}).get("agent_reach_enabled", True),
        "agent_reach": bool(shutil.which("agent-reach")),
        "gh": bool(shutil.which("gh")),
        "yt-dlp": bool(shutil.which("yt-dlp")),
    }

async def agent_reach_doctor() -> dict[str, Any]:
    exe = shutil.which("agent-reach")
    if not exe:
        return {"ok": False, "error": "agent-reach is not installed. Run INSTALL_POWER_TOOLS.bat"}
    return await _run([exe, "doctor"], timeout=120)

async def reach_read_url(url: str) -> dict[str, Any]:
    if not CONFIG.get("tools", {}).get("agent_reach_enabled", True):
        return {"ok": False, "error": "Agent Reach integration is disabled"}
    p = urllib.parse.urlparse(url)
    if p.scheme not in ("http", "https"):
        return {"ok": False, "error": "Only http/https URLs are allowed"}
    # Agent Reach documents the r.jina.ai reader as an upstream capability.
    reader = "https://r.jina.ai/" + url
    async with httpx.AsyncClient(timeout=45, follow_redirects=True, headers={"User-Agent":"Ollama-SuperAgent/2.0"}) as c:
        r = await c.get(reader)
        return {"ok": r.is_success, "status": r.status_code, "content": r.text[:160000]}

async def reach_github_repo(repo: str) -> dict[str, Any]:
    gh = shutil.which("gh")
    if not gh:
        return {"ok": False, "error": "gh CLI is not installed/configured. Agent Reach can help install/check it."}
    if repo.count("/") != 1 or any(ch.isspace() for ch in repo):
        return {"ok": False, "error": "repo must look like owner/repo"}
    return await _run([gh, "repo", "view", repo, "--json", "nameWithOwner,description,url,homepageUrl,licenseInfo,stargazerCount,updatedAt,defaultBranchRef"], timeout=45)

async def reach_youtube_info(url: str) -> dict[str, Any]:
    ytdlp = shutil.which("yt-dlp")
    if not ytdlp:
        return {"ok": False, "error": "yt-dlp is not installed. Agent Reach can help install/check it."}
    p = urllib.parse.urlparse(url)
    if p.scheme not in ("http", "https"):
        return {"ok": False, "error": "Only http/https URLs are allowed"}
    return await _run([ytdlp, "--skip-download", "--dump-single-json", "--no-warnings", url], timeout=120)
