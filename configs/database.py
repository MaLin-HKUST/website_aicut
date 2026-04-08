"""数据库配置 - SQLAlchemy 2.0 配置"""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 默认数据库路径
DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "db" / "smart_cut.db"
DEFAULT_DB_URL = f"sqlite:///{DEFAULT_DB_PATH}"

# 从环境变量读取数据库URL，或使用默认值
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

# 确保数据库目录存在
if DATABASE_URL.startswith("sqlite:///"):
    db_path = DATABASE_URL.replace("sqlite:///", "")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

# 创建引擎 - SQLAlchemy 2.0 语法
# connect_args 仅对 SQLite 需要
engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    **engine_kwargs
)

# 会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# 声明式基类
Base = declarative_base()


def get_db():
    """获取数据库会话的依赖函数"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库 - 创建所有表"""
    # 延迟导入模型，避免循环导入
    from apps.models.task import SmartCutTask  # noqa: F401
    from apps.models.scheduler_task import SchedulerTask  # noqa: F401
    from apps.models.device import SmartCutDevice  # noqa: F401
    Base.metadata.create_all(bind=engine)
