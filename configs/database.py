"""数据库配置 - SQLAlchemy 2.0 配置"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 默认数据库路径
DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "db" / "smart_cut.db"
DEFAULT_DB_URL = f"sqlite:///{DEFAULT_DB_PATH}"
REQUIRED_SCHEDULER_TABLES = (
    "scheduler_tasks",
    "smart_cut_devices",
)


def get_database_url() -> str:
    """获取默认业务数据库 URL。"""
    return os.getenv("DATABASE_URL", DEFAULT_DB_URL)


def get_scheduler_database_url(
    *,
    explicit_url: str | None = None,
    fallback_to_database_url: bool = True,
) -> str | None:
    """获取调度器数据库 URL。

    优先级:
    1. 显式传入
    2. SCHEDULER_DATABASE_URL
    3. DATABASE_URL（可选回退）
    """
    if explicit_url:
        return explicit_url

    scheduler_url = os.getenv("SCHEDULER_DATABASE_URL")
    if scheduler_url:
        return scheduler_url

    if fallback_to_database_url:
        return os.getenv("DATABASE_URL")

    return None


def build_engine(database_url: str, *, echo: bool | None = None) -> Engine:
    """按数据库类型创建 Engine。"""
    engine_kwargs: dict[str, object] = {}

    if database_url.startswith("sqlite:///"):
        db_path = database_url.replace("sqlite:///", "", 1)
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_recycle"] = 3600

    if echo is None:
        echo = os.getenv("SQL_ECHO", "false").lower() == "true"

    return create_engine(database_url, echo=echo, **engine_kwargs)


def create_session_factory(database_url: str) -> sessionmaker:
    """根据 URL 创建会话工厂。"""
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=build_engine(database_url),
    )


# 默认业务数据库引擎 / 会话工厂，保持向后兼容
DATABASE_URL = get_database_url()
engine = build_engine(DATABASE_URL)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# 声明式基类
Base = declarative_base()


def _apply_additive_smart_cut_schema(bind_engine: Engine) -> None:
    """Apply additive Smart Cut schema changes for existing deployments."""
    inspector = inspect(bind_engine)
    if not inspector.has_table("smart_cut_tasks"):
        return

    dialect = bind_engine.dialect.name
    column_names = {column["name"] for column in inspector.get_columns("smart_cut_tasks")}
    statements: list[str] = []

    if "task_title" not in column_names:
        if dialect == "postgresql":
            statements.append(
                "ALTER TABLE smart_cut_tasks ADD COLUMN IF NOT EXISTS task_title VARCHAR(128)"
            )
        else:
            statements.append("ALTER TABLE smart_cut_tasks ADD COLUMN task_title VARCHAR(128)")
    if "visible_in_task_center" not in column_names:
        if dialect == "postgresql":
            statements.append(
                "ALTER TABLE smart_cut_tasks ADD COLUMN IF NOT EXISTS visible_in_task_center BOOLEAN NOT NULL DEFAULT FALSE"
            )
        else:
            statements.append(
                "ALTER TABLE smart_cut_tasks ADD COLUMN visible_in_task_center BOOLEAN NOT NULL DEFAULT 0"
            )
    if "session_scope_id" not in column_names:
        if dialect == "postgresql":
            statements.append(
                "ALTER TABLE smart_cut_tasks ADD COLUMN IF NOT EXISTS session_scope_id VARCHAR(128)"
            )
        else:
            statements.append("ALTER TABLE smart_cut_tasks ADD COLUMN session_scope_id VARCHAR(128)")
    if "company_id" not in column_names:
        if dialect == "postgresql":
            statements.append(
                "ALTER TABLE smart_cut_tasks ADD COLUMN IF NOT EXISTS company_id INTEGER"
            )
        else:
            statements.append("ALTER TABLE smart_cut_tasks ADD COLUMN company_id INTEGER")

    true_literal = "TRUE" if dialect == "postgresql" else "1"
    false_literal = "FALSE" if dialect == "postgresql" else "0"
    visibility_backfill = text(
        f"""
        UPDATE smart_cut_tasks
        SET visible_in_task_center = CASE
            WHEN status IN ('finalizing', 'finalize_failed', 'success') THEN {true_literal}
            ELSE {false_literal}
        END
        """
    )

    with bind_engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
        if "visible_in_task_center" in column_names or any(
            "visible_in_task_center" in statement for statement in statements
        ):
            conn.execute(visibility_backfill)


def get_db():
    """获取默认业务数据库会话的依赖函数。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(*, bind_engine: Engine | None = None) -> None:
    """初始化数据库 - 创建所有表。"""
    # 延迟导入模型，避免循环导入
    from apps.models.task import SmartCutTask  # noqa: F401
    from apps.models.scheduler_task import SchedulerTask  # noqa: F401
    from apps.models.device import SmartCutDevice  # noqa: F401
    from apps.models.edit import SmartCutEdit  # noqa: F401

    target_engine = bind_engine or engine
    Base.metadata.create_all(bind=target_engine)
    _apply_additive_smart_cut_schema(target_engine)


def init_scheduler_db(database_url: str) -> Engine:
    """初始化调度器数据库并返回其 Engine。"""
    scheduler_engine = build_engine(database_url)
    init_db(bind_engine=scheduler_engine)
    return scheduler_engine


def check_database_connection(bind_engine: Engine) -> None:
    """验证数据库连接。"""
    with bind_engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def get_missing_tables(
    bind_engine: Engine,
    required_tables: Iterable[str],
) -> list[str]:
    """返回当前数据库里缺失的表。"""
    inspector = inspect(bind_engine)
    return [
        table_name
        for table_name in required_tables
        if not inspector.has_table(table_name)
    ]
