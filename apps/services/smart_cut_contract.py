"""Shared Smart Cut draft/session contract helpers."""

from __future__ import annotations

import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException, Request, status


SESSION_SCOPE_COOKIE_NAME = "session_token"
SESSION_SCOPE_HEADER_NAME = "x-session-scope-id"
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
TASK_CENTER_VISIBLE_STATUSES = frozenset({
    "finalizing",
    "finalize_failed",
    "success",
})


def should_be_visible_in_task_center(task_status: str | None) -> bool:
    return bool(task_status and task_status in TASK_CENTER_VISIBLE_STATUSES)


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
