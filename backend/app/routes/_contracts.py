from __future__ import annotations

from collections import defaultdict
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from app.models.domain import Escalation, LedgerEntry, ReviewerDecision, Run, Task, TaskAttempt
from app.schemas.run import (
    ApiErrorResponse,
    BenchmarkDrilldownSchema,
    BenchmarkOverviewSchema,
    BenchmarkRunDetailSchema,
    ClaimedVsVerifiedSummarySchema,
    ConfigurationComparisonSchema,
    ConfigurationDrilldownSchema,
    ConfigurationRunDetailSchema,
    EscalationSchema,
    LedgerEntrySchema,
    ReviewerDecisionSchema,
    RunInspectionSchema,
    RunSchema,
    RunSummarySchema,
    TaskAttemptSchema,
    TaskEvidenceSchema,
    TaskInspectionSchema,
    TaskSchema,
)


def build_api_error(
    code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = ApiErrorResponse(
        error={"code": code, "message": message, "details": details},
        detail=message,
    )
    return payload.model_dump()


def raise_api_error(
    status_code: int,
    code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
) -> None:
    raise HTTPException(status_code=status_code, detail=build_api_error(code, message, details=details))


def error_code_for_status(status_code: int) -> str:
    return {
        status.HTTP_400_BAD_REQUEST: "bad_request",
        status.HTTP_404_NOT_FOUND: "not_found",
        status.HTTP_409_CONFLICT: "conflict",
    }.get(status_code, "request_error")


def to_run_summary(run: Run) -> RunSummarySchema:
    return RunSummarySchema(
        id=run.id,
        goal=run.goal,
        status=run.status,
        kind=run.kind,
        latest_confidence=run.latest_confidence,
        created_at=run.created_at,
        task_count=len(run.tasks),
    )


def to_reviewer_decision_schema(
    decision: ReviewerDecision,
    *,
    escalation_status: str,
    task_status: str,
    run_status: str,
    reprocess_requested: bool = False,
) -> ReviewerDecisionSchema:
    return ReviewerDecisionSchema(
        id=decision.id,
        escalation_id=decision.escalation_id,
        run_id=decision.run_id,
        task_id=decision.task_id,
        reviewer_key=decision.reviewer_key,
        reviewer_display_name=decision.reviewer_display_name,
        reviewer_name=decision.reviewer_name,
        decision=decision.decision,
        notes=decision.notes,
        escalation_status=escalation_status,
        task_status=task_status,
        run_status=run_status,
        reprocess_requested=reprocess_requested,
        created_at=decision.created_at,
    )


def to_escalation_schema(
    escalation: Escalation,
    *,
    task_status: str,
    run_status: str,
) -> EscalationSchema:
    return EscalationSchema(
        id=escalation.id,
        run_id=escalation.run_id,
        task_id=escalation.task_id,
        status=escalation.status,
        failure_reason=escalation.failure_reason,
        evidence_bundle=escalation.evidence_bundle,
        created_at=escalation.created_at,
        resolved_at=escalation.resolved_at,
        reviewer_decisions=[
            to_reviewer_decision_schema(
                decision,
                escalation_status=escalation.status,
                task_status=task_status,
                run_status=run_status,
                reprocess_requested=decision.decision == "send_back",
            )
            for decision in escalation.reviewer_decisions
        ],
    )


def to_ledger_entry_schema(entry: LedgerEntry, *, task_description: str) -> LedgerEntrySchema:
    return LedgerEntrySchema(
        id=entry.id,
        run_id=entry.run_id,
        task_id=entry.task_id,
        attempt_id=entry.attempt_id,
        task_description=task_description,
        verification_method=entry.verification_method,
        confidence=entry.confidence,
        verified=entry.verified,
        evidence=entry.evidence,
        judge_reasoning=entry.judge_reasoning,
        created_at=entry.created_at,
    )


def build_claimed_vs_verified_summary(tasks: list[Task]) -> ClaimedVsVerifiedSummarySchema:
    statuses = [task.status for task in tasks]
    return ClaimedVsVerifiedSummarySchema(
        total_tasks=len(tasks),
        pending_tasks=sum(1 for status in statuses if status == "pending"),
        executing_tasks=sum(1 for status in statuses if status == "executing"),
        claimed_tasks=sum(1 for status in statuses if status == "claimed"),
        verified_tasks=sum(1 for status in statuses if status == "verified"),
        failed_tasks=sum(1 for status in statuses if status == "failed"),
        escalated_tasks=sum(1 for status in statuses if status == "escalated"),
    )


def to_run_schema(run: Run) -> RunSchema:
    run.tasks.sort(key=lambda task: task.index)
    run.task_attempts.sort(key=lambda attempt: (attempt.task_id, attempt.attempt_index, attempt.created_at))
    task_by_id = {task.id: task for task in run.tasks}
    escalation_by_id = {escalation.id: escalation for escalation in run.escalations}
    run_reviewer_decisions = [
        to_reviewer_decision_schema(
            decision,
            escalation_status=escalation_by_id.get(decision.escalation_id).status if escalation_by_id.get(decision.escalation_id) else "unknown",
            task_status=task_by_id.get(decision.task_id).status if task_by_id.get(decision.task_id) else "unknown",
            run_status=run.status,
            reprocess_requested=decision.decision == "send_back",
        )
        for decision in run.reviewer_decisions
    ]

    return RunSchema(
        id=run.id,
        goal=run.goal,
        acceptance_criteria=run.acceptance_criteria,
        status=run.status,
        kind=run.kind,
        latest_confidence=run.latest_confidence,
        failure_record=run.failure_record,
        created_at=run.created_at,
        updated_at=run.updated_at,
        tasks=[TaskSchema.model_validate(task) for task in run.tasks],
        telemetry=run.telemetry,
        task_attempts=[TaskAttemptSchema.model_validate(attempt) for attempt in run.task_attempts],
        escalations=[
            to_escalation_schema(
                escalation,
                task_status=task_by_id.get(escalation.task_id).status if task_by_id.get(escalation.task_id) else "unknown",
                run_status=run.status,
            )
            for escalation in run.escalations
        ],
        reviewer_decisions=run_reviewer_decisions,
        executor_config=run.executor_config,
        judge_config=run.judge_config,
        benchmark_suite=run.benchmark_suite,
        benchmark_case=run.benchmark_case,
    )


def build_run_inspection(run: Run) -> RunInspectionSchema:
    task_attempts_by_task: dict[UUID, list[TaskAttempt]] = defaultdict(list)
    for attempt in run.task_attempts:
        task_attempts_by_task[attempt.task_id].append(attempt)

    ledger_by_task: dict[UUID, list[LedgerEntry]] = defaultdict(list)
    for entry in run.ledger_entries:
        ledger_by_task[entry.task_id].append(entry)

    escalations_by_task: dict[UUID, list[Escalation]] = defaultdict(list)
    for escalation in run.escalations:
        escalations_by_task[escalation.task_id].append(escalation)

    task_inspections: list[TaskInspectionSchema] = []
    for task in run.tasks:
        attempts = sorted(task_attempts_by_task.get(task.id, []), key=lambda item: (item.attempt_index, item.created_at))
        ledger_entries = sorted(ledger_by_task.get(task.id, []), key=lambda item: item.created_at)
        escalations = escalations_by_task.get(task.id, [])
        latest_attempt = attempts[-1] if attempts else None
        latest_verification = latest_attempt.verification_payload if latest_attempt is not None else None
        latest_claim = latest_attempt.action_claim if latest_attempt is not None else task.claimed_result

        task_inspections.append(
            TaskInspectionSchema(
                task=TaskSchema.model_validate(task),
                latest_claim=latest_claim,
                latest_verification=latest_verification,
                attempts=[TaskAttemptSchema.model_validate(attempt) for attempt in attempts],
                ledger_entries=[
                    to_ledger_entry_schema(entry, task_description=task.description)
                    for entry in ledger_entries
                ],
                escalations=[
                    to_escalation_schema(
                        escalation,
                        task_status=task.status,
                        run_status=run.status,
                    )
                    for escalation in escalations
                ],
            )
        )

    return RunInspectionSchema(
        run=to_run_schema(run),
        claimed_vs_verified=build_claimed_vs_verified_summary(run.tasks),
        task_inspections=task_inspections,
    )


def build_task_evidence(run: Run, task: Task) -> TaskEvidenceSchema:
    attempts = sorted(
        [attempt for attempt in run.task_attempts if attempt.task_id == task.id],
        key=lambda item: (item.attempt_index, item.created_at),
    )
    ledger_entries = sorted(
        [entry for entry in run.ledger_entries if entry.task_id == task.id],
        key=lambda item: item.created_at,
    )
    escalations = [escalation for escalation in run.escalations if escalation.task_id == task.id]
    latest_attempt = attempts[-1] if attempts else None
    latest_claim = latest_attempt.action_claim if latest_attempt is not None else task.claimed_result
    latest_verification = latest_attempt.verification_payload if latest_attempt is not None else None

    return TaskEvidenceSchema(
        task=TaskSchema.model_validate(task),
        latest_claim=latest_claim,
        latest_verification=latest_verification,
        attempts=[TaskAttemptSchema.model_validate(attempt) for attempt in attempts],
        ledger_entries=[to_ledger_entry_schema(entry, task_description=task.description) for entry in ledger_entries],
        escalations=[
            to_escalation_schema(
                escalation,
                task_status=task.status,
                run_status=run.status,
            )
            for escalation in escalations
        ],
    )


def build_benchmark_drilldown(
    overview: BenchmarkOverviewSchema,
    runs: list[Run],
) -> BenchmarkDrilldownSchema:
    return BenchmarkDrilldownSchema(
        overview=overview,
        runs=[
            BenchmarkRunDetailSchema(
                run_id=run.id,
                run_status=run.status,
                benchmark_case_id=run.benchmark_case_id,
                benchmark_case_name=run.benchmark_case.name if run.benchmark_case else None,
                goal=run.goal,
                latest_confidence=run.latest_confidence,
                retry_count=run.telemetry.total_retry_count if run.telemetry else 0,
                escalation_count=len(run.escalations),
            )
            for run in runs
        ],
    )


def build_configuration_drilldown(
    comparison: ConfigurationComparisonSchema,
    runs: list[Run],
) -> ConfigurationDrilldownSchema:
    return ConfigurationDrilldownSchema(
        comparison=comparison,
        runs=[
            ConfigurationRunDetailSchema(
                run_id=run.id,
                run_status=run.status,
                goal=run.goal,
                latest_confidence=run.latest_confidence,
                retry_count=run.telemetry.total_retry_count if run.telemetry else 0,
                escalation_count=len(run.escalations),
                average_cost_usd=run.telemetry.total_estimated_cost_usd if run.telemetry else 0.0,
            )
            for run in runs
        ],
    )
