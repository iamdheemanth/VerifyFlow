from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Sequence
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.telemetry import record_llm_call


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
                started_at = time.perf_counter()
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                )
                latency_ms = (time.perf_counter() - started_at) * 1000
                usage = getattr(response, "usage", None)
                prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
                completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
                total_tokens = int(getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or 0)
                record_llm_call(
                    role="executor" if self is executor_llm else "judge",
                    provider=self.base_url,
                    model_name=self.model,
                    latency_ms=latency_ms,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
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
        json_candidate = self._extract_json_candidate(cleaned_response)

        try:
            parsed = json.loads(json_candidate)
        except json.JSONDecodeError as exc:
            snippet = json_candidate[:200] if json_candidate else "<empty response>"
            raise ValueError(f"LLM response was not valid JSON: {snippet}") from exc

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

    @staticmethod
    def _extract_json_candidate(content: str) -> str:
        cleaned = content.strip()
        if not cleaned:
            return cleaned

        if cleaned.startswith("{") and cleaned.endswith("}"):
            return cleaned

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return cleaned[start : end + 1].strip()

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
