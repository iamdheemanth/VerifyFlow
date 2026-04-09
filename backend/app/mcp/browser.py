from __future__ import annotations

from typing import Any

from mcp import StdioServerParameters

from app.mcp import BaseMCPClient, extract_image_bytes, extract_text, normalize_tool_result


class BrowserMCP(BaseMCPClient):
    def __init__(self):
        super().__init__(
            StdioServerParameters(
                command="npx",
                args=["-y", "@playwright/mcp"],
            )
        )

    async def navigate(self, url: str) -> dict[str, Any]:
        result = await self._call_tool("browser_navigate", {"url": url})
        return normalize_tool_result(result)

    async def click(self, selector: str) -> dict[str, Any]:
        js = (
            "(selector) => { "
            "const element = document.querySelector(selector); "
            "if (!element) return { clicked: false, error: 'Element not found' }; "
            "element.click(); "
            "return { clicked: true }; "
            "}"
        )
        result = await self._call_tool("browser_evaluate", {"function": js, "selector": selector})
        return normalize_tool_result(result)

    async def fill(self, selector: str, value: str) -> dict[str, Any]:
        js = (
            "([selector, value]) => { "
            "const element = document.querySelector(selector); "
            "if (!element) return { filled: false, error: 'Element not found' }; "
            "element.value = value; "
            "element.dispatchEvent(new Event('input', { bubbles: true })); "
            "element.dispatchEvent(new Event('change', { bubbles: true })); "
            "return { filled: true }; "
            "}"
        )
        result = await self._call_tool(
            "browser_evaluate",
            {"function": js, "args": [selector, value]},
        )
        return normalize_tool_result(result)

    async def screenshot(self) -> bytes:
        result = await self._call_tool("browser_screenshot")
        image_bytes = extract_image_bytes(result)
        return image_bytes or b""

    async def get_text(self, selector: str) -> str | None:
        js = (
            "(selector) => { "
            "const element = document.querySelector(selector); "
            "return element ? element.textContent : null; "
            "}"
        )
        result = await self._call_tool("browser_evaluate", {"function": js, "selector": selector})
        if result.isError:
            return None
        return extract_text(result)

    async def evaluate(self, js_expression: str) -> dict[str, Any]:
        result = await self._call_tool("browser_evaluate", {"function": js_expression})
        return normalize_tool_result(result)
