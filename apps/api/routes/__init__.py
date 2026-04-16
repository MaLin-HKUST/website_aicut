"""API 路由包 - F06 实现

导出所有 API 路由供主应用注册
"""

from fastapi import APIRouter

from apps.api.routes.tasks import router as tasks_router
from apps.api.routes.stages import router as stages_router
from apps.api.routes.task_center import router as task_center_router
from apps.api.routes.upload import router as upload_router


# 主 API Router
api_router = APIRouter()

# 注册各模块路由
api_router.include_router(tasks_router)
api_router.include_router(stages_router)
api_router.include_router(task_center_router)
api_router.include_router(upload_router)


# 导出所有 router
__all__ = [
    "api_router",
    "tasks_router",
    "stages_router",
    "task_center_router",
    "upload_router",
]
