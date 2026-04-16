"""Task Center API routes for 0415.

当前版本底层数据源为 Smart Cut 任务，但页面结构按统一任务中心输出。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from configs.database import get_db
from apps.api.models.schemas import TaskCenterTaskRead
from apps.api.routes.tasks import build_task_center_item
from apps.models.task import SmartCutTask


router = APIRouter(prefix="/api", tags=["task-center"])


@router.get(
    "/task-center/tasks",
    response_model=list[TaskCenterTaskRead],
    summary="普通用户任务中心列表",
)
async def list_user_task_center(
    db: Session = Depends(get_db),
    user_id: str | None = Query(default=None, description="用户 ID；为空时返回全部任务"),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[TaskCenterTaskRead]:
    stmt = select(SmartCutTask).order_by(desc(SmartCutTask.updated_at)).limit(limit)
    if user_id:
        stmt = stmt.where(SmartCutTask.user_id == user_id)
    tasks = list(db.execute(stmt).scalars().all())
    return [build_task_center_item(db, task, include_admin_fields=False) for task in tasks]


@router.get(
    "/admin/task-center/tasks",
    response_model=list[TaskCenterTaskRead],
    summary="Admin 任务中心列表",
)
async def list_admin_task_center(
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[TaskCenterTaskRead]:
    tasks = list(
        db.execute(select(SmartCutTask).order_by(desc(SmartCutTask.updated_at)).limit(limit)).scalars().all()
    )
    return [build_task_center_item(db, task, include_admin_fields=True) for task in tasks]
