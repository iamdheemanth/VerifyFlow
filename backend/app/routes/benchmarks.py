from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.domain import BenchmarkSuite, Run
from app.routes._contracts import build_benchmark_drilldown, raise_api_error
from app.schemas.run import (
    BenchmarkCaseSchema,
    BenchmarkDrilldownSchema,
    BenchmarkOverviewSchema,
    BenchmarkSuiteSchema,
)

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


async def _load_benchmark_runs(db: AsyncSession) -> list[Run]:
    result = await db.execute(
        select(Run).options(
            selectinload(Run.telemetry),
            selectinload(Run.benchmark_suite),
            selectinload(Run.benchmark_case),
            selectinload(Run.escalations),
        )
        .where(Run.kind == "benchmark")
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


@router.get("/suites", response_model=list[BenchmarkSuiteSchema])
async def list_benchmark_suites(db: AsyncSession = Depends(get_db)) -> list[BenchmarkSuiteSchema]:
    result = await db.execute(select(BenchmarkSuite).order_by(BenchmarkSuite.created_at.asc()))
    return result.scalars().all()


@router.get("/cases", response_model=list[BenchmarkCaseSchema])
async def list_benchmark_cases(db: AsyncSession = Depends(get_db)) -> list[BenchmarkCaseSchema]:
    result = await db.execute(
        select(BenchmarkSuite)
        .options(selectinload(BenchmarkSuite.cases))
        .order_by(BenchmarkSuite.created_at.asc())
    )
    suites = result.scalars().unique().all()
    cases = []
    for suite in suites:
        cases.extend(suite.cases)
    return cases


@router.get("/overview", response_model=list[BenchmarkOverviewSchema])
async def benchmark_overview(db: AsyncSession = Depends(get_db)) -> list[BenchmarkOverviewSchema]:
    return _build_overviews(await _load_benchmark_runs(db))


@router.get("/suites/{suite_id}/drilldown", response_model=BenchmarkDrilldownSchema)
async def benchmark_drilldown(suite_id: UUID, db: AsyncSession = Depends(get_db)) -> BenchmarkDrilldownSchema:
    runs = await _load_benchmark_runs(db)
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
