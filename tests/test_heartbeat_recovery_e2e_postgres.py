from datetime import datetime, timedelta
import os
import uuid

import pytest

from apps.models.device import DeviceStatus, SmartCutDevice
from apps.models.scheduler_task import SchedulerTask, SchedulerTaskStatus, SchedulerTaskType
from apps.models.task import CurrentStage, SmartCutTask, TaskStatus
from apps.scheduler.scheduler_service import SchedulerService
from apps.services.device_service import DeviceService
from configs.database import create_session_factory, init_scheduler_db


@pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL is required for PostgreSQL-backed heartbeat recovery e2e",
)
def test_heartbeat_timeout_and_recovery_through_shared_postgres() -> None:
    db_url = os.environ["TEST_DATABASE_URL"]
    suffix = uuid.uuid4().hex[:8]
    init_scheduler_db(db_url)
    session_factory = create_session_factory(db_url)

    with session_factory() as db:
        device_service = DeviceService(db)

        worker_1 = device_service.register_device(
            worker_id=f"worker-timeout-1-{suffix}",
            worker_name="Worker Timeout 1",
            supported_task_types=[SchedulerTaskType.SMART_CUT_ANALYZE.value],
        )
        worker_2 = device_service.register_device(
            worker_id=f"worker-timeout-2-{suffix}",
            worker_name="Worker Timeout 2",
            supported_task_types=[SchedulerTaskType.SMART_CUT_ANALYZE.value],
        )

        # Isolate this recovery scenario from any previously registered analyze workers
        for other_worker in db.query(SmartCutDevice).all():
            if other_worker.worker_id not in {worker_1.worker_id, worker_2.worker_id}:
                other_worker.status = DeviceStatus.OFFLINE
        db.commit()

        business_task = SmartCutTask(
            user_id="heartbeat-user",
            status=TaskStatus.READY_ANALYZE,
            current_stage=CurrentStage.ANALYZE,
        )
        db.add(business_task)
        db.commit()
        db.refresh(business_task)

        scheduler_task = SchedulerTask(
            task_type=SchedulerTaskType.SMART_CUT_ANALYZE,
            status=SchedulerTaskStatus.PENDING,
            business_task_id=business_task.id,
            payload={
                "smart_cut_task_id": business_task.id,
                "original_video_tos_key": "smart-cut/demo/input/source_video.mp4",
                "reference_text_tos_key": "smart-cut/demo/input/reference.txt",
            },
        )
        db.add(scheduler_task)
        db.commit()
        db.refresh(scheduler_task)

        scheduler = SchedulerService(db, device_service)
        assert scheduler.schedule_pending_tasks() >= 1

        assigned_task = db.query(SchedulerTask).filter_by(id=scheduler_task.id).first()
        assert assigned_task.status == SchedulerTaskStatus.ASSIGNED
        assert assigned_task.assigned_worker_id == worker_1.worker_id

        # Force worker_1 to look stale and keep worker_2 healthy for recovery.
        worker_1_row = db.query(SmartCutDevice).filter_by(worker_id=worker_1.worker_id).first()
        worker_2_row = db.query(SmartCutDevice).filter_by(worker_id=worker_2.worker_id).first()
        worker_1_row.current_task_id = assigned_task.id
        worker_1_row.heartbeat_at = datetime.utcnow() - timedelta(seconds=300)
        worker_1_row.status = DeviceStatus.IDLE
        worker_2_row.heartbeat_at = datetime.utcnow()
        worker_2_row.status = DeviceStatus.IDLE
        db.commit()

        assert scheduler.check_worker_heartbeats(timeout_seconds=60) == 1

        worker_1_row = db.query(SmartCutDevice).filter_by(worker_id=worker_1.worker_id).first()
        reassigned_task = db.query(SchedulerTask).filter_by(id=scheduler_task.id).first()

        assert worker_1_row.status == DeviceStatus.OFFLINE
        assert worker_1_row.current_task_id is None
        assert reassigned_task.status == SchedulerTaskStatus.PENDING
        assert reassigned_task.assigned_worker_id is None
        assert reassigned_task.assigned_at is None
        assert reassigned_task.started_at is None

        assert scheduler.schedule_pending_tasks() >= 1

        reassigned_task = db.query(SchedulerTask).filter_by(id=scheduler_task.id).first()
        worker_2_row = db.query(SmartCutDevice).filter_by(worker_id=worker_2.worker_id).first()

        assert reassigned_task.status == SchedulerTaskStatus.ASSIGNED
        assert reassigned_task.assigned_worker_id == worker_2.worker_id
        assert worker_2_row.current_task_id == reassigned_task.id

        # Recovery of the offline worker should return it to idle when it re-registers.
        recovered = device_service.register_device(
            worker_id=f"worker-timeout-1-{suffix}",
            worker_name="Worker Timeout 1",
            supported_task_types=[SchedulerTaskType.SMART_CUT_ANALYZE.value],
        )
        assert recovered.status == DeviceStatus.IDLE
