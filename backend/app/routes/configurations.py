from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.domain import ModelPromptConfig, Run
from app.routes._contracts import build_configuration_drilldown, raise_api_error
from app.schemas.run import (
    ConfigurationComparisonSchema,
    ConfigurationDrilldownSchema,
    ModelPromptConfigSchema,
)

router = APIRouter(prefix="/configurations", tags=["configurations"])


async def _load_configurations(db: AsyncSession) -> list[ModelPromptConfig]:
    result = await db.execute(select(ModelPromptConfig).order_by(ModelPromptConfig.created_at.asc()))
    return result.scalars().all()


async def _load_configuration_runs(db: AsyncSession) -> list[Run]:
    result = await db.execute(
        select(Run).options(
            selectinload(Run.telemetry),
            selectinload(Run.executor_config),
            selectinload(Run.judge_config),
            selectinload(Run.escalations),
        )
    )
    return result.scalars().unique().all()


def _build_comparisons(configs: list[ModelPromptConfig], runs: list[Run]) -> list[ConfigurationComparisonSchema]:
    rows: list[ConfigurationComparisonSchema] = []
    for config in configs:
        if config.role == "executor":
            relevant_runs = [run for run in runs if run.executor_config_id == config.id]
        else:
            relevant_runs = [run for run in runs if run.judge_config_id == config.id]

        run_count = len(relevant_runs)
        successful = [run for run in relevant_runs if run.status == "completed"]
        escalated = [run for run in relevant_runs if run.escalations]
        confidences = [run.telemetry.average_confidence for run in relevant_runs if run.telemetry]
        costs = [run.telemetry.total_estimated_cost_usd for run in relevant_runs if run.telemetry]

        rows.append(
            ConfigurationComparisonSchema(
                config_id=config.id,
                role=config.role,
                name=config.name,
                model_name=config.model_name,
                prompt_version=config.prompt_version,
                run_count=run_count,
                success_rate=(len(successful) / run_count) if run_count else 0.0,
                escalation_rate=(len(escalated) / run_count) if run_count else 0.0,
                average_confidence=(sum(confidences) / len(confidences)) if confidences else 0.0,
                average_cost_usd=(sum(costs) / len(costs)) if costs else 0.0,
            )
        )

    return sorted(rows, key=lambda row: (row.role, row.name.lower()))


@router.get("", response_model=list[ModelPromptConfigSchema])
async def list_configurations(db: AsyncSession = Depends(get_db)) -> list[ModelPromptConfigSchema]:
    return await _load_configurations(db)


@router.get("/comparison", response_model=list[ConfigurationComparisonSchema])
async def compare_configurations(db: AsyncSession = Depends(get_db)) -> list[ConfigurationComparisonSchema]:
    return _build_comparisons(await _load_configurations(db), await _load_configuration_runs(db))


@router.get("/{config_id}/drilldown", response_model=ConfigurationDrilldownSchema)
async def configuration_drilldown(config_id: UUID, db: AsyncSession = Depends(get_db)) -> ConfigurationDrilldownSchema:
    configs = await _load_configurations(db)
    runs = await _load_configuration_runs(db)
    comparison = next((item for item in _build_comparisons(configs, runs) if item.config_id == config_id), None)
    if comparison is None:
        raise_api_error(
            status.HTTP_404_NOT_FOUND,
            "configuration_not_found",
            "Configuration not found",
            details={"config_id": str(config_id)},
        )

    if comparison.role == "executor":
        relevant_runs = [run for run in runs if run.executor_config_id == config_id]
    else:
        relevant_runs = [run for run in runs if run.judge_config_id == config_id]
    return build_configuration_drilldown(comparison, relevant_runs)
