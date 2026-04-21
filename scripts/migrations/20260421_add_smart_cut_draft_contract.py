"""Add Smart Cut draft/session contract columns to existing databases.

Usage:
    python3 scripts/migrations/20260421_add_smart_cut_draft_contract.py
    DATABASE_URL=postgresql+psycopg://... python3 scripts/migrations/20260421_add_smart_cut_draft_contract.py
"""

from __future__ import annotations

from configs.database import build_engine, get_database_url, _apply_additive_smart_cut_schema


def main() -> None:
    database_url = get_database_url()
    engine = build_engine(database_url)
    _apply_additive_smart_cut_schema(engine)
    print(f"Applied additive Smart Cut draft contract schema updates to {database_url}")


if __name__ == "__main__":
    main()
