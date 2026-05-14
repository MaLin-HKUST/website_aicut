"""Shared Smart Cut draft/session contract helpers."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException, Request, status


SESSION_SCOPE_COOKIE_NAME = "session_token"
SESSION_SCOPE_HEADER_NAME = "x-session-scope-id"
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
STATUS_DETAIL_WAITING_UPLOAD = "待上传素材"
STATUS_DETAIL_QUEUED = "排队中"
STATUS_DETAIL_ANALYZING = "正在分析"
STATUS_DETAIL_WAITING_USER = "待人工确认 / 试听"
STATUS_DETAIL_PREVIEWING = "正在生成试听"
STATUS_DETAIL_PREVIEW_FAILED = "试听失败"
STATUS_DETAIL_GENERATING_VIDEO = "正在生成视频"
STATUS_DETAIL_GENERATING_SUBTITLE = "正在生成字幕"
STATUS_DETAIL_ANALYZE_FAILED = "分析失败"
STATUS_DETAIL_FINALIZE_FAILED = "生成失败"
STATUS_DETAIL_SUCCESS = "已完成"
STATUS_DETAIL_ABANDONED = "已放弃"
STATUS_DETAIL_RESOURCE_WAIT = "等待服务器资源，系统会自动重试"
TASK_CENTER_VISIBLE_STATUSES = frozenset({
    "finalizing",
    "finalize_failed",
    "success",
})
_RESOURCE_ERROR_PATTERN = re.compile(
    r"no space|errno\s*28|enospc|硬盘|空间不足|资源不足",
    re.IGNORECASE,
)


def should_be_visible_in_task_center(task_status: str | None) -> bool:
    return bool(task_status and task_status in TASK_CENTER_VISIBLE_STATUSES)


def default_status_detail(task_status: str | None) -> str | None:
    mapping = {
        "waiting_upload": STATUS_DETAIL_WAITING_UPLOAD,
        "ready_analyze": STATUS_DETAIL_QUEUED,
        "analyzing": STATUS_DETAIL_ANALYZING,
        "waiting_user": STATUS_DETAIL_WAITING_USER,
        "previewing": STATUS_DETAIL_PREVIEWING,
        "preview_failed": STATUS_DETAIL_PREVIEW_FAILED,
        "finalizing": STATUS_DETAIL_GENERATING_VIDEO,
        "finalize_failed": STATUS_DETAIL_FINALIZE_FAILED,
        "success": STATUS_DETAIL_SUCCESS,
        "analyze_failed": STATUS_DETAIL_ANALYZE_FAILED,
        "abandoned": STATUS_DETAIL_ABANDONED,
    }
    if not task_status:
        return None
    return mapping.get(str(task_status))


def sanitize_user_error_message(message: str | None) -> str | None:
    if message is None:
        return None
    if _RESOURCE_ERROR_PATTERN.search(message):
        return STATUS_DETAIL_RESOURCE_WAIT
    return message


def build_smart_cut_task_title(now: datetime | None = None) -> str:
    local_now = (now or datetime.now(tz=SHANGHAI_TZ)).astimezone(SHANGHAI_TZ)
    return f"智能剪气口-{local_now.strftime('%Y%m%d-%H%M%S')}"


def resolve_session_scope_id(
    request: Request,
    explicit_scope_id: str | None = None,
    *,
    required: bool,
) -> str | None:
    if explicit_scope_id:
        normalized = explicit_scope_id.strip()
        if normalized:
            return normalized

    header_value = request.headers.get(SESSION_SCOPE_HEADER_NAME)
    if header_value:
        normalized = header_value.strip()
        if normalized:
            return normalized

    session_token = request.cookies.get(SESSION_SCOPE_COOKIE_NAME)
    if session_token:
        digest = hashlib.sha256(session_token.encode("utf-8")).hexdigest()
        return f"scs_{digest}"

    if required:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Session scope unavailable; current draft endpoints require "
                "a login session cookie or x-session-scope-id header"
            ),
        )
    return None
