from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.domain import ModelPromptConfig, Run
from app.schemas.run import ConfigurationComparisonSchema, ModelPromptConfigSchema

router = APIRouter(prefix="/configurations", tags=["configurations"])


@router.get("", response_model=list[ModelPromptConfigSchema])
async def list_configurations(db: AsyncSession = Depends(get_db)) -> list[ModelPromptConfigSchema]:
    result = await db.execute(select(ModelPromptConfig).order_by(ModelPromptConfig.created_at.asc()))
    return result.scalars().all()


@router.get("/comparison", response_model=list[ConfigurationComparisonSchema])
async def compare_configurations(db: AsyncSession = Depends(get_db)) -> list[ConfigurationComparisonSchema]:
    configs = (await db.execute(select(ModelPromptConfig))).scalars().all()
    runs = (
        await db.execute(
            select(Run).options(selectinload(Run.telemetry), selectinload(Run.executor_config), selectinload(Run.judge_config))
        )
    ).scalars().unique().all()

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
