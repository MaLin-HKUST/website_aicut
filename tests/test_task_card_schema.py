from pathlib import Path

from sqlalchemy import inspect

from configs.database import build_engine, init_db


def test_task_card_schema_creates_task_runs_and_additive_columns(tmp_path: Path) -> None:
    db_path = tmp_path / "taskcard.db"
    engine = build_engine(f"sqlite:///{db_path}")

    init_db(bind_engine=engine)

    inspector = inspect(engine)

    assert inspector.has_table("smart_cut_tasks")
    assert inspector.has_table("smart_cut_task_runs")

    task_columns = {column["name"] for column in inspector.get_columns("smart_cut_tasks")}
    assert "company_id" in task_columns
    assert "current_run_id" in task_columns
    assert "latest_successful_run_id" in task_columns
    assert "failed_stage" in task_columns
    assert "abandoned_at" in task_columns
    assert "revision_count" in task_columns

    run_columns = {column["name"] for column in inspector.get_columns("smart_cut_task_runs")}
    assert {
        "id",
        "task_id",
        "run_type",
        "status",
        "sequence_number",
        "scheduler_task_id",
        "source_edit_id",
        "payload_snapshot",
        "result_snapshot",
        "error_message",
    }.issubset(run_columns)
