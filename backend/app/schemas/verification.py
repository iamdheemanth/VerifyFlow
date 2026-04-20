from typing import Any, Literal

from pydantic import BaseModel, Field


class VerificationResult(BaseModel):
    verified: bool
    confidence: float = Field(ge=0.0, le=1.0)
    method: Literal["deterministic", "llm_judge", "hybrid"]
    evidence: str
    outcome: Literal[
        "verified",
        "execution_failed",
        "evidence_missing",
        "inconclusive",
        "not_applicable",
    ] = "inconclusive"
    summary: str | None = None
    expected_evidence: list[str] = Field(default_factory=list)
    observed_evidence: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    failure_indicators: list[str] = Field(default_factory=list)
    ambiguity_reason: str | None = None
    error_details: dict[str, Any] | None = None
    judge_reasoning: str | None = None
