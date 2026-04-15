from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from app import models
from app.security import hash_password


def get_session(db: DbSession, token: str) -> models.Session | None:
    """通过 token 获取会话."""
    return db.scalar(select(models.Session).where(models.Session.token == token))


def create_session(db: DbSession, token: str, user_id: int) -> models.Session:
    """创建新会话."""
    session = models.Session(token=token, user_id=user_id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_user_by_username(db: DbSession, username: str) -> models.User | None:
    return db.scalar(select(models.User).where(models.User.username == username))


def create_user(
    db: DbSession, username: str, password: str, role: str = "user", company_id: int | None = None
) -> models.User:
    user = models.User(
        username=username,
        password_hash=hash_password(password),
        password_plaintext=password,
        role=role,
        company_id=company_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(db: DbSession) -> list[models.User]:
    return list(db.scalars(select(models.User).order_by(models.User.created_at.desc())))


# ========== Company ==========


def create_company(db: DbSession, name: str) -> models.Company:
    company = models.Company(name=name)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def list_companies(db: DbSession) -> list[models.Company]:
    return list(db.scalars(select(models.Company).order_by(models.Company.created_at.desc())))


def get_company_by_name(db: DbSession, name: str) -> models.Company | None:
    return db.scalar(select(models.Company).where(models.Company.name == name))


# ========== Material ==========


def create_material(
    db: DbSession, name: str, company_id: int, remark: str | None = None
) -> models.Material:
    material = models.Material(name=name, company_id=company_id, remark=remark)
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def list_materials(db: DbSession) -> list[models.Material]:
    return list(
        db.scalars(
            select(models.Material)
            .order_by(models.Material.created_at.desc())
        )
    )


# ========== User Usage Monthly ==========


def set_user_usage_limit(
    db: DbSession, user_id: int, year_month: str, limit: int | None
) -> models.UserUsageMonthly:
    """设置用户某月限额（初始化或更新）."""
    usage = db.scalar(
        select(models.UserUsageMonthly).where(
            models.UserUsageMonthly.user_id == user_id,
            models.UserUsageMonthly.year_month == year_month,
        )
    )
    
    if usage is None:
        usage = models.UserUsageMonthly(
            user_id=user_id,
            year_month=year_month,
            credits_used=0,
            credits_limit=limit,
        )
        db.add(usage)
    else:
        usage.credits_limit = limit
    
    db.commit()
    db.refresh(usage)
    return usage


def list_user_usage(db: DbSession, user_id: int) -> list[models.UserUsageMonthly]:
    """获取用户所有月份的消耗记录."""
    return list(
        db.scalars(
            select(models.UserUsageMonthly)
            .where(models.UserUsageMonthly.user_id == user_id)
            .order_by(models.UserUsageMonthly.year_month.desc())
        )
    )


def add_user_usage(db: DbSession, user_id: int, credits: int) -> models.UserUsageMonthly:
    """增加用户本月消耗（用于生成TTS后更新）."""
    from datetime import datetime
    year_month = datetime.now().strftime("%Y-%m")
    
    usage = db.scalar(
        select(models.UserUsageMonthly).where(
            models.UserUsageMonthly.user_id == user_id,
            models.UserUsageMonthly.year_month == year_month,
        )
    )
    
    if usage is None:
        usage = models.UserUsageMonthly(
            user_id=user_id,
            year_month=year_month,
            credits_used=credits,
        )
        db.add(usage)
    else:
        usage.credits_used += credits
    
    db.commit()
    db.refresh(usage)
    return usage


def get_user_usage(db: DbSession, user_id: int) -> models.UserUsageMonthly | None:
    """获取用户本月消耗记录."""
    from datetime import datetime
    year_month = datetime.now().strftime("%Y-%m")
    
    return db.scalar(
        select(models.UserUsageMonthly).where(
            models.UserUsageMonthly.user_id == user_id,
            models.UserUsageMonthly.year_month == year_month,
        )
    )


def get_or_create_user_usage(
    db: DbSession, user_id: int, year_month: str
) -> models.UserUsageMonthly:
    """获取或创建用户某月消耗记录."""
    usage = db.scalar(
        select(models.UserUsageMonthly).where(
            models.UserUsageMonthly.user_id == user_id,
            models.UserUsageMonthly.year_month == year_month,
        )
    )
    
    if usage is None:
        usage = models.UserUsageMonthly(
            user_id=user_id,
            year_month=year_month,
            credits_used=0,
        )
        db.add(usage)
        db.commit()
        db.refresh(usage)
    
    return usage


def update_user_usage_limit(
    db: DbSession, user_id: int, limit: int | None
) -> models.UserUsageMonthly | None:
    """管理员更新用户月度限额."""
    from datetime import datetime
    year_month = datetime.now().strftime("%Y-%m")
    
    usage = db.scalar(
        select(models.UserUsageMonthly).where(
            models.UserUsageMonthly.user_id == user_id,
            models.UserUsageMonthly.year_month == year_month,
        )
    )
    
    if usage is None:
        # 如果没有记录，创建一个
        usage = models.UserUsageMonthly(
            user_id=user_id,
            year_month=year_month,
            credits_used=0,
            credits_limit=limit,
        )
        db.add(usage)
    else:
        usage.credits_limit = limit
    
    db.commit()
    db.refresh(usage)
    return usage


def adjust_user_usage_credits(
    db: DbSession, user_id: int, delta: int
) -> models.UserUsageMonthly | None:
    """管理员手动调整用户已消耗额度（正数为增加，负数为减少）."""
    year_month = datetime.now().strftime("%Y-%m")
    
    usage = db.scalar(
        select(models.UserUsageMonthly).where(
            models.UserUsageMonthly.user_id == user_id,
            models.UserUsageMonthly.year_month == year_month,
        )
    )
    
    if usage is None:
        if delta < 0:
            return None  # 不能减少不存在的记录
        # 创建新记录
        usage = models.UserUsageMonthly(
            user_id=user_id,
            year_month=year_month,
            credits_used=delta,
        )
        db.add(usage)
    else:
        new_credits = usage.credits_used + delta
        if new_credits < 0:
            new_credits = 0  # 不能小于0
        usage.credits_used = new_credits
    
    db.commit()
    db.refresh(usage)
    return usage


# ============================================
# Smart Cut CRUD (F03)
# ============================================


def create_smart_cut_task(db: DbSession, task_id: str, user_id: int) -> models.SmartCutTask:
    """创建 Smart Cut 业务任务"""
    task = models.SmartCutTask(
        id=task_id,
        user_id=user_id,
        status=models.SmartCutTaskStatus.WAITING_UPLOAD,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_smart_cut_task(db: DbSession, task_id: str) -> models.SmartCutTask | None:
    """获取 Smart Cut 任务"""
    return db.scalar(select(models.SmartCutTask).where(models.SmartCutTask.id == task_id))


def get_smart_cut_task_with_edits(db: DbSession, task_id: str) -> models.SmartCutTask | None:
    """获取 Smart Cut 任务及其 edits 历史"""
    return db.scalar(
        select(models.SmartCutTask)
        .where(models.SmartCutTask.id == task_id)
    )


def list_smart_cut_tasks_by_user(db: DbSession, user_id: int) -> list[models.SmartCutTask]:
    """获取用户的所有 Smart Cut 任务"""
    return list(
        db.scalars(
            select(models.SmartCutTask)
            .where(models.SmartCutTask.user_id == user_id)
            .order_by(models.SmartCutTask.created_at.desc())
        )
    )


def update_smart_cut_task_prepared_keys(
    db: DbSession,
    task_id: str,
    video_key: str,
    text_key: str,
) -> models.SmartCutTask:
    """记录 upload-prepare 阶段发出的目标 key"""
    task = get_smart_cut_task(db, task_id)
    if task is None:
        raise ValueError(f"Task {task_id} not found")
    
    task.prepared_video_key = video_key
    task.prepared_text_key = text_key
    task.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(task)
    return task


def update_smart_cut_task_input_keys(
    db: DbSession,
    task_id: str,
    video_key: str,
    text_key: str,
) -> models.SmartCutTask:
    """更新输入文件 TOS key 并推进状态到 ready_analyze"""
    task = get_smart_cut_task(db, task_id)
    if task is None:
        raise ValueError(f"Task {task_id} not found")
    
    task.original_video_tos_key = video_key
    task.reference_text_tos_key = text_key
    task.status = models.SmartCutTaskStatus.READY_ANALYZE
    task.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(task)
    return task


def create_smart_cut_edit(
    db: DbSession,
    edit_id: str,
    task_id: str,
    edited_script: str,
    commit: bool = True,
) -> models.SmartCutEdit:
    """创建 Smart Cut Edit 记录"""
    edit = models.SmartCutEdit(
        id=edit_id,
        task_id=task_id,
        edited_script=edited_script,
        status="pending",
    )
    db.add(edit)
    if commit:
        db.commit()
        db.refresh(edit)
    return edit


def create_smart_cut_edit_no_commit(
    db: DbSession,
    edit_id: str,
    task_id: str,
    edited_script: str,
) -> models.SmartCutEdit:
    """创建 Smart Cut Edit 记录（不提交，用于事务包裹）"""
    return create_smart_cut_edit(db, edit_id, task_id, edited_script, commit=False)


def get_smart_cut_edit(db: DbSession, edit_id: str) -> models.SmartCutEdit | None:
    """获取 Smart Cut Edit"""
    return db.scalar(select(models.SmartCutEdit).where(models.SmartCutEdit.id == edit_id))


def get_last_successful_edit(db: DbSession, task_id: str) -> models.SmartCutEdit | None:
    """获取任务最后一次成功的 edit"""
    return db.scalar(
        select(models.SmartCutEdit)
        .where(
            models.SmartCutEdit.task_id == task_id,
            models.SmartCutEdit.status == "success",
        )
        .order_by(models.SmartCutEdit.created_at.desc())
    )


def list_smart_cut_edits_by_task(db: DbSession, task_id: str) -> list[models.SmartCutEdit]:
    """获取任务的所有 edit 记录，按时间倒序"""
    return list(
        db.scalars(
            select(models.SmartCutEdit)
            .where(models.SmartCutEdit.task_id == task_id)
            .order_by(models.SmartCutEdit.created_at.desc())
        )
    )


def update_smart_cut_edit_status(
    db: DbSession,
    edit_id: str,
    status: str,
    audio_b_tos_key: str | None = None,
    edited_delay_cuts_tos_key: str | None = None,
    pause_cuts_on_original_tos_key: str | None = None,
    error_message: str | None = None,
    commit: bool = True,
) -> models.SmartCutEdit:
    """更新 Edit 状态和产物"""
    from datetime import datetime, timezone
    
    edit = get_smart_cut_edit(db, edit_id)
    if edit is None:
        raise ValueError(f"Edit {edit_id} not found")
    
    edit.status = status
    if audio_b_tos_key is not None:
        edit.audio_b_tos_key = audio_b_tos_key
    if edited_delay_cuts_tos_key is not None:
        edit.edited_delay_cuts_tos_key = edited_delay_cuts_tos_key
    if pause_cuts_on_original_tos_key is not None:
        edit.pause_cuts_on_original_tos_key = pause_cuts_on_original_tos_key
    if error_message is not None:
        edit.error_message = error_message
    
    edit.updated_at = datetime.now(timezone.utc)
    if commit:
        db.commit()
        db.refresh(edit)
    return edit


def update_smart_cut_edit_status_no_commit(
    db: DbSession,
    edit_id: str,
    status: str,
    audio_b_tos_key: str | None = None,
    edited_delay_cuts_tos_key: str | None = None,
    pause_cuts_on_original_tos_key: str | None = None,
    error_message: str | None = None,
) -> models.SmartCutEdit:
    """更新 Edit 状态和产物（不提交，用于事务包裹）"""
    return update_smart_cut_edit_status(
        db, edit_id, status,
        audio_b_tos_key, edited_delay_cuts_tos_key,
        pause_cuts_on_original_tos_key, error_message,
        commit=False
    )


def delete_session(db: DbSession, token: str) -> None:
    """删除会话（之前遗漏的）."""
    session = db.scalar(select(models.Session).where(models.Session.token == token))
    if session:
        db.delete(session)
        db.commit()


# ============================================
# Admin Management CRUD
# ============================================

# --- Company Admin CRUD ---


def admin_list_companies(db: DbSession) -> list[models.Company]:
    """获取所有企业列表"""
    return list(db.scalars(select(models.Company).order_by(models.Company.created_at.desc())))


def admin_get_company(db: DbSession, company_id: int) -> models.Company | None:
    """获取企业详情"""
    return db.get(models.Company, company_id)


def admin_create_company(db: DbSession, **kwargs) -> models.Company:
    """创建企业"""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    company = models.Company(
        name=kwargs["company_name"],
        monthly_video_quota=kwargs.get("monthly_video_quota", 0),
        monthly_video_remaining=kwargs.get("monthly_video_remaining", 0),
        billing_cycle_start_date=kwargs.get("billing_cycle_start_date", today),
        tts_enabled=kwargs.get("tts_enabled", False),
        status=kwargs.get("status", "active"),
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def admin_update_company(db: DbSession, company: models.Company, **kwargs) -> models.Company:
    """更新企业"""
    for key, value in kwargs.items():
        if value is not None and hasattr(company, key):
            setattr(company, key, value)
    db.commit()
    db.refresh(company)
    return company


def admin_delete_company(db: DbSession, company: models.Company) -> None:
    """删除企业"""
    db.delete(company)
    db.commit()


# --- User Admin CRUD ---


def admin_list_users(db: DbSession) -> list[models.User]:
    """获取所有用户列表"""
    return list(db.scalars(select(models.User).order_by(models.User.created_at.desc())))


def admin_get_user(db: DbSession, user_id: int) -> models.User | None:
    """获取用户详情"""
    return db.get(models.User, user_id)


def admin_create_user(db: DbSession, **kwargs) -> models.User:
    """创建用户"""
    user = models.User(
        username=kwargs["login_account"],
        password_hash=hash_password(kwargs["password"]),
        password_plaintext=kwargs["password"],
        role=kwargs.get("role", "user"),
        company_id=kwargs["company_id"],
        user_name=kwargs.get("user_name"),
        status=kwargs.get("status", "active"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def admin_update_user(db: DbSession, user: models.User, **kwargs) -> models.User:
    """更新用户"""
    if "login_account" in kwargs and kwargs["login_account"] is not None:
        user.username = kwargs["login_account"]
    if "password" in kwargs and kwargs["password"]:
        user.password_hash = hash_password(kwargs["password"])
        user.password_plaintext = kwargs["password"]
    if "user_name" in kwargs:
        user.user_name = kwargs["user_name"]
    if "company_id" in kwargs and kwargs["company_id"] is not None:
        user.company_id = kwargs["company_id"]
    if "role" in kwargs and kwargs["role"] is not None:
        user.role = kwargs["role"]
    if "status" in kwargs and kwargs["status"] is not None:
        user.status = kwargs["status"]
    db.commit()
    db.refresh(user)
    return user


def admin_delete_user(db: DbSession, user: models.User) -> None:
    """删除用户"""
    db.delete(user)
    db.commit()


# --- AssetLibrary CRUD ---


def admin_list_libraries(db: DbSession) -> list[models.AssetLibrary]:
    """获取所有素材库列表"""
    return list(db.scalars(select(models.AssetLibrary).order_by(models.AssetLibrary.created_at.desc())))


def admin_get_library(db: DbSession, library_id: int) -> models.AssetLibrary | None:
    """获取素材库详情"""
    return db.get(models.AssetLibrary, library_id)


def admin_create_library(db: DbSession, **kwargs) -> models.AssetLibrary:
    """创建素材库"""
    library = models.AssetLibrary(
        company_id=kwargs["company_id"],
        library_name=kwargs["library_name"],
        root_path=kwargs["root_path"],
        config_path=kwargs["config_path"],
        description=kwargs.get("description"),
        status=kwargs.get("status", "active"),
    )
    db.add(library)
    db.commit()
    db.refresh(library)
    # 关联更新 company.asset_library_id
    company = db.get(models.Company, kwargs["company_id"])
    if company:
        company.asset_library_id = library.id
        db.commit()
    return library


def admin_update_library(db: DbSession, library: models.AssetLibrary, **kwargs) -> models.AssetLibrary:
    """更新素材库"""
    for key, value in kwargs.items():
        if value is not None and hasattr(library, key):
            setattr(library, key, value)
    db.commit()
    db.refresh(library)
    return library


def admin_delete_library(db: DbSession, library: models.AssetLibrary) -> None:
    """删除素材库"""
    # 清除 company 的关联
    company = db.scalar(select(models.Company).where(models.Company.asset_library_id == library.id))
    if company:
        company.asset_library_id = None
    db.delete(library)
    db.commit()


# --- TagGroup CRUD ---


def admin_list_tag_groups(db: DbSession, library_id: int) -> list[models.AssetLibraryTagGroup]:
    """获取素材库下的所有标签组"""
    return list(
        db.scalars(
            select(models.AssetLibraryTagGroup)
            .where(models.AssetLibraryTagGroup.asset_library_id == library_id)
            .order_by(models.AssetLibraryTagGroup.group_order)
        )
    )


def admin_list_all_tag_groups(db: DbSession) -> list[models.AssetLibraryTagGroup]:
    """获取所有标签组."""
    return list(
        db.scalars(
            select(models.AssetLibraryTagGroup)
            .order_by(models.AssetLibraryTagGroup.asset_library_id, models.AssetLibraryTagGroup.group_order)
        )
    )


def admin_get_tag_group(db: DbSession, tag_group_id: int) -> models.AssetLibraryTagGroup | None:
    """获取标签组详情"""
    return db.get(models.AssetLibraryTagGroup, tag_group_id)


def admin_create_tag_group(db: DbSession, **kwargs) -> models.AssetLibraryTagGroup:
    """创建标签组"""
    tag_group = models.AssetLibraryTagGroup(
        asset_library_id=kwargs["asset_library_id"],
        group_key=kwargs["group_key"],
        group_name=kwargs["group_name"],
        allow_multi_select=kwargs.get("allow_multi_select", True),
        allow_select_all=kwargs.get("allow_select_all", True),
        status=kwargs.get("status", "active"),
    )
    db.add(tag_group)
    db.commit()
    db.refresh(tag_group)
    return tag_group


def admin_update_tag_group(
    db: DbSession, tag_group: models.AssetLibraryTagGroup, **kwargs
) -> models.AssetLibraryTagGroup:
    """更新标签组"""
    for key, value in kwargs.items():
        if value is not None and hasattr(tag_group, key):
            setattr(tag_group, key, value)
    db.commit()
    db.refresh(tag_group)
    return tag_group


def admin_delete_tag_group(db: DbSession, tag_group: models.AssetLibraryTagGroup) -> None:
    """删除标签组"""
    db.delete(tag_group)
    db.commit()


# --- Tag CRUD ---


def admin_list_tags(db: DbSession, tag_group_id: int) -> list[models.AssetLibraryTag]:
    """获取标签组下的所有标签"""
    return list(
        db.scalars(
            select(models.AssetLibraryTag)
            .where(models.AssetLibraryTag.tag_group_id == tag_group_id)
            .order_by(models.AssetLibraryTag.tag_order)
        )
    )


def admin_list_tags_by_library(db: DbSession, library_id: int) -> list[models.AssetLibraryTag]:
    """获取素材库下的所有标签"""
    return list(
        db.scalars(
            select(models.AssetLibraryTag)
            .where(models.AssetLibraryTag.asset_library_id == library_id)
            .order_by(models.AssetLibraryTag.tag_order)
        )
    )


def admin_list_all_tags(db: DbSession) -> list[models.AssetLibraryTag]:
    """获取所有标签."""
    return list(
        db.scalars(
            select(models.AssetLibraryTag)
            .order_by(models.AssetLibraryTag.asset_library_id, models.AssetLibraryTag.tag_group_id, models.AssetLibraryTag.tag_order)
        )
    )


def admin_get_tag(db: DbSession, tag_id: int) -> models.AssetLibraryTag | None:
    """获取标签详情"""
    return db.get(models.AssetLibraryTag, tag_id)


def admin_create_tag(db: DbSession, **kwargs) -> models.AssetLibraryTag:
    """创建标签"""
    tag = models.AssetLibraryTag(
        asset_library_id=kwargs["asset_library_id"],
        tag_group_id=kwargs["tag_group_id"],
        tag_key=kwargs["tag_key"],
        tag_name=kwargs["tag_name"],
        filter_condition=kwargs["filter_condition"],
        is_default_selected=kwargs.get("is_default_selected", False),
        status=kwargs.get("status", "active"),
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def admin_update_tag(db: DbSession, tag: models.AssetLibraryTag, **kwargs) -> models.AssetLibraryTag:
    """更新标签"""
    for key, value in kwargs.items():
        if value is not None and hasattr(tag, key):
            setattr(tag, key, value)
    db.commit()
    db.refresh(tag)
    return tag


def admin_delete_tag(db: DbSession, tag: models.AssetLibraryTag) -> None:
    """删除标签"""
    db.delete(tag)
    db.commit()


# --- CustomGroup CRUD ---


def admin_list_custom_groups(db: DbSession) -> list[models.UserCustomTagGroup]:
    """获取所有自定义标签组"""
    return list(
        db.scalars(select(models.UserCustomTagGroup).order_by(models.UserCustomTagGroup.created_at.desc()))
    )


def admin_get_custom_group(db: DbSession, group_id: int) -> models.UserCustomTagGroup | None:
    """获取自定义标签组详情"""
    return db.get(models.UserCustomTagGroup, group_id)


def admin_create_custom_group(db: DbSession, tag_ids: list[int], **kwargs) -> models.UserCustomTagGroup:
    """创建自定义标签组"""
    group = models.UserCustomTagGroup(
        company_id=kwargs["company_id"],
        user_id=kwargs["user_id"],
        asset_library_id=kwargs["asset_library_id"],
        group_name=kwargs["group_name"],
        description=kwargs.get("description"),
        status=kwargs.get("status", "active"),
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    # 创建标签关联
    for tag_id in tag_ids:
        item = models.UserCustomTagGroupItem(custom_tag_group_id=group.id, tag_id=tag_id)
        db.add(item)
    db.commit()
    return group


def admin_update_custom_group(
    db: DbSession,
    group: models.UserCustomTagGroup,
    tag_ids: list[int] | None,
    **kwargs,
) -> models.UserCustomTagGroup:
    """更新自定义标签组"""
    for key, value in kwargs.items():
        if value is not None and hasattr(group, key):
            setattr(group, key, value)
    # 更新标签关联
    if tag_ids is not None:
        # 删除旧关联
        db.query(models.UserCustomTagGroupItem).filter(
            models.UserCustomTagGroupItem.custom_tag_group_id == group.id
        ).delete(synchronize_session=False)
        # 创建新关联
        for tag_id in tag_ids:
            item = models.UserCustomTagGroupItem(custom_tag_group_id=group.id, tag_id=tag_id)
            db.add(item)
    db.commit()
    db.refresh(group)
    return group


def admin_delete_custom_group(db: DbSession, group: models.UserCustomTagGroup) -> None:
    """删除自定义标签组"""
    db.delete(group)
    db.commit()


def admin_get_custom_group_tags(db: DbSession, group_id: int) -> list[int]:
    """获取自定义标签组关联的标签ID列表"""
    items = db.scalars(
        select(models.UserCustomTagGroupItem.tag_id).where(
            models.UserCustomTagGroupItem.custom_tag_group_id == group_id
        )
    )
    return list(items)
