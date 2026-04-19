from __future__ import annotations

import time
from contextvars import ContextVar, Token
from typing import Any


_telemetry_events: ContextVar[list[dict[str, Any]] | None] = ContextVar("verifyflow_telemetry_events", default=None)


MODEL_COSTS_PER_1K_TOKENS: dict[str, tuple[float, float]] = {
    "gpt-4.1-mini": (0.0004, 0.0016),
    "gpt-4.1": (0.002, 0.008),
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4o": (0.0025, 0.01),
}


def begin_capture() -> Token:
    return _telemetry_events.set([])


def end_capture(token: Token) -> list[dict[str, Any]]:
    events = list(_telemetry_events.get() or [])
    _telemetry_events.reset(token)
    return events


def _normalize_model_name(model_name: str) -> str:
    lowered = model_name.lower()
    for known in MODEL_COSTS_PER_1K_TOKENS:
        if known in lowered:
            return known
    return lowered


def estimate_cost_usd(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    normalized = _normalize_model_name(model_name)
    prompt_rate, completion_rate = MODEL_COSTS_PER_1K_TOKENS.get(normalized, (0.0, 0.0))
    return ((prompt_tokens / 1000) * prompt_rate) + ((completion_tokens / 1000) * completion_rate)


def record_llm_call(
    *,
    role: str,
    provider: str,
    model_name: str,
    latency_ms: float,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
) -> None:
    events = _telemetry_events.get()
    if events is None:
        return

    events.append(
        {
            "type": "llm_call",
            "role": role,
            "provider": provider,
            "model_name": model_name,
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": estimate_cost_usd(model_name, prompt_tokens, completion_tokens),
        }
    )


def now_ms() -> float:
    return time.perf_counter() * 1000
