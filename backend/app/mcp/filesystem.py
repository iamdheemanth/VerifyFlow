from __future__ import annotations

from typing import Any

from mcp import StdioServerParameters

from app.mcp import BaseMCPClient, extract_text, normalize_tool_result
from app.core.filesystem_sandbox import resolve_allowed_base_paths, resolve_allowed_path


class FilesystemMCP(BaseMCPClient):
    def __init__(self):
        allowed_paths = [str(path) for path in resolve_allowed_base_paths()]
        super().__init__(
            StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem", *allowed_paths],
            )
        )

    async def write_file(self, path: str, content: str) -> dict[str, Any]:
        safe_path = str(resolve_allowed_path(path))
        result = await self._call_tool("write_file", {"path": safe_path, "content": content})
        return normalize_tool_result(result)

    async def read_file(self, path: str) -> str | None:
        safe_path = str(resolve_allowed_path(path))
        result = await self._call_tool("read_text_file", {"path": safe_path})
        if result.isError:
            return None
        return extract_text(result)

    async def list_directory(self, path: str) -> list[str]:
        safe_path = str(resolve_allowed_path(path))
        result = await self._call_tool("list_directory", {"path": safe_path})
        if result.isError:
            return []

        if result.structuredContent and isinstance(result.structuredContent, dict):
            entries = result.structuredContent.get("entries")
            if isinstance(entries, list):
                names: list[str] = []
                for entry in entries:
                    if isinstance(entry, dict):
                        name = entry.get("name") or entry.get("path")
                        if isinstance(name, str):
                            names.append(name)
                return names

        text = extract_text(result)
        if not text:
            return []
        return [line.strip() for line in text.splitlines() if line.strip()]

    async def file_exists(self, path: str) -> bool:
        safe_path = resolve_allowed_path(path)
        parent = str(safe_path.parent)
        target = safe_path.name
        entries = await self.list_directory(parent)
        return target in entries or str(safe_path) in entries
