from pathlib import Path
from datetime import datetime

from apps.api.routes.tasks import build_task_center_item
from apps.models.device import DeviceStatus, SmartCutDevice
from apps.models.edit import EditStatus, SmartCutEdit
from apps.models.scheduler_task import SchedulerTask, SchedulerTaskStatus, SchedulerTaskType
from apps.models.task import CurrentStage, SmartCutTask, TaskStatus
from apps.models.task_run import SmartCutTaskRun, TaskRunStatus, TaskRunType
from apps.scheduler.scheduler_service import SchedulerService
from apps.services.device_service import DeviceService
from configs.database import Base, build_engine
from sqlalchemy.orm import sessionmaker
from worker.core import SmartCutWorker


def test_reconcile_orphaned_preview_task_marks_preview_failed(tmp_path: Path) -> None:
    db_path = tmp_path / "reconcile.db"
    engine = build_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with session_local() as db:
        task = SmartCutTask(
            user_id="alice",
            company_id=9,
            status=TaskStatus.PREVIEWING,
            current_stage=CurrentStage.PREVIEW,
            current_run_id="run-preview-1",
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        scheduler = SchedulerService(db, DeviceService(db))
        reconciled = scheduler.reconcile_orphaned_business_tasks()
        assert reconciled == 1

        db.refresh(task)
        assert task.status == TaskStatus.PREVIEW_FAILED
        assert task.current_stage == CurrentStage.PREVIEW
        assert task.failed_stage == "preview"
        assert task.status_detail == "试听失败"
        assert task.current_run_id is None


def test_analyze_post_can_auto_queue_finalize(tmp_path: Path) -> None:
    db_path = tmp_path / "auto_finalize.db"
    engine = build_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with session_local() as db:
        task = SmartCutTask(
            user_id="alice",
            company_id=9,
            status=TaskStatus.ANALYZING,
            current_stage=CurrentStage.ANALYZE,
            original_video_url="smart-cut/demo/input/source_video.mp4",
            reference_text_url="smart-cut/demo/input/reference.txt",
        )
        db.add(task)
        db.flush()

        analyze_scheduler = SchedulerTask(
            task_type=SchedulerTaskType.SMART_CUT_ANALYZE,
            status=SchedulerTaskStatus.RUNNING,
            business_task_id=task.id,
            payload={
                "smart_cut_task_id": task.id,
                "original_video_tos_key": task.original_video_url,
                "reference_text_tos_key": task.reference_text_url,
                "auto_finalize_after_analyze": True,
                "auto_finalize_output_mode": "vertical_1080p",
                "auto_finalize_feed_to_ai": False,
            },
            result={
                "script": "保留重点文案",
                "asr_result_tos_key": "smart-cut/demo/analyze/asr.json",
            },
        )
        db.add(analyze_scheduler)
        db.flush()

        analyze_run = SmartCutTaskRun(
            task_id=task.id,
            run_type=TaskRunType.ANALYZE,
            status=TaskRunStatus.RUNNING,
            sequence_number=1,
            scheduler_task_id=analyze_scheduler.id,
        )
        db.add(analyze_run)

        edit = SmartCutEdit(
            task_id=task.id,
            edited_script="保留重点文案",
            status=EditStatus.SUCCESS,
            delay_cuts_tos_key="smart-cut/demo/analyze/delay_cuts.json",
            version_number=1,
        )
        db.add(edit)

        worker = SmartCutDevice(
            worker_id="worker-1",
            worker_name="Worker 1",
            status=DeviceStatus.POST,
            current_task_id=analyze_scheduler.id,
            supported_task_types=["smart_cut_analyze", "smart_cut_finalize"],
        )
        db.add(worker)
        db.commit()

        scheduler = SchedulerService(db, DeviceService(db))
        scheduler._advance_business_task_on_post(analyze_scheduler, worker)

        db.refresh(task)
        db.refresh(worker)
        assert task.status == TaskStatus.FINALIZING
        assert task.current_stage == CurrentStage.FINALIZE
        assert task.status_detail == "正在生成视频"
        assert task.latest_successful_run_id == analyze_run.id
        assert task.current_run_id is not None
        assert worker.status == DeviceStatus.IDLE
        assert worker.current_task_id is None

        finalize_scheduler = (
            db.query(SchedulerTask)
            .filter(
                SchedulerTask.business_task_id == task.id,
                SchedulerTask.task_type == SchedulerTaskType.SMART_CUT_FINALIZE,
            )
            .order_by(SchedulerTask.created_at.desc())
            .first()
        )
        assert finalize_scheduler is not None
        assert finalize_scheduler.status == SchedulerTaskStatus.PENDING
        assert finalize_scheduler.payload["edit_id"] == edit.id
        assert finalize_scheduler.payload["output_mode"] == "vertical_1080p"
        assert finalize_scheduler.payload["feed_to_ai"] is False

        finalize_run = (
            db.query(SmartCutTaskRun)
            .filter(SmartCutTaskRun.scheduler_task_id == finalize_scheduler.id)
            .first()
        )
        assert finalize_run is not None
        assert finalize_run.run_type == TaskRunType.FINALIZE
        assert finalize_run.status == TaskRunStatus.QUEUED
        assert finalize_run.source_edit_id == edit.id


def test_running_scheduler_with_persisted_result_self_heals_and_queues_finalize(tmp_path: Path) -> None:
    db_path = tmp_path / "running_result_self_heal.db"
    engine = build_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with session_local() as db:
        task = SmartCutTask(
            user_id="alice",
            company_id=9,
            status=TaskStatus.ANALYZING,
            current_stage=CurrentStage.ANALYZE,
            status_detail="正在分析",
            original_video_url="smart-cut/demo/input/source_video.mp4",
            reference_text_url="smart-cut/demo/input/reference.txt",
        )
        db.add(task)
        db.flush()

        analyze_scheduler = SchedulerTask(
            task_type=SchedulerTaskType.SMART_CUT_ANALYZE,
            status=SchedulerTaskStatus.RUNNING,
            business_task_id=task.id,
            assigned_worker_id="worker1-phase6",
            payload={
                "smart_cut_task_id": task.id,
                "original_video_tos_key": task.original_video_url,
                "reference_text_tos_key": task.reference_text_url,
                "auto_finalize_after_analyze": True,
            },
            result={
                "script": {"segments": [{"text": "保留重点文案"}]},
                "asr_result_tos_key": "smart-cut/demo/analyze/asr.json",
            },
        )
        db.add(analyze_scheduler)
        db.flush()

        analyze_run = SmartCutTaskRun(
            task_id=task.id,
            run_type=TaskRunType.ANALYZE,
            status=TaskRunStatus.QUEUED,
            sequence_number=1,
            scheduler_task_id=analyze_scheduler.id,
        )
        db.add(analyze_run)

        edit = SmartCutEdit(
            task_id=task.id,
            edited_script={"segments": [{"text": "保留重点文案"}]},
            status=EditStatus.SUCCESS,
            delay_cuts_tos_key="smart-cut/demo/analyze/delay_cuts.json",
            version_number=1,
        )
        db.add(edit)

        worker = SmartCutDevice(
            worker_id="worker1-phase6",
            worker_name="Worker 1 Phase 6",
            company_id=9,
            status=DeviceStatus.IDLE,
            current_task_id=analyze_scheduler.id,
            supported_task_types=["smart_cut_analyze", "smart_cut_finalize"],
            heartbeat_at=datetime.utcnow(),
        )
        db.add(worker)
        db.commit()

        scheduler = SchedulerService(db, DeviceService(db))
        stats = scheduler.run_cycle()

        db.refresh(task)
        db.refresh(analyze_scheduler)
        db.refresh(analyze_run)
        db.refresh(worker)
        assert stats["completed"] == 1
        assert analyze_scheduler.status == SchedulerTaskStatus.SUCCESS
        assert analyze_run.status == TaskRunStatus.SUCCESS
        assert task.status == TaskStatus.FINALIZING
        assert task.current_stage == CurrentStage.FINALIZE
        assert task.status_detail == "正在生成视频"
        assert task.latest_successful_run_id == analyze_run.id
        assert task.current_run_id is not None
        assert worker.status == DeviceStatus.IDLE
        assert worker.current_task_id != analyze_scheduler.id

        finalize_schedulers = (
            db.query(SchedulerTask)
            .filter(
                SchedulerTask.business_task_id == task.id,
                SchedulerTask.task_type == SchedulerTaskType.SMART_CUT_FINALIZE,
            )
            .all()
        )
        assert len(finalize_schedulers) == 1
        assert finalize_schedulers[0].status in {
            SchedulerTaskStatus.PENDING,
            SchedulerTaskStatus.ASSIGNED,
        }
        if finalize_schedulers[0].status == SchedulerTaskStatus.ASSIGNED:
            assert worker.current_task_id == finalize_schedulers[0].id

        stats = scheduler.run_cycle()
        assert stats["completed"] == 0
        assert (
            db.query(SchedulerTask)
            .filter(
                SchedulerTask.business_task_id == task.id,
                SchedulerTask.task_type == SchedulerTaskType.SMART_CUT_FINALIZE,
            )
            .count()
            == 1
        )


def test_post_scheduler_with_result_closes_without_device_row(tmp_path: Path) -> None:
    db_path = tmp_path / "post_without_device.db"
    engine = build_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with session_local() as db:
        task = SmartCutTask(
            user_id="alice",
            company_id=9,
            status=TaskStatus.FINALIZING,
            current_stage=CurrentStage.FINALIZE,
            status_detail="正在生成字幕",
        )
        db.add(task)
        db.flush()

        finalize_scheduler = SchedulerTask(
            task_type=SchedulerTaskType.SMART_CUT_FINALIZE,
            status=SchedulerTaskStatus.POST,
            business_task_id=task.id,
            assigned_worker_id="missing-worker",
            payload={"smart_cut_task_id": task.id},
            result={
                "final_video_url": "https://example.test/final.mp4",
                "subtitle_srt_url": "https://example.test/final.srt",
            },
        )
        db.add(finalize_scheduler)
        db.flush()

        finalize_run = SmartCutTaskRun(
            task_id=task.id,
            run_type=TaskRunType.FINALIZE,
            status=TaskRunStatus.RUNNING,
            sequence_number=1,
            scheduler_task_id=finalize_scheduler.id,
        )
        db.add(finalize_run)
        db.commit()

        scheduler = SchedulerService(db, DeviceService(db))
        assert scheduler.reconcile_completed_scheduler_tasks() == 1

        db.refresh(task)
        db.refresh(finalize_scheduler)
        db.refresh(finalize_run)
        assert finalize_scheduler.status == SchedulerTaskStatus.SUCCESS
        assert finalize_run.status == TaskRunStatus.SUCCESS
        assert task.status == TaskStatus.SUCCESS
        assert task.current_stage == CurrentStage.COMPLETE
        assert task.status_detail == "已完成"
        assert task.final_video_url == "https://example.test/final.mp4"
        assert task.subtitle_srt_url == "https://example.test/final.srt"


def test_auto_finalize_queue_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "auto_finalize_idempotent.db"
    engine = build_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with session_local() as db:
        task = SmartCutTask(
            user_id="alice",
            company_id=9,
            status=TaskStatus.ANALYZING,
            current_stage=CurrentStage.ANALYZE,
            original_video_url="smart-cut/demo/input/source_video.mp4",
        )
        db.add(task)
        db.flush()

        edit = SmartCutEdit(
            task_id=task.id,
            edited_script="保留重点文案",
            status=EditStatus.SUCCESS,
            delay_cuts_tos_key="smart-cut/demo/analyze/delay_cuts.json",
            version_number=1,
        )
        db.add(edit)
        db.commit()

        scheduler = SchedulerService(db, DeviceService(db))
        payload = {
            "auto_finalize_after_analyze": True,
            "auto_finalize_output_mode": "original",
            "auto_finalize_feed_to_ai": True,
        }

        first_run = scheduler._queue_finalize_after_analyze(task, payload)
        second_run = scheduler._queue_finalize_after_analyze(task, payload)
        assert first_run is not None
        assert second_run is not None
        assert second_run.scheduler_task_id == first_run.scheduler_task_id
        assert (
            db.query(SchedulerTask)
            .filter(
                SchedulerTask.business_task_id == task.id,
                SchedulerTask.task_type == SchedulerTaskType.SMART_CUT_FINALIZE,
            )
            .count()
            == 1
        )


def test_worker_success_result_moves_scheduler_task_to_post(tmp_path: Path) -> None:
    db_path = tmp_path / "worker_store_result.db"
    engine = build_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with session_local() as db:
        task = SmartCutTask(
            user_id="alice",
            company_id=9,
            status=TaskStatus.ANALYZING,
            current_stage=CurrentStage.ANALYZE,
        )
        db.add(task)
        db.flush()
        scheduler_task = SchedulerTask(
            task_type=SchedulerTaskType.SMART_CUT_ANALYZE,
            status=SchedulerTaskStatus.RUNNING,
            business_task_id=task.id,
            payload={},
        )
        db.add(scheduler_task)
        db.commit()

        worker = SmartCutWorker.__new__(SmartCutWorker)
        worker.SessionLocal = session_local
        worker._store_task_result(
            scheduler_task,
            {"asr_result_tos_key": Path("smart-cut/demo/asr.json")},
        )

        db.refresh(scheduler_task)
        assert scheduler_task.status == SchedulerTaskStatus.POST
        assert scheduler_task.result == {"asr_result_tos_key": "smart-cut/demo/asr.json"}


def test_scheduler_respects_worker_company_affinity_and_keeps_extra_tasks_queued(tmp_path: Path) -> None:
    db_path = tmp_path / "affinity.db"
    engine = build_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with session_local() as db:
        company9_task = SmartCutTask(
            user_id="alice",
            company_id=9,
            status=TaskStatus.READY_ANALYZE,
            current_stage=CurrentStage.ANALYZE,
            status_detail="排队中",
        )
        company10_task = SmartCutTask(
            user_id="bob",
            company_id=10,
            status=TaskStatus.READY_ANALYZE,
            current_stage=CurrentStage.ANALYZE,
            status_detail="排队中",
        )
        db.add_all([company9_task, company10_task])
        db.flush()

        analyze_9 = SchedulerTask(
            task_type=SchedulerTaskType.SMART_CUT_ANALYZE,
            status=SchedulerTaskStatus.PENDING,
            business_task_id=company9_task.id,
            payload={},
        )
        analyze_10 = SchedulerTask(
            task_type=SchedulerTaskType.SMART_CUT_ANALYZE,
            status=SchedulerTaskStatus.PENDING,
            business_task_id=company10_task.id,
            payload={},
        )
        db.add_all([analyze_9, analyze_10])

        worker = SmartCutDevice(
            worker_id="worker-company-9",
            worker_name="Worker Company 9",
            company_id=9,
            status=DeviceStatus.IDLE,
            supported_task_types=["smart_cut_analyze"],
            heartbeat_at=company9_task.created_at,
        )
        db.add(worker)
        db.commit()

        scheduler = SchedulerService(db, DeviceService(db))
        assert scheduler.schedule_pending_tasks() == 1

        db.refresh(analyze_9)
        db.refresh(analyze_10)
        assert analyze_9.assigned_worker_id == "worker-company-9"
        assert analyze_10.assigned_worker_id is None

        queued_item = build_task_center_item(
            db,
            company10_task,
            include_admin_fields=False,
        )
        assert queued_item.status == "queued"
        assert queued_item.progress_detail == "排队中"


def test_device_status_updates_clear_stale_current_task_on_idle(tmp_path: Path) -> None:
    db_path = tmp_path / "device_clear.db"
    engine = build_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with session_local() as db:
        device_service = DeviceService(db)
        device = device_service.register_device(
            worker_id="worker-clear",
            worker_name="Worker Clear",
            supported_task_types=["smart_cut_finalize"],
        )

        device_service.update_device_status(
            worker_id=device.worker_id,
            status=DeviceStatus.RUNNING,
            current_task_id="scheduler-1",
        )
        device_service.update_device_status(
            worker_id=device.worker_id,
            status=DeviceStatus.IDLE,
            current_task_id=None,
        )

        refreshed = device_service.get_device(device.worker_id)
        assert refreshed is not None
        assert refreshed.status == DeviceStatus.IDLE
        assert refreshed.current_task_id is None

        refreshed.current_task_id = "scheduler-2"
        db.commit()

        device_service.heartbeat(
            worker_id=device.worker_id,
            status=DeviceStatus.IDLE,
            current_task_id=None,
        )

        refreshed = device_service.get_device(device.worker_id)
        assert refreshed is not None
        assert refreshed.current_task_id is None
