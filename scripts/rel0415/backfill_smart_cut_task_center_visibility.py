#!/usr/bin/env python3
"""Backfill Smart Cut task-center visibility fields for legacy tasks."""

from __future__ import annotations

import argparse
from collections.abc import Iterable

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from apps.models.task import SmartCutTask
from apps.services.smart_cut_contract import should_be_visible_in_task_center
from configs.database import create_session_factory, get_database_url


COLUMN_DDL = {
    "task_title": "ALTER TABLE smart_cut_tasks ADD COLUMN task_title VARCHAR(128)",
    "visible_in_task_center": (
        "ALTER TABLE smart_cut_tasks "
        "ADD COLUMN visible_in_task_center BOOLEAN NOT NULL DEFAULT false"
    ),
    "session_scope_id": "ALTER TABLE smart_cut_tasks ADD COLUMN session_scope_id VARCHAR(128)",
}


def ensure_columns(session: Session) -> list[str]:
    inspector = inspect(session.bind)
    existing_columns = {column["name"] for column in inspector.get_columns("smart_cut_tasks")}
    added: list[str] = []
    for column_name, ddl in COLUMN_DDL.items():
        if column_name in existing_columns:
            continue
        session.execute(text(ddl))
        added.append(column_name)
    if added:
        session.commit()
    return added


def backfill_visibility(session: Session) -> tuple[int, int, int]:
    rows = session.query(SmartCutTask).all()
    hidden_statuses: set[str] = set()
    visible_statuses: set[str] = set()
    updated_count = 0

    for task in rows:
        expected_visibility = should_be_visible_in_task_center(task.status.value)
        if expected_visibility:
            visible_statuses.add(task.status.value)
        else:
            hidden_statuses.add(task.status.value)

        if task.visible_in_task_center != expected_visibility:
            task.visible_in_task_center = expected_visibility
            updated_count += 1

    session.commit()
    return updated_count, len(hidden_statuses), len(visible_statuses)


def format_columns(columns: Iterable[str]) -> str:
    values = list(columns)
    return ", ".join(values) if values else "(none)"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add/backfill Smart Cut task-center visibility columns for legacy tasks.",
    )
    parser.add_argument(
        "--database-url",
        default=get_database_url(),
        help="Database URL. Defaults to DATABASE_URL or the repo SQLite DB.",
    )
    args = parser.parse_args()

    session_factory = create_session_factory(args.database_url)
    with session_factory() as session:
        added_columns = ensure_columns(session)
        updated_count, hidden_count, visible_count = backfill_visibility(session)

    print(f"database_url={args.database_url}")
    print(f"added_columns={format_columns(added_columns)}")
    print(f"updated_rows={updated_count}")
    print(f"hidden_status_count={hidden_count}")
    print(f"visible_status_count={visible_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
