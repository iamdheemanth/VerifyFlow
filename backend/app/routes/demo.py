from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_token
from app.db.session import get_db
from app.models.domain import (
    BenchmarkCase,
    BenchmarkSuite,
    Escalation,
    ModelPromptConfig,
    ReviewerDecision,
    Run,
    RunTelemetry,
    Task,
    TaskAttempt,
)
from app.routes.authorization import user_email, user_subject

router = APIRouter(prefix="/demo", tags=["demo"])

DEMO_SUITE_NAME = "Reliability Smoke Suite"
DEMO_GOOGLE_CASE_NAME = "Google Search Result Verification"
DEMO_WIKIPEDIA_CASE_NAME = "Wikipedia English Link Verification"


@router.post("/seed")
async def seed_demo_data(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_token),
) -> dict[str, int | str]:
    owner = user_subject(current_user)
    suite = (
        await db.execute(
            select(BenchmarkSuite).where(BenchmarkSuite.name == DEMO_SUITE_NAME)
        )
    ).scalar_one_or_none()
    if suite is not None:
        existing_demo_runs = (
            await db.execute(
                select(Run.id).where(
                    Run.owner_subject == owner,
                    Run.kind == "benchmark",
                    Run.benchmark_suite_id == suite.id,
                )
            )
        ).scalars().first()
        if existing_demo_runs is not None:
            return {
                "created_runs": 0,
                "created_suites": 0,
                "created_cases": 0,
                "message": "No new demo data was created. Demo benchmark data already exists for this account.",
            }

    executor_config = ModelPromptConfig(
        role="executor",
        name="Baseline Executor",
        model_name="executor-model",
        prompt_template="Plan the minimum set of verifiable steps.",
        prompt_version="v1",
        config_metadata={"family": "baseline"},
    )
    judge_config = ModelPromptConfig(
        role="judge",
        name="Adversarial Judge",
        model_name="judge-model",
        prompt_template="Find evidence of failure before considering success.",
        prompt_version="v1",
        config_metadata={"stance": "skeptical"},
    )
    created_suites = 0
    if suite is None:
        suite = BenchmarkSuite(
            name=DEMO_SUITE_NAME,
            description="Small benchmark suite for replaying representative verification flows.",
        )
        db.add(suite)
        await db.flush()
        created_suites = 1

    case = (
        await db.execute(
            select(BenchmarkCase).where(
                BenchmarkCase.suite_id == suite.id,
                BenchmarkCase.name == DEMO_GOOGLE_CASE_NAME,
                BenchmarkCase.owner_subject == owner,
            )
        )
    ).scalar_one_or_none()
    created_cases = 0
    if case is None:
        case = BenchmarkCase(
            owner_subject=owner,
            owner_email=user_email(current_user),
            suite=suite,
            name=DEMO_GOOGLE_CASE_NAME,
            goal="Navigate to https://www.google.com/search?q=OpenAI and verify that the results page contains the text OpenAI",
            acceptance_criteria="The browser opens the Google search results page for OpenAI and the visible page text or page title contains OpenAI.",
            expected_outcome="completed",
            label_data={"expected_verified": True},
        )
        db.add(case)
        created_cases += 1

    escalated_case = (
        await db.execute(
            select(BenchmarkCase).where(
                BenchmarkCase.suite_id == suite.id,
                BenchmarkCase.name == DEMO_WIKIPEDIA_CASE_NAME,
                BenchmarkCase.owner_subject == owner,
            )
        )
    ).scalar_one_or_none()
    if escalated_case is None:
        escalated_case = BenchmarkCase(
            owner_subject=owner,
            owner_email=user_email(current_user),
            suite=suite,
            name=DEMO_WIKIPEDIA_CASE_NAME,
            goal="Navigate to https://www.wikipedia.org, click the English language link, and verify that the destination page contains The Free Encyclopedia",
            acceptance_criteria="The browser opens https://www.wikipedia.org, clicks the English language link, and the destination page contains The Free Encyclopedia in the visible page text or title.",
            expected_outcome="needs_review",
            label_data={"expected_verified": False},
        )
        db.add(escalated_case)
        created_cases += 1

    completed_run = Run(
        owner_subject=owner,
        owner_email=user_email(current_user),
        goal=case.goal,
        acceptance_criteria=case.acceptance_criteria,
        status="completed",
        kind="benchmark",
        latest_confidence=1.0,
        executor_config=executor_config,
        judge_config=judge_config,
        benchmark_suite=suite,
        benchmark_case=case,
    )
    completed_task = Task(
        run=completed_run,
        index=0,
        description="Open the Google search results page.",
        success_criteria=case.acceptance_criteria,
        tool_name="browser.navigate",
        tool_params={"url": "https://www.google.com/search?q=OpenAI", "expected_text": "OpenAI"},
        status="verified",
        claimed_result={"claimed_success": True, "result": {"structured_content": {"matched_text": True}}},
        retry_count=0,
    )
    completed_attempt = TaskAttempt(
        run=completed_run,
        task=completed_task,
        attempt_index=0,
        tool_name="browser.navigate",
        tool_params={"url": "https://www.google.com/search?q=OpenAI", "expected_text": "OpenAI"},
        action_claim={"claimed_success": True},
        verification_payload={"verified": True, "confidence": 1.0, "method": "deterministic"},
        execution_steps=[
            {"type": "planned", "description": "Open the Google search results page."},
            {"type": "claimed", "action_claim": {"claimed_success": True}},
            {"type": "verified", "verification_payload": {"verified": True, "confidence": 1.0}},
        ],
        tool_calls=[{"tool_name": "browser.navigate"}],
        claimed_success=True,
        verification_method="deterministic",
        final_confidence=1.0,
        executor_latency_ms=810.0,
        verifier_latency_ms=120.0,
        total_latency_ms=930.0,
        token_input=0,
        token_output=0,
        token_total=0,
        estimated_cost_usd=0.0,
        outcome="verified",
    )
    completed_telemetry = RunTelemetry(
        run=completed_run,
        total_executor_latency_ms=810.0,
        total_verifier_latency_ms=120.0,
        total_task_latency_ms=930.0,
        total_retry_count=0,
        total_token_input=0,
        total_token_output=0,
        total_token_total=0,
        total_estimated_cost_usd=0.0,
        total_tool_calls=1,
        deterministic_verifications=1,
        llm_judge_verifications=0,
        hybrid_verifications=0,
        average_confidence=1.0,
    )

    escalated_run = Run(
        owner_subject=owner,
        owner_email=user_email(current_user),
        goal=escalated_case.goal,
        acceptance_criteria=escalated_case.acceptance_criteria,
        status="failed",
        kind="benchmark",
        latest_confidence=0.0,
        executor_config=executor_config,
        judge_config=judge_config,
        benchmark_suite=suite,
        benchmark_case=escalated_case,
    )
    escalated_task = Task(
        run=escalated_run,
        index=0,
        description="Click the English language link.",
        success_criteria="The destination page contains The Free Encyclopedia.",
        tool_name="browser.click",
        tool_params={"selectors": ["link=English", "text=English"], "expected_text": "The Free Encyclopedia"},
        status="escalated",
        claimed_result={"claimed_success": True, "result": {"structured_content": {"clicked": True}}},
        retry_count=3,
    )
    escalated_attempt = TaskAttempt(
        run=escalated_run,
        task=escalated_task,
        attempt_index=3,
        tool_name="browser.click",
        tool_params={"selectors": ["link=English", "text=English"], "expected_text": "The Free Encyclopedia"},
        action_claim={"claimed_success": True},
        verification_payload={"verified": False, "confidence": 0.0, "method": "hybrid"},
        execution_steps=[
            {"type": "planned", "description": "Click the English language link."},
            {"type": "claimed", "action_claim": {"claimed_success": True}},
            {"type": "verified", "verification_payload": {"verified": False, "confidence": 0.0}},
        ],
        tool_calls=[{"tool_name": "browser.click"}],
        claimed_success=True,
        verification_method="hybrid",
        final_confidence=0.0,
        executor_latency_ms=900.0,
        verifier_latency_ms=340.0,
        total_latency_ms=1240.0,
        token_input=850,
        token_output=120,
        token_total=970,
        estimated_cost_usd=0.002,
        outcome="escalated",
        error="Expected text was not proven on the destination page.",
    )
    escalated_telemetry = RunTelemetry(
        run=escalated_run,
        total_executor_latency_ms=900.0,
        total_verifier_latency_ms=340.0,
        total_task_latency_ms=1240.0,
        total_retry_count=3,
        total_token_input=850,
        total_token_output=120,
        total_token_total=970,
        total_estimated_cost_usd=0.002,
        total_tool_calls=1,
        deterministic_verifications=0,
        llm_judge_verifications=1,
        hybrid_verifications=1,
        average_confidence=0.0,
    )
    escalation = Escalation(
        run=escalated_run,
        task=escalated_task,
        status="approved",
        failure_reason="Confidence remained below threshold after retries.",
        evidence_bundle={
            "planned": escalated_task.description,
            "claimed": escalated_task.claimed_result,
            "verified": {"confidence": 0.0, "method": "hybrid"},
        },
    )
    reviewer_decision = ReviewerDecision(
        escalation=escalation,
        run=escalated_run,
        task=escalated_task,
        reviewer_name="Reliability Reviewer",
        decision="approve",
        notes="Escalation was appropriate because the click outcome could not be proven.",
    )

    db.add_all(
        [
            executor_config,
            judge_config,
            suite,
            case,
            escalated_case,
            completed_run,
            completed_task,
            completed_attempt,
            completed_telemetry,
            escalated_run,
            escalated_task,
            escalated_attempt,
            escalated_telemetry,
            escalation,
            reviewer_decision,
        ]
    )
    await db.commit()
    return {
        "created_runs": 2,
        "created_suites": created_suites,
        "created_cases": created_cases,
        "message": "Demo benchmark data created.",
    }
