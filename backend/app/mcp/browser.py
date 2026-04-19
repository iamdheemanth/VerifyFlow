from __future__ import annotations

import json
from typing import Any

from mcp import StdioServerParameters

from app.core.config import settings
from app.mcp import BaseMCPClient, extract_image_bytes, extract_text, normalize_tool_result


class BrowserMCP(BaseMCPClient):
    def __init__(self, channel: str | None = None):
        browser_channel = channel or settings.browser_channels[0]
        super().__init__(
            StdioServerParameters(
                command="npx",
                args=["-y", "@playwright/mcp", "--browser", browser_channel, "--isolated"],
            )
        )

    async def navigate(self, url: str) -> dict[str, Any]:
        result = await self._call_tool("browser_navigate", {"url": url})
        return normalize_tool_result(result)

    async def click(self, selector: str) -> dict[str, Any]:
        encoded_selector = json.dumps(selector)
        js = (
            "() => { "
            "const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim().toLowerCase(); "
            "const pressEnter = () => { "
            "const active = document.activeElement; "
            "if (!active) return { clicked: false, error: 'No active element' }; "
            "const form = active.form || active.closest?.('form'); "
            "if (form && typeof form.requestSubmit === 'function') { form.requestSubmit(); return { clicked: true, submitted: true }; } "
            "for (const type of ['keydown','keypress','keyup']) { "
            "active.dispatchEvent(new KeyboardEvent(type, { key: 'Enter', code: 'Enter', bubbles: true })); "
            "} "
            "return { clicked: true, submitted: true }; "
            "}; "
            "const resolve = (candidate) => { "
            "if (!candidate) return null; "
            "if (candidate === 'special=enter') return { __special: 'enter' }; "
            "if (candidate.startsWith('css=')) return document.querySelector(candidate.slice(4)); "
            "if (candidate.startsWith('link=')) { "
            "const needle = normalize(candidate.slice(5)); "
            "return Array.from(document.querySelectorAll('a')).find((element) => normalize(element.innerText || element.textContent) === needle) || null; "
            "} "
            "if (candidate.startsWith('button=')) { "
            "const needle = normalize(candidate.slice(7)); "
            "return Array.from(document.querySelectorAll('button,input[type=\"submit\"],input[type=\"button\"],[role=\"button\"]')).find((element) => normalize(element.innerText || element.value || element.getAttribute('aria-label') || element.textContent) === needle) || null; "
            "} "
            "if (candidate.startsWith('text=')) { "
            "const needle = normalize(candidate.slice(5)); "
            "return Array.from(document.querySelectorAll('a,button,input[type=\"submit\"],input[type=\"button\"],[role=\"button\"],summary')).find((element) => normalize(element.innerText || element.value || element.getAttribute('aria-label') || element.textContent) === needle) || null; "
            "} "
            "if (candidate.startsWith('aria=')) { "
            "const needle = normalize(candidate.slice(5)); "
            "return Array.from(document.querySelectorAll('[aria-label],[title]')).find((element) => normalize(element.getAttribute('aria-label') || element.getAttribute('title')) === needle) || null; "
            "} "
            "return document.querySelector(candidate); "
            "}; "
            f"const element = resolve({encoded_selector}); "
            "if (!element) return { clicked: false, error: 'Element not found' }; "
            "if (element.__special === 'enter') return pressEnter(); "
            "if (element.tagName === 'A' && element.href) { window.location.assign(element.href); return { clicked: true, navigated_to: element.href }; } "
            "if ((element.tagName === 'BUTTON' || (element.tagName === 'INPUT' && ['submit', 'button'].includes((element.type || '').toLowerCase()))) && element.form && typeof element.form.requestSubmit === 'function') { element.form.requestSubmit(); return { clicked: true, submitted: true }; } "
            "element.click(); "
            "return { clicked: true }; "
            "}"
        )
        result = await self._call_tool("browser_evaluate", {"function": js})
        return normalize_tool_result(result)

    async def fill(self, selector: str, value: str) -> dict[str, Any]:
        encoded_selector = json.dumps(selector)
        encoded_value = json.dumps(value)
        js = (
            "() => { "
            "const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim().toLowerCase(); "
            "const findByLabel = (labelText) => { "
            "const needle = normalize(labelText); "
            "const label = Array.from(document.querySelectorAll('label')).find((element) => normalize(element.innerText || element.textContent) === needle); "
            "if (!label) return null; "
            "if (label.control) return label.control; "
            "const forId = label.getAttribute('for'); "
            "return forId ? document.getElementById(forId) : label.querySelector('input,textarea'); "
            "}; "
            "const resolve = (candidate) => { "
            "if (!candidate) return null; "
            "if (candidate.startsWith('css=')) return document.querySelector(candidate.slice(4)); "
            "if (candidate.startsWith('label=')) return findByLabel(candidate.slice(6)); "
            "if (candidate.startsWith('placeholder=')) { "
            "const needle = normalize(candidate.slice(12)); "
            "return Array.from(document.querySelectorAll('input,textarea')).find((element) => normalize(element.getAttribute('placeholder')) === needle) || null; "
            "} "
            "if (candidate.startsWith('aria=')) { "
            "const needle = normalize(candidate.slice(5)); "
            "return Array.from(document.querySelectorAll('input,textarea')).find((element) => normalize(element.getAttribute('aria-label')) === needle) || null; "
            "} "
            "if (candidate.startsWith('name=')) return document.querySelector(`[name=\"${candidate.slice(5)}\"]`); "
            "return document.querySelector(candidate); "
            "}; "
            f"const element = resolve({encoded_selector}); "
            "if (!element) return { filled: false, error: 'Element not found' }; "
            "element.focus(); "
            f"element.value = {encoded_value}; "
            "element.dispatchEvent(new Event('input', { bubbles: true })); "
            "element.dispatchEvent(new Event('change', { bubbles: true })); "
            "return { filled: true }; "
            "}"
        )
        result = await self._call_tool("browser_evaluate", {"function": js})
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
