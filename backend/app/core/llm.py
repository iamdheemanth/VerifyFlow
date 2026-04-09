from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings


class LLMClient:
    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.2,
        max_tokens: int = 4096,
        response_format: dict | None = None,
    ) -> str:
        last_error: Exception | None = None

        for attempt in range(3):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                )
                content = response.choices[0].message.content
                if isinstance(content, str):
                    return content
                if isinstance(content, Sequence):
                    return "".join(
                        part.get("text", "") if isinstance(part, dict) else str(part)
                        for part in content
                    )
                return str(content)
            except Exception as exc:
                last_error = exc
                if attempt == 2:
                    break
                await asyncio.sleep(2**attempt)

        raise RuntimeError(
            f"LLM request failed for provider {self.base_url} using model {self.model}: {last_error}"
        ) from last_error

    async def chat_json(
        self,
        messages: list[dict],
        schema_hint: str,
        temperature: float = 0.1,
    ) -> dict:
        system_message = {
            "role": "system",
            "content": f"Return valid JSON only. No markdown fences. Shape: {schema_hint}",
        }
        raw_response = await self.chat(
            messages=[system_message, *messages],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        cleaned_response = self._strip_markdown_fences(raw_response)

        try:
            parsed = json.loads(cleaned_response)
        except json.JSONDecodeError as exc:
            raise ValueError("LLM response was not valid JSON") from exc

        if not isinstance(parsed, dict):
            raise ValueError("LLM response JSON must decode to an object")

        return parsed

    @staticmethod
    def _strip_markdown_fences(content: str) -> str:
        cleaned = content.strip()

        if cleaned.startswith("```") and cleaned.endswith("```"):
            lines = cleaned.splitlines()
            if lines:
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        return cleaned


executor_llm = LLMClient(
    base_url=settings.llm_base_url,
    api_key=settings.llm_api_key,
    model=settings.llm_model,
)
judge_llm = LLMClient(
    base_url=settings.llm_base_url,
    api_key=settings.llm_api_key,
    model=settings.llm_judge_model,
)
