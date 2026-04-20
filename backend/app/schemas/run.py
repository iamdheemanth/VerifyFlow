from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ErrorDetailSchema(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ApiErrorResponse(BaseModel):
    error: ErrorDetailSchema
    detail: str


class CreateRunRequest(BaseModel):
    goal: str
    acceptance_criteria: str | None = None
    executor_config_id: UUID | None = None
    judge_config_id: UUID | None = None
    benchmark_case_id: UUID | None = None


class ReviewerDecisionRequest(BaseModel):
    decision: str
    notes: str | None = None
    reviewer_key: str
    reviewer_display_name: str | None = None


class TaskSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    index: int
    description: str
    success_criteria: str
    tool_name: str
    tool_params: dict[str, Any]
    status: str
    claimed_result: dict[str, Any] | None
    retry_count: int
    created_at: datetime


class ModelPromptConfigSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    name: str
    model_name: str
    prompt_template: str
    prompt_version: str
    config_metadata: dict[str, Any] | None = None
    created_at: datetime


class BenchmarkSuiteSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    created_at: datetime


class BenchmarkCaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    suite_id: UUID
    name: str
    goal: str
    acceptance_criteria: str | None
    expected_outcome: str | None
    label_data: dict[str, Any] | None = None
    created_at: datetime


class TaskAttemptSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    task_id: UUID
    attempt_index: int
    tool_name: str
    tool_params: dict[str, Any]
    action_claim: dict[str, Any] | None
    verification_payload: dict[str, Any] | None
    execution_steps: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    claimed_success: bool | None
    verification_method: str | None
    final_confidence: float | None
    executor_latency_ms: float | None
    verifier_latency_ms: float | None
    total_latency_ms: float | None
    token_input: int
    token_output: int
    token_total: int
    estimated_cost_usd: float
    outcome: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime


class LedgerEntrySchema(BaseModel):
    id: UUID
    run_id: UUID
    task_id: UUID
    attempt_id: UUID | None
    task_description: str
    verification_method: str
    confidence: float
    verified: bool
    evidence: str
    judge_reasoning: str | None
    created_at: datetime


class RunTelemetrySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    total_executor_latency_ms: float
    total_verifier_latency_ms: float
    total_task_latency_ms: float
    total_retry_count: int
    total_token_input: int
    total_token_output: int
    total_token_total: int
    total_estimated_cost_usd: float
    total_tool_calls: int
    deterministic_verifications: int
    llm_judge_verifications: int
    hybrid_verifications: int
    average_confidence: float
    created_at: datetime
    updated_at: datetime


class ReviewerDecisionSchema(BaseModel):
    id: UUID
    escalation_id: UUID
    run_id: UUID
    task_id: UUID
    reviewer_key: str | None
    reviewer_display_name: str | None
    reviewer_name: str | None
    decision: str
    notes: str | None
    escalation_status: str
    task_status: str
    run_status: str
    reprocess_requested: bool = False
    created_at: datetime


class EscalationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    task_id: UUID
    status: str
    failure_reason: str
    evidence_bundle: dict[str, Any]
    created_at: datetime
    resolved_at: datetime | None
    reviewer_decisions: list[ReviewerDecisionSchema] = []


class ClaimedVsVerifiedSummarySchema(BaseModel):
    total_tasks: int
    pending_tasks: int
    executing_tasks: int
    claimed_tasks: int
    verified_tasks: int
    failed_tasks: int
    escalated_tasks: int


class TaskEvidenceSchema(BaseModel):
    task: TaskSchema
    latest_claim: dict[str, Any] | None = None
    latest_verification: dict[str, Any] | None = None
    attempts: list[TaskAttemptSchema] = []
    ledger_entries: list[LedgerEntrySchema] = []
    escalations: list[EscalationSchema] = []


class TaskInspectionSchema(TaskEvidenceSchema):
    pass


class RunSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    goal: str
    acceptance_criteria: str | None
    status: str
    kind: str
    latest_confidence: float | None
    failure_record: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    tasks: list[TaskSchema]
    telemetry: RunTelemetrySchema | None = None
    task_attempts: list[TaskAttemptSchema] = []
    escalations: list[EscalationSchema] = []
    reviewer_decisions: list[ReviewerDecisionSchema] = []
    executor_config: ModelPromptConfigSchema | None = None
    judge_config: ModelPromptConfigSchema | None = None
    benchmark_suite: BenchmarkSuiteSchema | None = None
    benchmark_case: BenchmarkCaseSchema | None = None


class RunInspectionSchema(BaseModel):
    run: RunSchema
    claimed_vs_verified: ClaimedVsVerifiedSummarySchema
    task_inspections: list[TaskInspectionSchema]


class RunSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    goal: str
    status: str
    kind: str
    latest_confidence: float | None
    created_at: datetime
    task_count: int


class ReliabilityOverviewSchema(BaseModel):
    total_runs: int
    completed_runs: int
    failed_runs: int
    escalated_runs: int
    average_confidence: float
    total_estimated_cost_usd: float
    total_tokens: int


class BenchmarkOverviewSchema(BaseModel):
    suite_id: UUID | None
    suite_name: str
    run_count: int
    claim_accuracy: float
    verification_pass_rate: float
    retry_rate: float
    escalation_rate: float
    average_confidence: float
    false_positive_rate: float
    false_negative_rate: float


class BenchmarkRunDetailSchema(BaseModel):
    run_id: UUID
    run_status: str
    benchmark_case_id: UUID | None
    benchmark_case_name: str | None
    goal: str
    latest_confidence: float | None
    retry_count: int
    escalation_count: int


class BenchmarkDrilldownSchema(BaseModel):
    overview: BenchmarkOverviewSchema
    runs: list[BenchmarkRunDetailSchema]


class ConfigurationComparisonSchema(BaseModel):
    config_id: UUID
    role: str
    name: str
    model_name: str
    prompt_version: str
    run_count: int
    success_rate: float
    escalation_rate: float
    average_confidence: float
    average_cost_usd: float


class ConfigurationRunDetailSchema(BaseModel):
    run_id: UUID
    run_status: str
    goal: str
    latest_confidence: float | None
    retry_count: int
    escalation_count: int
    average_cost_usd: float


class ConfigurationDrilldownSchema(BaseModel):
    comparison: ConfigurationComparisonSchema
    runs: list[ConfigurationRunDetailSchema]
