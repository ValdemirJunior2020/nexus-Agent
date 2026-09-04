import asyncio
import json
import shutil
from typing import Any

from .builtin import web_fetch, list_files, read_file, write_file
from .browser_use_adapter import browser_task, browser_status
from .mcp_adapter import mcp_status, mcp_list_tools, mcp_call_tool
from .agent_reach_adapter import agent_reach_status, agent_reach_doctor, reach_read_url, reach_github_repo, reach_youtube_info
from ..error_logging import record_issue

TOOL_SPECS = [
    {"name":"web_fetch","description":"Fetch a public HTTP/HTTPS page as text. Use for simple web reading when a full browser is unnecessary.","args":{"url":"string"}},
    {"name":"list_files","description":"List files inside the agent workspace only.","args":{"path":"string, optional"}},
    {"name":"read_file","description":"Read a UTF-8/text file inside the agent workspace only.","args":{"path":"string"}},
    {"name":"write_file","description":"Write a text file inside the agent workspace only.","args":{"path":"string","content":"string"}},
    {"name":"browser_task","description":"Run a real browser automation task with Browser Use and the selected Ollama model. Use for clicking, forms, multi-step websites, or visual browser workflows.","args":{"task":"string"}},
    {"name":"reach_read_url","description":"Read a public URL through the Agent Reach/Jina-style web reader capability.","args":{"url":"string"}},
    {"name":"reach_github_repo","description":"Inspect a public GitHub repository using the gh CLI when available.","args":{"repo":"owner/repo"}},
    {"name":"reach_youtube_info","description":"Read metadata/subtitles information for an authorized/public YouTube URL using yt-dlp when available.","args":{"url":"string"}},
    {"name":"mcp_list_tools","description":"List tools exposed by a configured MCP server.","args":{"server":"configured server name"}},
    {"name":"mcp_call_tool","description":"Call a tool on a configured MCP server.","args":{"server":"configured server name","tool":"tool name","arguments":"object"}},
]


def tool_catalog_text() -> str:
    return json.dumps(TOOL_SPECS, indent=2)


async def status() -> dict[str, Any]:
    return {
        "browser_use": await browser_status(),
        "mcp": await mcp_status(),
        "agent_reach": await agent_reach_status(),
        "commands": {
            "gh": bool(shutil.which("gh")),
            "yt-dlp": bool(shutil.which("yt-dlp")),
            "agent-reach": bool(shutil.which("agent-reach")),
        },
    }


async def execute(name: str, args: dict[str, Any], model: str) -> dict[str, Any]:
    try:
        if name == "web_fetch":
            result = await web_fetch(str(args.get("url", "")))
        elif name == "list_files":
            result = list_files(str(args.get("path", ".")))
        elif name == "read_file":
            result = read_file(str(args.get("path", "")))
        elif name == "write_file":
            result = write_file(str(args.get("path", "")), str(args.get("content", "")))
        elif name == "browser_task":
            result = await browser_task(str(args.get("task", "")), model=model)
        elif name == "reach_read_url":
            result = await reach_read_url(str(args.get("url", "")))
        elif name == "reach_github_repo":
            result = await reach_github_repo(str(args.get("repo", "")))
        elif name == "reach_youtube_info":
            result = await reach_youtube_info(str(args.get("url", "")))
        elif name == "mcp_list_tools":
            result = await mcp_list_tools(str(args.get("server", "")))
        elif name == "mcp_call_tool":
            arguments = args.get("arguments") or {}
            if not isinstance(arguments, dict):
                result = {"ok": False, "error": "arguments must be an object"}
            else:
                result = await mcp_call_tool(str(args.get("server", "")), str(args.get("tool", "")), arguments)
        else:
            result = {"ok": False, "error": f"Unknown tool: {name}"}

        if isinstance(result, dict) and result.get("ok") is False:
            incident_id = record_issue(
                f"tool.{name}",
                message=str(result.get("error") or "Tool returned ok=false"),
                context={"tool": name, "model": model},
            )
            result = dict(result)
            result.setdefault("incident_id", incident_id)
        return result
    except Exception as exc:
        incident_id = record_issue(
            f"tool.{name}",
            exc,
            context={"tool": name, "model": model},
        )
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "incident_id": incident_id}
