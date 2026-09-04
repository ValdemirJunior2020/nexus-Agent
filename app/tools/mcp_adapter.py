import json
from pathlib import Path
from typing import Any
from ..config import ROOT, CONFIG

MCP_CONFIG = ROOT / "mcp_servers.json"


def _servers() -> dict[str, Any]:
    if not MCP_CONFIG.exists():
        return {}
    with MCP_CONFIG.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("servers", data)


async def mcp_status() -> dict[str, Any]:
    try:
        import mcp  # noqa
        installed = True
    except Exception as exc:
        return {"installed": False, "enabled": CONFIG.get("tools", {}).get("mcp_enabled", True), "servers": list(_servers()), "error": str(exc)}
    return {"installed": installed, "enabled": CONFIG.get("tools", {}).get("mcp_enabled", True), "servers": list(_servers())}


def _normalize_content(result) -> Any:
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    if isinstance(result, (dict, list, str, int, float, bool)) or result is None:
        return result
    return str(result)


async def _client(server_name: str):
    if not CONFIG.get("tools", {}).get("mcp_enabled", True):
        raise RuntimeError("MCP is disabled in config.json")
    servers = _servers()
    cfg = servers.get(server_name)
    if not cfg:
        raise KeyError(f"MCP server '{server_name}' is not configured")
    if cfg.get("enabled", True) is False:
        raise RuntimeError(f"MCP server '{server_name}' is disabled")

    try:
        from mcp import Client, StdioServerParameters
    except Exception as exc:
        raise RuntimeError("MCP extra is not installed. Run INSTALL_POWER_TOOLS.bat") from exc

    transport = cfg.get("transport", "stdio")
    if transport in ("http", "streamable-http", "streamable_http"):
        url = cfg.get("url")
        if not url:
            raise ValueError("HTTP MCP server is missing url")
        return Client(url)
    if transport == "stdio":
        command = cfg.get("command")
        if not command:
            raise ValueError("stdio MCP server is missing command")
        params = StdioServerParameters(
            command=command,
            args=cfg.get("args", []),
            env=cfg.get("env") or None,
        )
        return Client(params)
    raise ValueError(f"Unsupported MCP transport: {transport}")


async def mcp_list_tools(server_name: str) -> dict[str, Any]:
    client = await _client(server_name)
    async with client:
        tools = await client.list_tools()
        return {"ok": True, "server": server_name, "tools": _normalize_content(tools)}


async def mcp_call_tool(server_name: str, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    client = await _client(server_name)
    async with client:
        result = await client.call_tool(tool_name, arguments)
        return {"ok": True, "server": server_name, "tool": tool_name, "result": _normalize_content(result)}
