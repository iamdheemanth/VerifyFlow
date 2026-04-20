from __future__ import annotations

import asyncio
import base64
import json
from collections.abc import Mapping
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult


class MCPToolError(RuntimeError):
    def __init__(self, message: str, *, tool_name: str, category: str, retryable: bool) -> None:
        super().__init__(message)
        self.tool_name = tool_name
        self.category = category
        self.retryable = retryable

    def to_error_details(self, *, source: str) -> dict[str, Any]:
        return {
            "message": str(self),
            "category": self.category,
            "retryable": self.retryable,
            "tool_name": self.tool_name,
            "source": source,
        }


def _classify_mcp_exception(tool_name: str, exc: Exception) -> MCPToolError:
    message = str(exc)
    lowered = message.lower()
    if any(marker in lowered for marker in ("timeout", "timed out", "deadline exceeded")):
        return MCPToolError(message, tool_name=tool_name, category="timeout", retryable=True)
    if any(marker in lowered for marker in ("connection reset", "connection refused", "broken pipe", "generatorexit", "cancel scope", "session is not initialized", "stdio")):
        return MCPToolError(message, tool_name=tool_name, category="mcp_session_failure", retryable=True)
    return MCPToolError(message, tool_name=tool_name, category="tool_error", retryable=False)


class BaseMCPClient:
    def __init__(self, server_params: StdioServerParameters):
        self.server_params = server_params
        self._exit_stack = AsyncExitStack()
        self._session: ClientSession | None = None

    async def __aenter__(self):
        read_stream, write_stream = await self._exit_stack.enter_async_context(
            stdio_client(self.server_params)
        )
        session = ClientSession(read_stream, write_stream)
        self._session = await self._exit_stack.enter_async_context(session)
        await self._session.initialize()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._session = None
        await self._exit_stack.aclose()

    @property
    def session(self) -> ClientSession:
        if self._session is None:
            raise MCPToolError(
                "MCP session is not initialized. Use the client in an async with block.",
                tool_name="session",
                category="mcp_session_failure",
                retryable=True,
            )
        return self._session

    async def _call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> CallToolResult:
        try:
            return await asyncio.wait_for(self.session.call_tool(tool_name, arguments or {}), timeout=30)
        except Exception as exc:
            if isinstance(exc, MCPToolError):
                raise
            raise _classify_mcp_exception(tool_name, exc) from exc


def normalize_tool_result(result: CallToolResult) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "is_error": result.isError,
        "structured_content": result.structuredContent,
        "content": [],
    }

    for item in result.content:
        if hasattr(item, "model_dump"):
            payload["content"].append(item.model_dump())
        elif isinstance(item, Mapping):
            payload["content"].append(dict(item))
        else:
            payload["content"].append({"value": str(item)})

    if result.isError:
        error_message = extract_text(result)
        payload["error"] = error_message or "MCP tool call failed."
        payload["error_details"] = {
            "message": payload["error"],
            "category": "tool_error",
            "retryable": False,
            "source": "mcp",
        }

    return payload


def extract_text(result: CallToolResult) -> str | None:
    if result.structuredContent:
        try:
            return json.dumps(result.structuredContent)
        except TypeError:
            return str(result.structuredContent)

    text_parts: list[str] = []
    for item in result.content:
        text_value = getattr(item, "text", None)
        if isinstance(text_value, str):
            text_parts.append(text_value)

    if not text_parts:
        return None

    return "\n".join(text_parts)


def extract_image_bytes(result: CallToolResult) -> bytes | None:
    for item in result.content:
        if getattr(item, "type", None) == "image":
            data = getattr(item, "data", None)
            if isinstance(data, str):
                return base64.b64decode(data)
    return None
