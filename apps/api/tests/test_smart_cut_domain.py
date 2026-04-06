"""
Smart Cut 领域逻辑测试

覆盖 F02 数据模型和状态转换
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.smart_cut_domain import (
    EditStatus,
    OutputMode,
    SmartCutEditRecord,
    SmartCutErrorStage,
    SmartCutStatus,
    SmartCutTaskRecord,
    bind_input,
    complete_analyze,
    complete_finalize,
    complete_preview,
    create_task,
    fail_analyze,
    fail_finalize,
    fail_preview,
    generate_input_keys,
    start_analyze,
    start_finalize,
    start_preview,
    validate_upload_keys,
)


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 4, 6, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def sample_task(now: datetime) -> SmartCutTaskRecord:
    """已创建的初始任务"""
    result = create_task(task_id="task-001", user_id=1, created_at=now)
    assert result.task is not None
    return result.task


class TestTaskCreation:
    """任务创建测试"""

    def test_create_task_initial_state(self, now: datetime) -> None:
        result = create_task(task_id="task-001", user_id=1, created_at=now)

        assert result.task is not None
        assert result.task.id == "task-001"
        assert result.task.user_id == 1
        assert result.task.status == SmartCutStatus.WAITING_UPLOAD
        assert "waiting_upload" in result.trace[0]

    def test_create_task_preserves_timestamps(self, now: datetime) -> None:
        result = create_task(task_id="task-001", user_id=1, created_at=now)

        assert result.task is not None
        assert result.task.created_at == now
        assert result.task.updated_at == now


class TestInputBinding:
    """输入绑定测试"""

    def test_bind_input_success(self, sample_task: SmartCutTaskRecord, now: datetime) -> None:
        result = bind_input(
            sample_task,
            video_tos_key="smart-cut/task-001/input/source_video.mp4",
            text_tos_key="smart-cut/task-001/input/reference.txt",
            now=now,
        )

        assert result.task is not None
        assert result.task.status == SmartCutStatus.READY_ANALYZE
        assert result.task.original_video_tos_key == "smart-cut/task-001/input/source_video.mp4"
        assert result.task.reference_text_tos_key == "smart-cut/task-001/input/reference.txt"
        assert "ready_analyze" in result.trace[0]

    def test_bind_input_wrong_state(self, sample_task: SmartCutTaskRecord, now: datetime) -> None:
        # 先绑定一次
        result = bind_input(
            sample_task,
            video_tos_key="smart-cut/task-001/input/source_video.mp4",
            text_tos_key="smart-cut/task-001/input/reference.txt",
            now=now,
        )

        # 再次绑定应该失败
        with pytest.raises(ValueError, match="Cannot bind input from status"):
            bind_input(
                result.task,  # type: ignore[arg-type]
                video_tos_key="smart-cut/task-001/input/other.mp4",
                text_tos_key="smart-cut/task-001/input/other.txt",
                now=now,
            )


class TestAnalyzeStage:
    """analyze 阶段测试"""

    @pytest.fixture
    def ready_task(self, sample_task: SmartCutTaskRecord, now: datetime) -> SmartCutTaskRecord:
        result = bind_input(
            sample_task,
            video_tos_key="smart-cut/task-001/input/source_video.mp4",
            text_tos_key="smart-cut/task-001/input/reference.txt",
            now=now,
        )
        assert result.task is not None
        return result.task

    def test_start_analyze(self, ready_task: SmartCutTaskRecord, now: datetime) -> None:
        result = start_analyze(
            ready_task,
            scheduler_task_id="scheduler-001",
            now=now,
        )

        assert result.task is not None
        assert result.task.status == SmartCutStatus.ANALYZING
        assert result.task.last_scheduler_task_id == "scheduler-001"
        assert result.scheduler_task_type == "smart_cut_analyze"
        assert result.scheduler_payload is not None
        assert result.scheduler_payload["smart_cut_task_id"] == "task-001"
        assert result.scheduler_payload["original_video_tos_key"] == "smart-cut/task-001/input/source_video.mp4"

    def test_complete_analyze(self, ready_task: SmartCutTaskRecord, now: datetime) -> None:
        # 启动 analyze
        result = start_analyze(ready_task, scheduler_task_id="scheduler-001", now=now)
        analyzing_task = result.task

        # 完成 analyze
        result = complete_analyze(
            analyzing_task,  # type: ignore[arg-type]
            script="line1\nline2\n",
            script_tos_key="smart-cut/task-001/analyze/script.json",
            asr_result_tos_key="smart-cut/task-001/analyze/asr_result.json",
            now=now,
        )

        assert result.task is not None
        assert result.task.status == SmartCutStatus.WAITING_USER
        assert result.task.analyze_script == "line1\nline2\n"
        assert result.task.analyze_script_tos_key == "smart-cut/task-001/analyze/script.json"
        assert result.task.asr_result_tos_key == "smart-cut/task-001/analyze/asr_result.json"
        assert result.task.current_stage == "analyze_done"

    def test_fail_analyze(self, ready_task: SmartCutTaskRecord, now: datetime) -> None:
        # 启动 analyze
        result = start_analyze(ready_task, scheduler_task_id="scheduler-001", now=now)
        analyzing_task = result.task

        # 失败
        result = fail_analyze(
            analyzing_task,  # type: ignore[arg-type]
            error_message="ASR processing failed",
            now=now,
        )

        assert result.task is not None
        assert result.task.status == SmartCutStatus.FAILED
        assert result.task.error_stage == SmartCutErrorStage.ANALYZE_FAILED
        assert result.task.error_message == "ASR processing failed"


class TestPreviewStage:
    """preview 阶段测试"""

    @pytest.fixture
    def waiting_user_task(
        self, sample_task: SmartCutTaskRecord, now: datetime
    ) -> SmartCutTaskRecord:
        # 绑定输入
        result = bind_input(
            sample_task,
            video_tos_key="smart-cut/task-001/input/source_video.mp4",
            text_tos_key="smart-cut/task-001/input/reference.txt",
            now=now,
        )
        # 启动 analyze
        result = start_analyze(result.task, scheduler_task_id="scheduler-001", now=now)  # type: ignore[arg-type]
        # 完成 analyze
        result = complete_analyze(
            result.task,  # type: ignore[arg-type]
            script="line1\nline2\n",
            script_tos_key="smart-cut/task-001/analyze/script.json",
            asr_result_tos_key="smart-cut/task-001/analyze/asr_result.json",
            now=now,
        )
        assert result.task is not None
        return result.task

    def test_start_preview(self, waiting_user_task: SmartCutTaskRecord, now: datetime) -> None:
        result = start_preview(
            waiting_user_task,
            edit_id="edit-001",
            edited_script="edited line1\nedited line2\n",
            scheduler_task_id="scheduler-002",
            now=now,
        )

        assert result.task is not None
        assert result.task.status == SmartCutStatus.PREVIEWING
        assert result.task.active_edit_id == "edit-001"

        assert result.new_edit is not None
        assert result.new_edit.id == "edit-001"
        assert result.new_edit.task_id == "task-001"
        assert result.new_edit.edited_script == "edited line1\nedited line2\n"
        assert result.new_edit.status == EditStatus.PROCESSING

        assert result.scheduler_task_type == "smart_cut_preview"
        assert result.scheduler_payload is not None
        assert result.scheduler_payload["edit_id"] == "edit-001"
        assert result.scheduler_payload["edited_script"] == "edited line1\nedited line2\n"

    def test_complete_preview(self, waiting_user_task: SmartCutTaskRecord, now: datetime) -> None:
        # 启动 preview
        result = start_preview(
            waiting_user_task,
            edit_id="edit-001",
            edited_script="edited script",
            scheduler_task_id="scheduler-002",
            now=now,
        )
        previewing_task = result.task
        new_edit = result.new_edit
        assert new_edit is not None

        # 完成 preview
        result = complete_preview(
            previewing_task,  # type: ignore[arg-type]
            new_edit,
            audio_b_tos_key="smart-cut/task-001/preview/edit-001/audio_b.mp3",
            edited_delay_cuts_tos_key="smart-cut/task-001/preview/edit-001/edited_delay_cuts.json",
            pause_cuts_on_original_tos_key="smart-cut/task-001/preview/edit-001/pause_cuts_on_original.json",
            now=now,
        )

        assert result.task is not None
        assert result.task.status == SmartCutStatus.WAITING_USER
        assert result.task.finalize_source_edit_id == "edit-001"  # 记录最后一次成功 preview

        assert result.edit is not None
        assert result.edit.status == EditStatus.SUCCESS
        assert result.edit.audio_b_tos_key == "smart-cut/task-001/preview/edit-001/audio_b.mp3"

    def test_fail_preview(self, waiting_user_task: SmartCutTaskRecord, now: datetime) -> None:
        # 启动 preview
        result = start_preview(
            waiting_user_task,
            edit_id="edit-001",
            edited_script="edited script",
            scheduler_task_id="scheduler-002",
            now=now,
        )
        previewing_task = result.task
        new_edit = result.new_edit
        assert new_edit is not None

        # 失败
        result = fail_preview(
            previewing_task,  # type: ignore[arg-type]
            new_edit,
            error_message="Preview processing failed",
            now=now,
        )

        assert result.task is not None
        assert result.task.status == SmartCutStatus.WAITING_USER
        assert result.task.finalize_source_edit_id is None  # 失败不更新
        assert result.task.error_stage == SmartCutErrorStage.PREVIEW_FAILED

        assert result.edit is not None
        assert result.edit.status == EditStatus.FAILED
        assert result.edit.error_message == "Preview processing failed"

    def test_preview_upload_fail(self, waiting_user_task: SmartCutTaskRecord, now: datetime) -> None:
        # 启动 preview
        result = start_preview(
            waiting_user_task,
            edit_id="edit-001",
            edited_script="edited script",
            scheduler_task_id="scheduler-002",
            now=now,
        )
        previewing_task = result.task
        new_edit = result.new_edit
        assert new_edit is not None

        # 上传失败
        result = fail_preview(
            previewing_task,  # type: ignore[arg-type]
            new_edit,
            error_message="Upload to TOS failed",
            upload_failed=True,
            now=now,
        )

        assert result.task is not None
        assert result.task.error_stage == SmartCutErrorStage.PREVIEW_UPLOAD_FAILED


class TestFinalizeStage:
    """finalize 阶段测试"""

    @pytest.fixture
    def ready_finalize_task(
        self, sample_task: SmartCutTaskRecord, now: datetime
    ) -> SmartCutTaskRecord:
        # 绑定输入
        result = bind_input(
            sample_task,
            video_tos_key="smart-cut/task-001/input/source_video.mp4",
            text_tos_key="smart-cut/task-001/input/reference.txt",
            now=now,
        )
        # 启动并完成 analyze
        result = start_analyze(result.task, scheduler_task_id="scheduler-001", now=now)  # type: ignore[arg-type]
        result = complete_analyze(
            result.task,  # type: ignore[arg-type]
            script="script",
            script_tos_key="script.json",
            asr_result_tos_key="asr.json",
            now=now,
        )
        # 启动并完成 preview
        result = start_preview(
            result.task,  # type: ignore[arg-type]
            edit_id="edit-001",
            edited_script="edited",
            scheduler_task_id="scheduler-002",
            now=now,
        )
        edit = result.new_edit
        assert edit is not None
        result = complete_preview(
            result.task,  # type: ignore[arg-type]
            edit,
            audio_b_tos_key="audio.mp3",
            edited_delay_cuts_tos_key="cuts.json",
            pause_cuts_on_original_tos_key="pauses.json",
            now=now,
        )
        assert result.task is not None
        return result.task

    def test_start_finalize(self, ready_finalize_task: SmartCutTaskRecord, now: datetime) -> None:
        result = start_finalize(
            ready_finalize_task,
            scheduler_task_id="scheduler-003",
            output_mode=OutputMode.VERTICAL_1080P,
            feed_to_ai=True,
            now=now,
        )

        assert result.task is not None
        assert result.task.status == SmartCutStatus.FINALIZING
        assert result.task.output_mode == OutputMode.VERTICAL_1080P
        assert result.task.feed_to_ai is True

        assert result.scheduler_task_type == "smart_cut_finalize"
        assert result.scheduler_payload is not None
        assert result.scheduler_payload["edit_id"] == "edit-001"
        assert result.scheduler_payload["output_mode"] == "vertical_1080p"
        assert result.scheduler_payload["feed_to_ai"] is True

    def test_start_finalize_without_preview(
        self, sample_task: SmartCutTaskRecord, now: datetime
    ) -> None:
        # 绑定输入但未 preview (状态是 ready_analyze 不是 waiting_user)
        result = bind_input(
            sample_task,
            video_tos_key="smart-cut/task-001/input/source_video.mp4",
            text_tos_key="smart-cut/task-001/input/reference.txt",
            now=now,
        )

        # 应该从状态检查失败
        with pytest.raises(ValueError, match="Cannot start finalize from status"):
            start_finalize(
                result.task,  # type: ignore[arg-type]
                scheduler_task_id="scheduler-003",
                now=now,
            )

    def test_complete_finalize(
        self, ready_finalize_task: SmartCutTaskRecord, now: datetime
    ) -> None:
        # 启动 finalize
        result = start_finalize(ready_finalize_task, scheduler_task_id="scheduler-003", now=now)
        finalizing_task = result.task

        # 完成 finalize
        result = complete_finalize(
            finalizing_task,  # type: ignore[arg-type]
            final_video_tos_key="smart-cut/task-001/final/output.mp4",
            groundtruth_tos_key="smart-cut/task-001/final/groundtruth/",
            now=now,
        )

        assert result.task is not None
        assert result.task.status == SmartCutStatus.SUCCESS
        assert result.task.final_video_tos_key == "smart-cut/task-001/final/output.mp4"
        assert result.task.groundtruth_tos_key == "smart-cut/task-001/final/groundtruth/"

    def test_complete_finalize_without_groundtruth(
        self, ready_finalize_task: SmartCutTaskRecord, now: datetime
    ) -> None:
        result = start_finalize(ready_finalize_task, scheduler_task_id="scheduler-003", now=now)
        finalizing_task = result.task

        result = complete_finalize(
            finalizing_task,  # type: ignore[arg-type]
            final_video_tos_key="smart-cut/task-001/final/output.mp4",
            groundtruth_tos_key=None,
            now=now,
        )

        assert result.task is not None
        assert result.task.status == SmartCutStatus.SUCCESS
        assert result.task.groundtruth_tos_key is None

    def test_fail_finalize(self, ready_finalize_task: SmartCutTaskRecord, now: datetime) -> None:
        result = start_finalize(ready_finalize_task, scheduler_task_id="scheduler-003", now=now)
        finalizing_task = result.task

        result = fail_finalize(
            finalizing_task,  # type: ignore[arg-type]
            error_message="Final video encoding failed",
            now=now,
        )

        assert result.task is not None
        assert result.task.status == SmartCutStatus.FAILED
        assert result.task.error_stage == SmartCutErrorStage.FINALIZE_FAILED

    def test_fail_finalize_upload(self, ready_finalize_task: SmartCutTaskRecord, now: datetime) -> None:
        result = start_finalize(ready_finalize_task, scheduler_task_id="scheduler-003", now=now)
        finalizing_task = result.task

        result = fail_finalize(
            finalizing_task,  # type: ignore[arg-type]
            error_message="Upload to TOS failed",
            upload_failed=True,
            now=now,
        )

        assert result.task is not None
        assert result.task.error_stage == SmartCutErrorStage.FINAL_UPLOAD_FAILED


class TestMultiplePreviews:
    """多次 preview 测试"""

    @pytest.fixture
    def after_first_preview(
        self, sample_task: SmartCutTaskRecord, now: datetime
    ) -> tuple[SmartCutTaskRecord, SmartCutEditRecord]:
        # 绑定输入
        result = bind_input(
            sample_task,
            video_tos_key="smart-cut/task-001/input/source_video.mp4",
            text_tos_key="smart-cut/task-001/input/reference.txt",
            now=now,
        )
        # analyze
        result = start_analyze(result.task, scheduler_task_id="s-001", now=now)  # type: ignore[arg-type]
        result = complete_analyze(
            result.task,  # type: ignore[arg-type]
            script="s",
            script_tos_key="s.json",
            asr_result_tos_key="a.json",
            now=now,
        )
        # first preview
        result = start_preview(
            result.task,  # type: ignore[arg-type]
            edit_id="edit-001",
            edited_script="first edit",
            scheduler_task_id="s-002",
            now=now,
        )
        edit1 = result.new_edit
        assert edit1 is not None
        result = complete_preview(
            result.task,  # type: ignore[arg-type]
            edit1,
            audio_b_tos_key="audio1.mp3",
            edited_delay_cuts_tos_key="cuts1.json",
            pause_cuts_on_original_tos_key="pauses1.json",
            now=now,
        )
        return result.task, edit1  # type: ignore[return-value]

    def test_second_preview_updates_active_edit(
        self, after_first_preview: tuple[SmartCutTaskRecord, SmartCutEditRecord], now: datetime
    ) -> None:
        task, _ = after_first_preview
        assert task.finalize_source_edit_id == "edit-001"

        # 第二次 preview
        result = start_preview(
            task,
            edit_id="edit-002",
            edited_script="second edit",
            scheduler_task_id="s-003",
            now=now,
        )

        assert result.task.active_edit_id == "edit-002"
        assert result.new_edit.id == "edit-002"

    def test_finalize_uses_last_successful_preview(
        self, after_first_preview: tuple[SmartCutTaskRecord, SmartCutEditRecord], now: datetime
    ) -> None:
        task, edit1 = after_first_preview

        # 第二次 preview 失败
        result = start_preview(
            task,
            edit_id="edit-002",
            edited_script="second edit",
            scheduler_task_id="s-003",
            now=now,
        )
        edit2 = result.new_edit
        assert edit2 is not None
        result = fail_preview(
            result.task,  # type: ignore[arg-type]
            edit2,
            error_message="Preview failed",
            now=now,
        )

        # finalize_source_edit_id 应该还是第一次的
        assert result.task.finalize_source_edit_id == "edit-001"

        # 第三次 preview 成功
        result = start_preview(
            result.task,  # type: ignore[arg-type]
            edit_id="edit-003",
            edited_script="third edit",
            scheduler_task_id="s-004",
            now=now,
        )
        edit3 = result.new_edit
        assert edit3 is not None
        result = complete_preview(
            result.task,  # type: ignore[arg-type]
            edit3,
            audio_b_tos_key="audio3.mp3",
            edited_delay_cuts_tos_key="cuts3.json",
            pause_cuts_on_original_tos_key="pauses3.json",
            now=now,
        )

        # 现在 finalize_source_edit_id 应该是第三次的
        assert result.task.finalize_source_edit_id == "edit-003"


class TestKeyValidation:
    """TOS key 验证测试"""

    def test_generate_input_keys(self) -> None:
        video_base, text_key = generate_input_keys("task-001")
        assert video_base == "smart-cut/task-001/input/source_video"
        assert text_key == "smart-cut/task-001/input/reference.txt"

    def test_validate_upload_keys_valid(self) -> None:
        assert validate_upload_keys(
            "task-001",
            "smart-cut/task-001/input/source_video.mp4",
            "smart-cut/task-001/input/reference.txt",
        ) is True

    def test_validate_upload_keys_wrong_prefix(self) -> None:
        assert validate_upload_keys(
            "task-001",
            "smart-cut/other-task/input/source_video.mp4",
            "smart-cut/task-001/input/reference.txt",
        ) is False

    def test_validate_upload_keys_not_in_input(self) -> None:
        assert validate_upload_keys(
            "task-001",
            "smart-cut/task-001/wrong/source_video.mp4",
            "smart-cut/task-001/input/reference.txt",
        ) is False

    def test_validate_upload_keys_wrong_text_name(self) -> None:
        assert validate_upload_keys(
            "task-001",
            "smart-cut/task-001/input/source_video.mp4",
            "smart-cut/task-001/input/wrong.txt",
        ) is False


class TestStateMachineGuards:
    """状态机守卫测试"""

    def test_cannot_start_analyze_from_wrong_state(
        self, sample_task: SmartCutTaskRecord, now: datetime
    ) -> None:
        # 未绑定输入直接启动 analyze
        with pytest.raises(ValueError, match="Cannot start analyze from status"):
            start_analyze(sample_task, scheduler_task_id="s-001", now=now)

    def test_cannot_start_preview_from_wrong_state(
        self, sample_task: SmartCutTaskRecord, now: datetime
    ) -> None:
        with pytest.raises(ValueError, match="Cannot start preview from status"):
            start_preview(
                sample_task,
                edit_id="edit-001",
                edited_script="edit",
                scheduler_task_id="s-002",
                now=now,
            )

    def test_cannot_start_finalize_from_wrong_state(
        self, sample_task: SmartCutTaskRecord, now: datetime
    ) -> None:
        with pytest.raises(ValueError, match="Cannot start finalize from status"):
            start_finalize(sample_task, scheduler_task_id="s-003", now=now)

    def test_cannot_complete_analyze_from_wrong_state(
        self, sample_task: SmartCutTaskRecord, now: datetime
    ) -> None:
        with pytest.raises(ValueError, match="Cannot complete analyze from status"):
            complete_analyze(
                sample_task,
                script="script",
                script_tos_key="s.json",
                asr_result_tos_key="a.json",
                now=now,
            )
