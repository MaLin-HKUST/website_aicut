"""Smart Cut API - 任务管理路由

F06: POST /api/smart-cut/tasks - 创建任务
F14: GET /api/smart-cut/tasks/{task_id} - 查询任务详情
F24: POST /api/smart-cut/tasks/{task_id}/abandon - 放弃任务
F25: Fake TOS 实现
F26: Cleanup 机制
"""

import asyncio
from datetime import datetime
from typing import Any, Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from configs.database import get_db
from apps.models.task import SmartCutTask, TaskStatus, CurrentStage
from apps.models.edit import SmartCutEdit
from apps.api.dependencies import get_tos_service
from apps.api.models.schemas import (
    TaskCreateRequest,
    TaskCreateData,
    TaskCreateResponse,
    TaskStatusData,
    TaskStatusResponse,
    PresignedUrlData,
    PresignedUrlResponse,
    TaskDetailResponse,
    TaskAbandonResponse,
    TaskNotFoundError,
    TaskCannotAbandonError,
)
from apps.services.tos_service import TOSService
from apps.services.cleanup_service import create_cleanup_service


router = APIRouter(
    prefix="/api/smart-cut/tasks",
    tags=["tasks"],
    responses={404: {"model": TaskNotFoundError, "description": "任务不存在"}}
)


# ============ F06: 创建任务 ============

@router.post(
    "",
    response_model=TaskCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建 Smart Cut 任务",
    description="""
    创建一个新的 Smart Cut 任务。
    
    任务创建后初始状态为 `waiting_upload`，用户需要：
    1. 调用获取上传 URL 接口上传视频和文案
    2. 确认上传完成后，任务状态会自动变为 `ready_analyze`
    3. 系统会自动开始分析处理
    
    **注意**: 当前版本 user_id 暂时使用 "anonymous"，后续版本将接入用户认证系统。
    """,
    responses={
        201: {"description": "任务创建成功"},
        500: {"description": "服务器内部错误"},
    },
)
async def create_task(
    request: TaskCreateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TaskCreateResponse:
    """创建新的 Smart Cut 任务
    
    Args:
        request: 创建任务请求，包含可选的 user_id
        db: 数据库会话
        
    Returns:
        TaskCreateResponse: 包含新创建任务的 ID、状态和创建时间
        
    Raises:
        HTTPException: 当数据库操作失败时抛出 500 错误
    """
    try:
        # 创建新任务
        task = SmartCutTask(
            user_id=request.user_id,
            status=TaskStatus.WAITING_UPLOAD,
            current_stage=CurrentStage.UPLOAD,
        )
        
        # 保存到数据库
        db.add(task)
        db.commit()
        db.refresh(task)
        
        # 构建响应
        return TaskCreateResponse(
            code=0,
            message="success",
            data=TaskCreateData(
                task_id=task.id,
                status=task.status.value,
                created_at=task.created_at,
            )
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(e)}"
        )


@router.get(
    "/{task_id}/status",
    response_model=TaskStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="查询任务状态",
    description="获取指定任务的详细状态和当前阶段信息",
    responses={
        200: {"description": "查询成功"},
        404: {"description": "任务不存在"},
    },
)
async def get_task_status(
    task_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> TaskStatusResponse:
    """查询任务状态
    
    Args:
        task_id: 任务 ID
        db: 数据库会话
        
    Returns:
        TaskStatusResponse: 任务详细信息
        
    Raises:
        HTTPException: 当任务不存在时抛出 404 错误
    """
    task = db.query(SmartCutTask).filter(SmartCutTask.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}"
        )
    
    return TaskStatusResponse(
        code=0,
        message="success",
        data=TaskStatusData(
            task_id=task.id,
            status=task.status.value,
            current_stage=task.current_stage.value,
            created_at=task.created_at,
            updated_at=task.updated_at,
            original_video_url=task.original_video_url,
            reference_text_url=task.reference_text_url,
            final_video_url=task.final_video_url,
        )
    )


@router.get(
    "/{task_id}/upload-url",
    response_model=PresignedUrlResponse,
    status_code=status.HTTP_200_OK,
    summary="获取视频上传 URL",
    description="获取用于上传原始视频的预签名 URL",
    responses={
        200: {"description": "获取成功"},
        404: {"description": "任务不存在"},
    },
)
async def get_video_upload_url(
    task_id: str,
    db: Annotated[Session, Depends(get_db)],
    tos: Annotated[TOSService, Depends(get_tos_service)],
) -> PresignedUrlResponse:
    """获取视频上传 URL
    
    Args:
        task_id: 任务 ID
        db: 数据库会话
        tos: TOS 服务实例
        
    Returns:
        PresignedUrlResponse: 预签名上传 URL
    """
    # 验证任务存在
    task = db.query(SmartCutTask).filter(SmartCutTask.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}"
        )
    
    # 生成上传 key
    key = f"tasks/{task_id}/original_video.mp4"
    
    # 生成预签名 URL
    result = tos.generate_upload_url(
        bucket="smart-cut-uploads",
        key=key,
        expires=3600,
    )
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate upload URL: {result.error}"
        )
    
    return PresignedUrlResponse(
        code=0,
        message="success",
        data=PresignedUrlData(
            url=result.data["url"],
            expires_at=result.metadata.get("expires_at", ""),
            key=key,
        )
    )


# ============ F14: 查询任务详情 ============

@router.get(
    "/{task_id}",
    response_model=TaskDetailResponse,
    summary="查询任务详情",
    description="获取指定任务的完整信息，包括基本信息、输入文件、各阶段产物等",
    responses={
        200: {"description": "查询成功", "model": TaskDetailResponse},
        404: {"description": "任务不存在", "model": TaskNotFoundError}
    }
)
async def get_task_detail(
    task_id: str,
    db: Session = Depends(get_db)
) -> TaskDetailResponse:
    """F14: 查询任务详情
    
    Args:
        task_id: 任务唯一标识
        db: 数据库会话
        
    Returns:
        TaskDetailResponse: 完整的任务详情
        
    Raises:
        HTTPException 404: 任务不存在
    """
    # 查询任务，同时加载关联的 edits 以获取当前编辑信息
    task = db.query(SmartCutTask).filter(SmartCutTask.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    # 获取当前编辑的脚本和 audio_b_url
    current_edited_script: dict[str, Any] | None = None
    audio_b_url: str | None = None
    
    if task.active_edit_id:
        edit = db.query(SmartCutEdit).filter(SmartCutEdit.id == task.active_edit_id).first()
        if edit:
            current_edited_script = edit.edited_script
            audio_b_url = edit.audio_b_url
    
    # 计算 groundtruth_saved 标记
    # 如果 groundtruth_url 不为空且 groundtruth_upload_status 为 completed，则认为已保存
    groundtruth_saved = bool(
        task.groundtruth_url and 
        task.groundtruth_upload_status == "completed"
    )
    
    # success 状态时返回 final_video_url，否则为 None
    final_video_url = task.final_video_url if task.status == TaskStatus.SUCCESS else None
    
    return TaskDetailResponse(
        # 基本信息
        id=task.id,
        user_id=task.user_id,
        status=task.status.value,
        current_stage=task.current_stage.value,
        created_at=task.created_at,
        updated_at=task.updated_at,
        
        # 输入
        original_video_url=task.original_video_url,
        reference_text_url=task.reference_text_url,
        
        # Analyze 产物
        analyze_script=task.analyze_script,
        asr_result_tos_key=task.asr_result_tos_key,
        
        # 当前 Edit
        active_edit_id=task.active_edit_id,
        current_edited_script=current_edited_script,
        audio_b_url=audio_b_url,
        
        # Finalize 产物
        final_video_url=final_video_url,
        groundtruth_url=task.groundtruth_url,
        groundtruth_saved=groundtruth_saved
    )


# ============ F24: 放弃任务 ============

@router.post(
    "/{task_id}/abandon",
    response_model=TaskAbandonResponse,
    summary="放弃任务",
    description="放弃指定任务。终态任务（success, abandoned, failed 等）不能放弃",
    responses={
        200: {"description": "放弃成功", "model": TaskAbandonResponse},
        400: {"description": "任务已处于终态，无法放弃", "model": TaskCannotAbandonError},
        404: {"description": "任务不存在", "model": TaskNotFoundError}
    }
)
async def abandon_task(
    task_id: str,
    db: Session = Depends(get_db)
) -> TaskAbandonResponse:
    """F24: 放弃任务
    
    校验任务状态，更新为 abandoned，并触发 workspace 清理 (F26)。
    
    Args:
        task_id: 任务唯一标识
        db: 数据库会话
        
    Returns:
        TaskAbandonResponse: 放弃确认信息
        
    Raises:
        HTTPException 404: 任务不存在
        HTTPException 400: 任务已处于终态，无法放弃
    """
    # 查询任务
    task = db.query(SmartCutTask).filter(SmartCutTask.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    # 校验任务状态 - 终态不能放弃
    if task.is_terminal():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"任务已处于终态 ({task.status.value})，无法放弃"
        )
    
    # 更新任务状态
    task.status = TaskStatus.ABANDONED
    task.current_stage = CurrentStage.COMPLETE
    task.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(task)
    
    # F26: 触发 workspace 清理 (异步)
    asyncio.create_task(cleanup_workspace_async(task))
    
    return TaskAbandonResponse(
        task_id=task.id,
        status=task.status.value,
        abandoned_at=task.updated_at
    )


async def cleanup_workspace_async(task: SmartCutTask) -> None:
    """异步清理 workspace (F26 实现)
    
    使用 CleanupService 清理放弃任务的资源。
    
    Args:
        task: SmartCutTask 对象
    """
    try:
        # 创建清理服务实例
        cleanup_service = create_cleanup_service()
        
        # 执行清理
        result = cleanup_service.cleanup_abandoned_task(task)
        
        # 记录清理结果
        print(f"[CLEANUP] Task {task.id} cleanup result: {result}")
        
    except Exception as e:
        # 清理失败不影响主流程，但应记录错误
        print(f"[CLEANUP ERROR] Failed to cleanup task {task.id}: {e}")
