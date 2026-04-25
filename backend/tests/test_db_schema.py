from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import mkstemp
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.models import domain as _domain  # noqa: F401
from app.db.session import Base, _sync_database_url


def _sqlite_url() -> tuple[str, Path]:
    fd, raw_path = mkstemp(suffix=".db")
    os.close(fd)
    path = Path(raw_path)
    return f"sqlite+aiosqlite:///{path.as_posix()}", path


def _alembic_config() -> Config:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    return config


@pytest.mark.asyncio
async def test_schema_exposes_expected_indexes_constraints_and_reviewer_identity_fields():
    database_url, path = _sqlite_url()
    engine = create_async_engine(database_url, future=True)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

            def _inspect(sync_conn):
                schema = inspect(sync_conn)
                return {
                    "runs_indexes": {item["name"] for item in schema.get_indexes("runs")},
                    "tasks_uniques": {item["name"] for item in schema.get_unique_constraints("tasks")},
                    "task_attempt_uniques": {item["name"] for item in schema.get_unique_constraints("task_attempts")},
                    "run_columns": {item["name"] for item in schema.get_columns("runs")},
                    "reviewer_columns": {item["name"] for item in schema.get_columns("reviewer_decisions")},
                    "ledger_foreign_keys": schema.get_foreign_keys("ledger_entries"),
                }

            inspected = await conn.run_sync(_inspect)

        assert "ix_runs_status_created_at" in inspected["runs_indexes"]
        assert "ix_runs_kind_created_at" in inspected["runs_indexes"]
        assert "ix_runs_owner_subject_created_at" in inspected["runs_indexes"]
        assert "uq_tasks_run_id_index" in inspected["tasks_uniques"]
        assert "uq_task_attempts_task_id_attempt_index" in inspected["task_attempt_uniques"]
        assert "failure_record" in inspected["run_columns"]
        assert {"owner_subject", "owner_email"} <= inspected["run_columns"]
        assert {"reviewer_key", "reviewer_display_name", "reviewer_name"} <= inspected["reviewer_columns"]
        assert any(
            foreign_key["constrained_columns"] == ["run_id"]
            and (foreign_key.get("options") or {}).get("ondelete") == "CASCADE"
            for foreign_key in inspected["ledger_foreign_keys"]
        )
    finally:
        await engine.dispose()
        path.unlink(missing_ok=True)


def test_sync_database_url_normalizes_async_driver_urls():
    assert _sync_database_url("postgresql+asyncpg://user:pass@localhost/db") == "postgresql://user:pass@localhost/db"
    assert _sync_database_url("sqlite+aiosqlite:///tmp/test.db") == "sqlite:///tmp/test.db"
    assert _sync_database_url("postgresql://user:pass@localhost/db") == "postgresql://user:pass@localhost/db"


def test_alembic_history_has_single_head_and_expected_revision_chain():
    script = ScriptDirectory.from_config(_alembic_config())

    heads = script.get_heads()
    revisions = [revision.revision for revision in script.walk_revisions(base="base", head="heads")]

    assert len(heads) == 1
    assert heads[0] == "e7a1b0c9d2f4"
    assert revisions == ["e7a1b0c9d2f4", "c4c2a6ee8d1e", "d3f532773223", "a7a25d8f0c31", "4e4263e2402a"]


def test_alembic_upgrade_from_reliability_expansion_checkpoint_preserves_legacy_reviewer_data(monkeypatch: pytest.MonkeyPatch):
    database_url, path = _sqlite_url()
    sync_url = _sync_database_url(database_url)
    config = _alembic_config()
    monkeypatch.setenv("DATABASE_URL", database_url)

    run_id = str(uuid4())
    task_id = str(uuid4())
    escalation_id = str(uuid4())
    reviewer_decision_id = str(uuid4())

    try:
        command.upgrade(config, "a7a25d8f0c31")

        engine = create_engine(sync_url, future=True)
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO runs (id, goal, acceptance_criteria, status)
                        VALUES (:id, :goal, :acceptance_criteria, :status)
                        """
                    ),
                    {
                        "id": run_id,
                        "goal": "Legacy upgraded run",
                        "acceptance_criteria": "Upgrade should preserve reviewer history",
                        "status": "failed",
                    },
                )
                conn.execute(
                    text(
                        """
                        INSERT INTO tasks (
                            id, run_id, "index", description, success_criteria,
                            tool_name, tool_params, status, retry_count
                        )
                        VALUES (
                            :id, :run_id, :index, :description, :success_criteria,
                            :tool_name, :tool_params, :status, :retry_count
                        )
                        """
                    ),
                    {
                        "id": task_id,
                        "run_id": run_id,
                        "index": 0,
                        "description": "Legacy escalated task",
                        "success_criteria": "Task remains queryable after upgrade",
                        "tool_name": "browser.click",
                        "tool_params": json.dumps({"selector": "text=English"}),
                        "status": "escalated",
                        "retry_count": 1,
                    },
                )
                conn.execute(
                    text(
                        """
                        INSERT INTO escalations (id, run_id, task_id, status, failure_reason, evidence_bundle)
                        VALUES (:id, :run_id, :task_id, :status, :failure_reason, :evidence_bundle)
                        """
                    ),
                    {
                        "id": escalation_id,
                        "run_id": run_id,
                        "task_id": task_id,
                        "status": "approved",
                        "failure_reason": "Legacy escalation awaiting upgraded reviewer metadata",
                        "evidence_bundle": json.dumps({"source": "legacy-upgrade-test"}),
                    },
                )
                conn.execute(
                    text(
                        """
                        INSERT INTO reviewer_decisions (
                            id, escalation_id, run_id, task_id, reviewer_name, decision, notes
                        )
                        VALUES (
                            :id, :escalation_id, :run_id, :task_id, :reviewer_name, :decision, :notes
                        )
                        """
                    ),
                    {
                        "id": reviewer_decision_id,
                        "escalation_id": escalation_id,
                        "run_id": run_id,
                        "task_id": task_id,
                        "reviewer_name": "Legacy Reviewer",
                        "decision": "approve",
                        "notes": "Approved before reviewer identity hardening.",
                    },
                )
        finally:
            engine.dispose()

        command.upgrade(config, "head")

        engine = create_engine(sync_url, future=True)
        try:
            with engine.connect() as conn:
                schema = inspect(conn)
                reviewer_columns = {item["name"] for item in schema.get_columns("reviewer_decisions")}
                run_columns = {item["name"] for item in schema.get_columns("runs")}
                alembic_revision = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                reviewer_row = conn.execute(
                    text(
                        """
                        SELECT reviewer_name, reviewer_display_name, reviewer_key, decision, notes
                        FROM reviewer_decisions
                        WHERE id = :id
                        """
                    ),
                    {"id": reviewer_decision_id},
                ).mappings().one()
        finally:
            engine.dispose()

        assert alembic_revision == "e7a1b0c9d2f4"
        assert {"reviewer_name", "reviewer_display_name", "reviewer_key"} <= reviewer_columns
        assert "failure_record" in run_columns
        assert {"owner_subject", "owner_email"} <= run_columns
        assert reviewer_row["reviewer_name"] == "Legacy Reviewer"
        assert reviewer_row["reviewer_display_name"] == "Legacy Reviewer"
        assert reviewer_row["reviewer_key"] is None
        assert reviewer_row["decision"] == "approve"
        assert reviewer_row["notes"] == "Approved before reviewer identity hardening."
    finally:
        path.unlink(missing_ok=True)
