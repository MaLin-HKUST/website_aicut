"""
Worker 身份验证模块

用于验证回调接口的调用方是否为合法的 Worker
"""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app import models


class WorkerTokenError(ValueError):
    """Worker Token 错误"""
    pass


def generate_worker_token() -> str:
    """生成新的 Worker Token"""
    return f"wkt_{secrets.token_urlsafe(32)}"


def hash_worker_token(token: str) -> str:
    """对 Worker Token 进行哈希（简化版，生产环境应使用更安全的哈希）"""
    # 使用简单的哈希，实际生产环境应使用类似 bcrypt 的算法
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()


def verify_worker_token(token: str, hashed: str) -> bool:
    """验证 Worker Token"""
    return hash_worker_token(token) == hashed


def get_worker_by_id(db: DbSession, worker_id: str) -> models.SchedulerWorker | None:
    """通过 ID 获取 Worker"""
    return db.scalar(select(models.SchedulerWorker).where(models.SchedulerWorker.worker_id == worker_id))


def authenticate_worker_callback(
    db: DbSession,
    worker_id: str,
    token: str,
    scheduler_task_id: str,
) -> models.SchedulerWorker:
    """
    验证 Worker 回调的身份

    验证流程：
        1. 检查 Worker 是否存在
        2. 验证 Worker Token（与注册时的 hashed_token 匹配）
        3. 检查 Worker 当前任务是否匹配
        4. 检查 Worker 状态（应该是 running 或 post）
        5. 检查心跳是否超时（5分钟）

    Args:
        db: 数据库会话
        worker_id: Worker ID
        token: Worker Token（明文，从 X-Worker-Token header 获取）
        scheduler_task_id: 调度任务 ID（用于验证 Worker 确实被分配了该任务）

    Returns:
        验证通过的 Worker 对象

    Raises:
        WorkerTokenError: 验证失败
    """
    # 1. 检查 Worker 是否存在
    worker = get_worker_by_id(db, worker_id)
    if worker is None:
        raise WorkerTokenError(f"Worker {worker_id} not found")

    # 2. 【新增】验证 Worker Token
    if not token:
        raise WorkerTokenError(f"Worker token is required")
    
    if not worker.hashed_token:
        raise WorkerTokenError(f"Worker {worker_id} has no registered token")
    
    if not verify_worker_token(token, worker.hashed_token):
        raise WorkerTokenError(f"Invalid worker token for {worker_id}")

    # 3. 检查 Worker 当前任务是否匹配
    if worker.current_task_id != scheduler_task_id:
        raise WorkerTokenError(
            f"Worker {worker_id} is not assigned to task {scheduler_task_id}. "
            f"Current task: {worker.current_task_id}"
        )

    # 4. 检查 Worker 状态（应该是 running 或 post）
    if worker.status not in ("running", "post", "error"):
        raise WorkerTokenError(
            f"Worker {worker_id} is not in active state. Current status: {worker.status}"
        )

    # 5. 检查心跳是否超时（5分钟）
    from app.scheduler_domain import ensure_utc
    from app.scheduler_service import utcnow
    now = utcnow()
    heartbeat_at = ensure_utc(worker.heartbeat_at) if worker.heartbeat_at else None
    if heartbeat_at is None:
        raise WorkerTokenError(f"Worker {worker_id} has no heartbeat recorded")
    heartbeat_timeout = now - timedelta(minutes=5)
    if heartbeat_at < heartbeat_timeout:
        raise WorkerTokenError(
            f"Worker {worker_id} heartbeat expired. Last heartbeat: {heartbeat_at}"
        )

    return worker


def verify_callback_matches_scheduler_task(
    db: DbSession,
    smart_cut_task: models.SmartCutTask,
    scheduler_task_id: str,
) -> models.SchedulerTask:
    """
    验证回调对应的调度任务是否匹配当前业务任务

    Args:
        db: 数据库会话
        smart_cut_task: Smart Cut 业务任务
        scheduler_task_id: 回调中提供的调度任务 ID

    Returns:
        验证通过的调度任务

    Raises:
        WorkerTokenError: 验证失败
    """
    from sqlalchemy import select

    # 1. 检查 scheduler_task_id 是否匹配 last_scheduler_task_id
    if smart_cut_task.last_scheduler_task_id != scheduler_task_id:
        raise WorkerTokenError(
            f"Scheduler task mismatch. Expected: {smart_cut_task.last_scheduler_task_id}, "
            f"got: {scheduler_task_id}"
        )

    # 2. 查询调度任务
    scheduler_task = db.scalar(
        select(models.SchedulerTask).where(models.SchedulerTask.task_id == scheduler_task_id)
    )
    if scheduler_task is None:
        raise WorkerTokenError(f"Scheduler task {scheduler_task_id} not found")

    # 3. 检查调度任务状态（应该是 assigned 或 running）
    if scheduler_task.status not in ("assigned", "running"):
        raise WorkerTokenError(
            f"Scheduler task {scheduler_task_id} is not active. Status: {scheduler_task.status}"
        )

    return scheduler_task
