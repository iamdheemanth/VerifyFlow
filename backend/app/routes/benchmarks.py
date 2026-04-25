from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import verify_token
from app.db.session import get_db
from app.models.domain import BenchmarkCase, BenchmarkSuite, Run, utcnow
from app.routes.authorization import user_email, user_subject
from app.routes._contracts import build_benchmark_drilldown, raise_api_error
from app.schemas.run import (
    BenchmarkCaseSchema,
    BenchmarkDrilldownSchema,
    BenchmarkOverviewSchema,
    BenchmarkSuiteSchema,
    CreateBenchmarkCaseRequest,
    CreateBenchmarkSuiteRequest,
)

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


async def _load_benchmark_runs(db: AsyncSession, owner_subject: str) -> list[Run]:
    result = await db.execute(
        select(Run).options(
            selectinload(Run.telemetry),
            selectinload(Run.benchmark_suite),
            selectinload(Run.benchmark_case),
            selectinload(Run.escalations),
        )
        .where(Run.kind == "benchmark", Run.owner_subject == owner_subject)
    )
    return result.scalars().unique().all()


def _build_overviews(runs: list[Run]) -> list[BenchmarkOverviewSchema]:
    grouped: dict[str, list[Run]] = defaultdict(list)
    for run in runs:
        key = str(run.benchmark_suite_id or "unscoped")
        grouped[key].append(run)

    overviews: list[BenchmarkOverviewSchema] = []
    for group_runs in grouped.values():
        suite = group_runs[0].benchmark_suite
        run_count = len(group_runs)
        completed = [run for run in group_runs if run.status == "completed"]
        retried = [run for run in group_runs if run.telemetry and run.telemetry.total_retry_count > 0]
        escalated = [run for run in group_runs if run.escalations]
        confidences = [run.telemetry.average_confidence for run in group_runs if run.telemetry]
        labelled_runs = [run for run in group_runs if run.benchmark_case and run.benchmark_case.label_data]
        false_positive_rate = 0.0
        false_negative_rate = 0.0
        if labelled_runs:
            false_positives = 0
            false_negatives = 0
            for run in labelled_runs:
                expected = (run.benchmark_case.label_data or {}).get("expected_verified")
                actual = run.status == "completed"
                if expected is True and actual is False:
                    false_negatives += 1
                if expected is False and actual is True:
                    false_positives += 1
            false_positive_rate = false_positives / len(labelled_runs)
            false_negative_rate = false_negatives / len(labelled_runs)

        overviews.append(
            BenchmarkOverviewSchema(
                suite_id=suite.id if suite else None,
                suite_name=suite.name if suite else "Unscoped benchmark",
                run_count=run_count,
                claim_accuracy=(len(completed) / run_count) if run_count else 0.0,
                verification_pass_rate=(len(completed) / run_count) if run_count else 0.0,
                retry_rate=(len(retried) / run_count) if run_count else 0.0,
                escalation_rate=(len(escalated) / run_count) if run_count else 0.0,
                average_confidence=(sum(confidences) / len(confidences)) if confidences else 0.0,
                false_positive_rate=false_positive_rate,
                false_negative_rate=false_negative_rate,
            )
        )

    return sorted(overviews, key=lambda item: item.suite_name.lower())


def _clean_required(value: str | None, field_name: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise_api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "invalid_benchmark_payload",
            f"{field_name} is required",
            details={"field": field_name},
        )
    return cleaned


async def _get_owned_benchmark_case_or_404(
    db: AsyncSession,
    case_id: UUID,
    owner_subject: str,
) -> BenchmarkCase:
    result = await db.execute(
        select(BenchmarkCase)
        .options(selectinload(BenchmarkCase.suite))
        .where(BenchmarkCase.id == case_id, BenchmarkCase.owner_subject == owner_subject)
    )
    case = result.scalar_one_or_none()
    if case is None:
        raise_api_error(
            status.HTTP_404_NOT_FOUND,
            "benchmark_case_not_found",
            "Benchmark case not found",
            details={"benchmark_case_id": str(case_id)},
        )
    return case


@router.get("/suites", response_model=list[BenchmarkSuiteSchema])
async def list_benchmark_suites(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_token),
) -> list[BenchmarkSuiteSchema]:
    owner = user_subject(current_user)
    result = await db.execute(
        select(BenchmarkSuite)
        .join(BenchmarkSuite.cases)
        .where(BenchmarkCase.owner_subject == owner)
        .order_by(BenchmarkSuite.created_at.asc())
    )
    return result.scalars().unique().all()


@router.get("/cases", response_model=list[BenchmarkCaseSchema])
async def list_benchmark_cases(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_token),
) -> list[BenchmarkCaseSchema]:
    owner = user_subject(current_user)
    result = await db.execute(
        select(BenchmarkCase)
        .where(BenchmarkCase.owner_subject == owner)
        .order_by(BenchmarkCase.created_at.asc())
    )
    return result.scalars().all()


@router.post("/suites", response_model=BenchmarkSuiteSchema, status_code=status.HTTP_201_CREATED)
async def create_benchmark_suite(
    payload: CreateBenchmarkSuiteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_token),
) -> BenchmarkSuiteSchema:
    _owner = user_subject(current_user)
    name = _clean_required(payload.name, "name")
    result = await db.execute(select(BenchmarkSuite).where(BenchmarkSuite.name == name))
    suite = result.scalar_one_or_none()
    if suite is None:
        suite = BenchmarkSuite(name=name, description=payload.description)
        db.add(suite)
        await db.commit()
        await db.refresh(suite)
    return suite


@router.post("/cases", response_model=BenchmarkCaseSchema, status_code=status.HTTP_201_CREATED)
async def create_benchmark_case(
    payload: CreateBenchmarkCaseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_token),
) -> BenchmarkCaseSchema:
    owner = user_subject(current_user)
    suite = None
    if payload.suite_id is not None:
        suite = (
            await db.execute(select(BenchmarkSuite).where(BenchmarkSuite.id == payload.suite_id))
        ).scalar_one_or_none()
        if suite is None:
            raise_api_error(
                status.HTTP_404_NOT_FOUND,
                "benchmark_suite_not_found",
                "Benchmark suite not found",
                details={"suite_id": str(payload.suite_id)},
            )
    else:
        suite_name = _clean_required(payload.suite_name, "suite_name")
        suite = (
            await db.execute(select(BenchmarkSuite).where(BenchmarkSuite.name == suite_name))
        ).scalar_one_or_none()
        if suite is None:
            suite = BenchmarkSuite(name=suite_name, description=payload.suite_description)
            db.add(suite)
            await db.flush()

    case = BenchmarkCase(
        owner_subject=owner,
        owner_email=user_email(current_user),
        suite=suite,
        name=_clean_required(payload.name, "name"),
        goal=_clean_required(payload.goal, "goal"),
        acceptance_criteria=payload.acceptance_criteria,
        expected_outcome=payload.expected_outcome,
        label_data=payload.label_data,
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)
    return case


@router.post("/cases/{case_id}/runs", response_model=dict[str, str], status_code=status.HTTP_201_CREATED)
async def start_benchmark_case_run(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_token),
) -> dict[str, str]:
    case = await _get_owned_benchmark_case_or_404(db, case_id, user_subject(current_user))
    run = Run(
        owner_subject=user_subject(current_user),
        owner_email=user_email(current_user),
        goal=case.goal,
        acceptance_criteria=case.acceptance_criteria,
        status="queued",
        queued_at=utcnow(),
        kind="benchmark",
        benchmark_suite_id=case.suite_id,
        benchmark_case_id=case.id,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return {"run_id": str(run.id), "status": run.status, "kind": run.kind}


@router.get("/overview", response_model=list[BenchmarkOverviewSchema])
async def benchmark_overview(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_token),
) -> list[BenchmarkOverviewSchema]:
    return _build_overviews(await _load_benchmark_runs(db, user_subject(current_user)))


@router.get("/suites/{suite_id}/drilldown", response_model=BenchmarkDrilldownSchema)
async def benchmark_drilldown(
    suite_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_token),
) -> BenchmarkDrilldownSchema:
    runs = await _load_benchmark_runs(db, user_subject(current_user))
    relevant_runs = [run for run in runs if run.benchmark_suite_id == suite_id]
    if not relevant_runs:
        raise_api_error(
            status.HTTP_404_NOT_FOUND,
            "benchmark_suite_not_found",
            "Benchmark suite not found",
            details={"suite_id": str(suite_id)},
        )

    overview = next((item for item in _build_overviews(relevant_runs) if item.suite_id == suite_id), None)
    if overview is None:
        raise_api_error(
            status.HTTP_404_NOT_FOUND,
            "benchmark_suite_not_found",
            "Benchmark suite not found",
            details={"suite_id": str(suite_id)},
        )
    return build_benchmark_drilldown(overview, relevant_runs)
