from typing import Literal

from pydantic import BaseModel, Field


class VerificationResult(BaseModel):
    verified: bool
    confidence: float = Field(ge=0.0, le=1.0)
    method: Literal["deterministic", "llm_judge", "hybrid"]
    evidence: str
    judge_reasoning: str | None = None
