from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult


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
            raise RuntimeError("MCP session is not initialized. Use the client in an async with block.")
        return self._session

    async def _call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> CallToolResult:
        return await self.session.call_tool(tool_name, arguments or {})


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
