from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/seed")
async def seed_demo_data(db: AsyncSession = Depends(get_db)) -> dict[str, int]:
    existing_runs = (await db.execute(select(Run.id))).scalars().all()
    if existing_runs:
        return {"created_runs": 0}

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
    suite = BenchmarkSuite(
        name="Reliability Smoke Suite",
        description="Small benchmark suite for replaying representative verification flows.",
    )
    case = BenchmarkCase(
        suite=suite,
        name="Google Search Result Verification",
        goal="Navigate to https://www.google.com/search?q=OpenAI and verify that the results page contains the text OpenAI",
        acceptance_criteria="The browser opens the Google search results page for OpenAI and the visible page text or page title contains OpenAI.",
        expected_outcome="completed",
        label_data={"expected_verified": True},
    )

    completed_run = Run(
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
        goal="Navigate to https://www.wikipedia.org, click the English language link, and verify that the destination page contains The Free Encyclopedia",
        acceptance_criteria="The browser opens https://www.wikipedia.org, clicks the English language link, and the destination page contains The Free Encyclopedia in the visible page text or title.",
        status="failed",
        kind="standard",
        latest_confidence=0.0,
        executor_config=executor_config,
        judge_config=judge_config,
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
    return {"created_runs": 2}
