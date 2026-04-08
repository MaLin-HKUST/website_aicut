"""Scheduler 模块 - 任务调度核心

F10+F11 - 调度器核心和 FCFS 策略
"""

__all__ = [
    "SchedulerService",
]


def __getattr__(name: str):
    if name == "SchedulerService":
        from apps.scheduler.scheduler_service import SchedulerService

        return SchedulerService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
