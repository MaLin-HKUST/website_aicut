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
from apps.models.scheduler_task import SchedulerTask, SchedulerTaskStatus
from apps.models.task import SmartCutTask


def _queue_positions(db: Session) -> dict[str, int]:
    pending_tasks = list(
        db.execute(
            select(SchedulerTask)
            .where(SchedulerTask.status == SchedulerTaskStatus.PENDING)
            .order_by(SchedulerTask.created_at.asc())
        ).scalars().all()
    )
    positions: dict[str, int] = {}
    for index, scheduler_task in enumerate(pending_tasks, start=1):
        positions.setdefault(scheduler_task.business_task_id, index)
    return positions


router = APIRouter(prefix="/api", tags=["task-center"])


def _apply_queue_positions(items: list[TaskCenterTaskRead]) -> list[TaskCenterTaskRead]:
    queued_items = sorted(
        [item for item in items if item.status == "queued"],
        key=lambda item: item.created_at,
    )
    positions = {item.id: index for index, item in enumerate(queued_items, start=1)}
    for item in items:
        if item.status == "queued":
            item.queue_position = positions.get(item.id)
    return items


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
    stmt = (
        select(SmartCutTask)
        .where(SmartCutTask.visible_in_task_center.is_(True))
        .order_by(desc(SmartCutTask.updated_at))
        .limit(limit)
    )
    if user_id:
        stmt = stmt.where(SmartCutTask.user_id == user_id)
    tasks = list(db.execute(stmt).scalars().all())
    queue_positions = _queue_positions(db)
    items = [
        build_task_center_item(
            db,
            task,
            include_admin_fields=False,
            queue_position=queue_positions.get(task.id),
        )
        for task in tasks
    ]
    return _apply_queue_positions(items)


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
        db.execute(
            select(SmartCutTask)
            .where(SmartCutTask.visible_in_task_center.is_(True))
            .order_by(desc(SmartCutTask.updated_at))
            .limit(limit)
        ).scalars().all()
    )
    queue_positions = _queue_positions(db)
    items = [
        build_task_center_item(
            db,
            task,
            include_admin_fields=True,
            queue_position=queue_positions.get(task.id),
        )
        for task in tasks
    ]
    return _apply_queue_positions(items)
