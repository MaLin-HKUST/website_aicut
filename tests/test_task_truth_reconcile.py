from pathlib import Path

from apps.models.task import CurrentStage, SmartCutTask, TaskStatus
from apps.scheduler.scheduler_service import SchedulerService
from apps.services.device_service import DeviceService
from configs.database import Base, build_engine
from sqlalchemy.orm import sessionmaker


def test_reconcile_orphaned_preview_task_returns_to_waiting_user(tmp_path: Path) -> None:
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
        assert task.status == TaskStatus.WAITING_USER
        assert task.current_stage == CurrentStage.USER_SELECT
        assert task.failed_stage == "preview"
        assert task.current_run_id is None
