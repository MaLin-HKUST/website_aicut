"""A-scheduler runtime entrypoint.

This module turns the scheduler-center service into a real long-running
process with a stable CLI contract suitable for Docker commands.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
from typing import TYPE_CHECKING, Sequence

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from apps.scheduler.scheduler_service import SchedulerService

DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_CHECK_INTERVAL = 5


def build_parser() -> argparse.ArgumentParser:
    """Create the scheduler CLI parser."""
    parser = argparse.ArgumentParser(
        prog="python -m apps.scheduler.main",
        description="Run the A-machine scheduler-center service.",
    )
    parser.add_argument(
        "--check-interval",
        type=int,
        default=int(os.getenv("SCHEDULER_INTERVAL", str(DEFAULT_CHECK_INTERVAL))),
        help="Seconds between scheduler cycles. Defaults to SCHEDULER_INTERVAL or 5.",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("SCHEDULER_LOG_LEVEL", DEFAULT_LOG_LEVEL),
        help="Logging level. Defaults to SCHEDULER_LOG_LEVEL or INFO.",
    )
    parser.add_argument(
        "--database-url",
        help="Explicit scheduler database URL. Overrides SCHEDULER_DATABASE_URL and DATABASE_URL.",
    )
    parser.add_argument(
        "--allow-sqlite",
        action="store_true",
        help="Allow SQLite for local debugging. Production scheduler startup should use PostgreSQL.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single scheduler cycle and exit.",
    )
    return parser


def configure_logging(log_level: str) -> None:
    """Initialize process logging once."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def resolve_database_url(cli_database_url: str | None) -> str:
    """Resolve the scheduler database URL with explicit scheduler precedence."""
    database_url = (
        cli_database_url
        or os.getenv("SCHEDULER_DATABASE_URL")
        or os.getenv("DATABASE_URL")
    )
    if not database_url:
        raise RuntimeError(
            "Scheduler database URL is not configured. Set "
            "SCHEDULER_DATABASE_URL, DATABASE_URL, or pass --database-url."
        )
    return database_url


def validate_database_url(database_url: str, allow_sqlite: bool) -> None:
    """Reject accidental SQLite startup on the scheduler production path."""
    if not allow_sqlite and database_url.startswith("sqlite"):
        raise RuntimeError(
            "Scheduler center requires PostgreSQL by default. Configure "
            "SCHEDULER_DATABASE_URL to a PostgreSQL DSN or pass --allow-sqlite "
            "for local-only debugging."
        )


def mask_database_url(database_url: str) -> str:
    """Redact database credentials before logging."""
    if "@" not in database_url or "://" not in database_url:
        return database_url
    scheme, rest = database_url.split("://", 1)
    credentials, host_part = rest.split("@", 1)
    if ":" not in credentials:
        return f"{scheme}://***@{host_part}"
    username, _ = credentials.split(":", 1)
    return f"{scheme}://{username}:***@{host_part}"


def create_scheduler_service(
    database_url: str,
    check_interval: int,
) -> tuple["Session", "SchedulerService"]:
    """Create the scheduler runtime session and service."""
    os.environ["DATABASE_URL"] = database_url

    from configs.database import SessionLocal
    from apps.scheduler.scheduler_service import SchedulerService
    from apps.services.device_service import DeviceService

    session = SessionLocal()
    session.execute(text("SELECT 1"))
    service = SchedulerService(
        db_session=session,
        device_service=DeviceService(session),
        check_interval=check_interval,
    )
    return session, service


def install_signal_handlers(service: "SchedulerService") -> None:
    """Stop the scheduler loop on SIGINT/SIGTERM."""
    loop = asyncio.get_running_loop()

    def handle_signal(sig: signal.Signals) -> None:
        logging.getLogger(__name__).info("Received %s, stopping scheduler loop", sig.name)
        service.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal, sig)
        except NotImplementedError:
            signal.signal(sig, lambda *_args, current=sig: handle_signal(current))


async def run_service(args: argparse.Namespace) -> int:
    """Run the scheduler service with the parsed CLI arguments."""
    database_url = resolve_database_url(args.database_url)
    validate_database_url(database_url, allow_sqlite=args.allow_sqlite)

    logger = logging.getLogger(__name__)
    logger.info("Starting scheduler center with database %s", mask_database_url(database_url))

    session = None
    try:
        session, service = create_scheduler_service(
            database_url=database_url,
            check_interval=args.check_interval,
        )

        if args.once:
            stats = service.run_cycle()
            logger.info("Scheduler single cycle completed: %s", stats)
            return 0

        install_signal_handlers(service)
        await service.run_scheduler_loop()
        return 0
    finally:
        if session is not None:
            session.close()


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.log_level)
    try:
        return asyncio.run(run_service(args))
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Keyboard interrupt received, exiting")
        return 0
    except Exception as exc:
        logging.getLogger(__name__).error("Scheduler startup failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
