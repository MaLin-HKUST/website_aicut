"""Worker runtime entrypoint.

Locks the formal startup contract for the gateway runtime so Docker and
local smoke tests both go through the same path.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any, Sequence

from apps.models.scheduler_task import SchedulerTaskType
from apps.services.tos_service import TOSService
from worker.core import SmartCutWorker
from worker.processors.analyze_processor import AnalyzeProcessor
from worker.processors.preview_processor import PreviewProcessor
from worker.processors.finalize_processor import FinalizeProcessor


logger = logging.getLogger(__name__)

DEFAULT_SUPPORTED_TASK_TYPES = [
    SchedulerTaskType.SMART_CUT_ANALYZE.value,
    SchedulerTaskType.SMART_CUT_PREVIEW.value,
    SchedulerTaskType.SMART_CUT_FINALIZE.value,
]


@dataclass
class WorkerRuntimeConfig:
    worker_id: str
    worker_name: str
    db_url: str
    api_base_url: str
    workspace: str
    use_fake_tos: bool
    fake_tos_base: str
    heartbeat_interval: float
    poll_interval: float
    supported_task_types: list[str]
    log_level: str

    @classmethod
    def from_env(cls) -> "WorkerRuntimeConfig":
        supported_task_types = os.environ.get("SUPPORTED_TASK_TYPES", "")
        parsed_task_types = [
            item.strip()
            for item in supported_task_types.split(",")
            if item.strip()
        ]

        worker_id = os.environ.get("WORKER_ID", "worker_01").strip()
        worker_name = os.environ.get("WORKER_NAME", f"Smart Cut Worker {worker_id}").strip()

        return cls(
            worker_id=worker_id,
            worker_name=worker_name,
            db_url=os.environ.get("DATABASE_URL", "sqlite:///./worker.db").strip(),
            api_base_url=os.environ.get("API_BASE_URL", "http://localhost:8000").strip(),
            workspace=os.environ.get("WORKER_DATA_BASE", "/data/smart-cut").strip(),
            use_fake_tos=os.environ.get("USE_FAKE_TOS", "true").lower() == "true",
            fake_tos_base=os.environ.get("FAKE_TOS_BASE_PATH", "/tmp/fake_tos").strip(),
            heartbeat_interval=float(os.environ.get("HEARTBEAT_INTERVAL", "10")),
            poll_interval=float(os.environ.get("POLL_INTERVAL", "5")),
            supported_task_types=parsed_task_types or list(DEFAULT_SUPPORTED_TASK_TYPES),
            log_level=os.environ.get("LOG_LEVEL", "INFO").strip(),
        )

    def validate(self) -> None:
        if not self.worker_id:
            raise ValueError("WORKER_ID must not be empty")
        if not self.worker_name:
            raise ValueError("WORKER_NAME must not be empty")
        if not self.db_url:
            raise ValueError("DATABASE_URL must not be empty")
        if not self.api_base_url:
            raise ValueError("API_BASE_URL must not be empty")
        if not self.workspace:
            raise ValueError("WORKER_DATA_BASE must not be empty")
        if self.heartbeat_interval <= 0:
            raise ValueError("HEARTBEAT_INTERVAL must be greater than 0")
        if self.poll_interval <= 0:
            raise ValueError("POLL_INTERVAL must be greater than 0")

        invalid_task_types = sorted(set(self.supported_task_types) - set(DEFAULT_SUPPORTED_TASK_TYPES))
        if invalid_task_types:
            raise ValueError(
                "SUPPORTED_TASK_TYPES contains unsupported values: "
                + ", ".join(invalid_task_types)
            )

    def to_log_fields(self) -> dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "worker_name": self.worker_name,
            "db_url": self.db_url,
            "api_base_url": self.api_base_url,
            "workspace": self.workspace,
            "use_fake_tos": self.use_fake_tos,
            "fake_tos_base": self.fake_tos_base if self.use_fake_tos else None,
            "heartbeat_interval": self.heartbeat_interval,
            "poll_interval": self.poll_interval,
            "supported_task_types": self.supported_task_types,
        }


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def build_tos_service(config: WorkerRuntimeConfig) -> TOSService:
    return TOSService(
        use_fake=config.use_fake_tos,
        fake_base_path=config.fake_tos_base,
    )


def build_worker(config: WorkerRuntimeConfig, tos_service: Any) -> SmartCutWorker:
    return SmartCutWorker(
        worker_id=config.worker_id,
        worker_name=config.worker_name,
        supported_task_types=config.supported_task_types,
        api_base_url=config.api_base_url,
        tos_service=tos_service,
        workspace=config.workspace,
        db_url=config.db_url,
        heartbeat_interval=config.heartbeat_interval,
        poll_interval=config.poll_interval,
    )


def register_processors(
    worker: SmartCutWorker,
    tos_service: Any,
    config: WorkerRuntimeConfig,
) -> list[str]:
    processor_factories = {
        SchedulerTaskType.SMART_CUT_ANALYZE.value: AnalyzeProcessor,
        SchedulerTaskType.SMART_CUT_PREVIEW.value: PreviewProcessor,
        SchedulerTaskType.SMART_CUT_FINALIZE.value: FinalizeProcessor,
    }

    registered: list[str] = []
    for task_type in config.supported_task_types:
        processor_cls = processor_factories[task_type]
        worker.register_processor(task_type, processor_cls(tos_service, config.workspace))
        registered.append(task_type)
    return registered


async def run_runtime(
    config: WorkerRuntimeConfig,
    run_seconds: float | None = None,
) -> int:
    config.validate()
    logger.info("Worker runtime contract: %s", config.to_log_fields())

    tos_service = build_tos_service(config)
    worker = build_worker(config, tos_service)
    registered = register_processors(worker, tos_service, config)
    logger.info("Registered processors: %s", ", ".join(registered))

    stop_task: asyncio.Task | None = None
    if run_seconds is not None:
        async def stop_later() -> None:
            await asyncio.sleep(run_seconds)
            logger.info("Timed smoke run finished after %.2fs, requesting shutdown", run_seconds)
            worker.request_shutdown()

        stop_task = asyncio.create_task(stop_later())

    try:
        await worker.run()
    finally:
        if stop_task is not None and not stop_task.done():
            stop_task.cancel()
            try:
                await stop_task
            except asyncio.CancelledError:
                pass

    return 0


async def run_from_cli(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smart Cut Worker runtime entrypoint")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate config and processor wiring without entering the main loop",
    )
    parser.add_argument(
        "--run-seconds",
        type=float,
        default=None,
        help="Run the worker for a bounded number of seconds before shutdown",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        help="Override LOG_LEVEL for this invocation",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    config = WorkerRuntimeConfig.from_env()
    if args.log_level:
        config.log_level = args.log_level

    configure_logging(config.log_level)
    config.validate()
    logger.info("Formal runtime entry: python -m worker.main")
    logger.info("Startup contract resolved: %s", config.to_log_fields())

    if args.check:
        tos_service = build_tos_service(config)
        worker = build_worker(config, tos_service)
        registered = register_processors(worker, tos_service, config)
        logger.info("Registered processors: %s", ", ".join(registered))
        logger.info("Runtime check completed")
        return 0

    return await run_runtime(config, run_seconds=args.run_seconds)


def cli_main() -> None:
    raise SystemExit(asyncio.run(run_from_cli()))


if __name__ == "__main__":
    cli_main()
