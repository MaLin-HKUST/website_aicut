"""API 依赖注入模块 - F06 实现

提供 FastAPI 依赖函数，用于：
- 获取数据库会话
- 获取 TOS 服务实例
"""

import os
from typing import Generator

from sqlalchemy.orm import Session

from configs.database import SessionLocal
from apps.services.tos_service import TOSService


def get_db() -> Generator[Session, None, None]:
    """获取数据库会话
    
    FastAPI 依赖函数，用于在请求处理过程中获取数据库会话。
    会话会在请求结束后自动关闭。
    
    Yields:
        Session: SQLAlchemy 数据库会话
        
    Example:
        ```python
        @router.post("/tasks")
        async def create_task(db: Annotated[Session, Depends(get_db)]):
            task = SmartCutTask(...)
            db.add(task)
            db.commit()
            return task
        ```
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# TOS 服务单例实例（延迟初始化）
_tos_service_instance: TOSService | None = None


def get_tos_service() -> TOSService:
    """获取 TOS 服务实例
    
    FastAPI 依赖函数，返回 TOS 服务单例实例。
    根据环境变量 TOS_MODE 决定使用 Fake 模式还是真实模式。
    
    环境变量:
        TOS_MODE: 设置为 "fake" 使用本地文件系统模拟 TOS（默认）
        FAKE_TOS_BASE_PATH: Fake 模式下的存储路径（默认: /tmp/fake_tos）
        TOS_ENDPOINT: 真实 TOS 端点 URL
        TOS_REGION: 真实 TOS 区域（默认: cn-beijing）
        TOS_ACCESS_KEY: 真实 TOS 访问密钥
        TOS_SECRET_KEY: 真实 TOS 密钥
    
    Returns:
        TOSService: TOS 服务实例
        
    Example:
        ```python
        @router.get("/upload-url")
        async def get_upload_url(tos: Annotated[TOSService, Depends(get_tos_service)]):
            result = tos.generate_upload_url(...)
            return result
        ```
    """
    global _tos_service_instance
    
    if _tos_service_instance is None:
        # 根据环境变量选择模式
        use_fake = os.getenv("TOS_MODE", "fake").lower() == "fake"
        
        if use_fake:
            fake_base_path = os.getenv("FAKE_TOS_BASE_PATH", "/tmp/fake_tos")
            _tos_service_instance = TOSService(
                use_fake=True,
                fake_base_path=fake_base_path,
            )
        else:
            _tos_service_instance = TOSService(
                use_fake=False,
                endpoint=os.getenv("TOS_ENDPOINT"),
                region=os.getenv("TOS_REGION", "cn-beijing"),
                access_key=os.getenv("TOS_ACCESS_KEY"),
                secret_key=os.getenv("TOS_SECRET_KEY"),
            )
    
    return _tos_service_instance


def reset_tos_service() -> None:
    """重置 TOS 服务实例
    
    主要用于测试场景，允许重新初始化 TOS 服务。
    """
    global _tos_service_instance
    _tos_service_instance = None
