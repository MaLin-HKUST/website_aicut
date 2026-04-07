#!/usr/bin/env python3
"""
PostgreSQL to SQLite Migration Script

Usage:
    # Migrate from PostgreSQL
    python scripts/migrate_pg_to_sqlite.py --pg-url postgresql+psycopg://scheduler:scheduler@localhost:5432/scheduler --sqlite-path ./data/website_aicut.db

    # Initialize fresh SQLite database
    python scripts/migrate_pg_to_sqlite.py --sqlite-path ./data/website_aicut.db
"""

import argparse
import os
import sys
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def init_sqlite_db(sqlite_path: str, admin_username: str = "admin", admin_password: str = "Malin123456"):
    """Initialize a fresh SQLite database with default data."""
    from app.database import Base, SessionLocal, engine
    from app.models import Company, User
    from app.security import hash_password

    # Ensure directory exists
    os.makedirs(os.path.dirname(os.path.abspath(sqlite_path)) or ".", exist_ok=True)

    # Remove existing database if present
    if os.path.exists(sqlite_path):
        print(f"Removing existing database: {sqlite_path}")
        os.remove(sqlite_path)

    # Create all tables
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Create admin user
        print(f"Creating admin user: {admin_username}")
        admin_user = User(
            username=admin_username,
            password_hash=hash_password(admin_password),
            role="admin",
            company_id=None,
            user_name="管理员",
            status="active",
        )
        db.add(admin_user)
        db.commit()
        print(f"Admin user created with ID: {admin_user.id}")

        print(f"\nSQLite database initialized at: {sqlite_path}")
        print(f"Admin login: {admin_username} / {admin_password}")
        return True
    finally:
        db.close()


def migrate_from_postgres(pg_url: str, sqlite_path: str):
    """Migrate data from PostgreSQL to SQLite."""
    from sqlalchemy import create_engine, select, text
    from sqlalchemy.orm import Session

    # Ensure directory exists
    os.makedirs(os.path.dirname(os.path.abspath(sqlite_path)) or ".", exist_ok=True)

    # Remove existing SQLite database
    if os.path.exists(sqlite_path):
        print(f"Removing existing database: {sqlite_path}")
        os.remove(sqlite_path)

    # Connect to PostgreSQL
    print(f"Connecting to PostgreSQL: {pg_url}")
    pg_engine = create_engine(pg_url)

    # Create SQLite database with new schema
    from app.database import Base, engine as sqlite_engine

    print("Creating SQLite tables with new schema...")
    Base.metadata.create_all(bind=sqlite_engine)

    pg_db = Session(pg_engine)
    sqlite_db = Session(sqlite_engine)

    try:
        today = datetime.now().strftime("%Y-%m-%d")

        # Migrate companies
        print("Migrating companies...")
        from app.models import Company
        companies = pg_db.execute(text("SELECT * FROM companies")).mappings().all()
        for row in companies:
            company = Company(
                id=row["id"],
                name=row["name"],
                created_at=row["created_at"],
                monthly_video_quota=0,
                monthly_video_remaining=0,
                billing_cycle_start_date=today,
                tts_enabled=False,
                ai_voice_monthly_usage=0,
                status="active",
            )
            sqlite_db.add(company)
        sqlite_db.commit()
        print(f"  Migrated {len(companies)} companies")

        # Migrate users
        print("Migrating users...")
        from app.models import User
        users = pg_db.execute(text("SELECT * FROM users")).mappings().all()
        for row in users:
            user = User(
                id=row["id"],
                username=row["username"],
                password_hash=row["password_hash"],
                role=row["role"],
                company_id=row.get("company_id"),
                created_at=row["created_at"],
                status="active",
            )
            sqlite_db.add(user)
        sqlite_db.commit()
        print(f"  Migrated {len(users)} users")

        # Migrate materials
        print("Migrating materials...")
        from app.models import Material
        materials = pg_db.execute(text("SELECT * FROM materials")).mappings().all()
        for row in materials:
            material = Material(
                id=row["id"],
                name=row["name"],
                company_id=row["company_id"],
                remark=row.get("remark"),
                created_at=row["created_at"],
            )
            sqlite_db.add(material)
        sqlite_db.commit()
        print(f"  Migrated {len(materials)} materials")

        # Migrate sessions
        print("Migrating sessions...")
        from app.models import Session
        sessions = pg_db.execute(text("SELECT * FROM sessions")).mappings().all()
        for row in sessions:
            session = Session(
                id=row["id"],
                token=row["token"],
                user_id=row["user_id"],
                created_at=row["created_at"],
            )
            sqlite_db.add(session)
        sqlite_db.commit()
        print(f"  Migrated {len(sessions)} sessions")

        # Migrate user_usage_monthly
        print("Migrating user_usage_monthly...")
        from app.models import UserUsageMonthly
        usages = pg_db.execute(text("SELECT * FROM user_usage_monthly")).mappings().all()
        for row in usages:
            usage = UserUsageMonthly(
                id=row["id"],
                user_id=row["user_id"],
                year_month=row["year_month"],
                credits_used=row["credits_used"],
                credits_limit=row.get("credits_limit"),
                last_updated=row["last_updated"],
            )
            sqlite_db.add(usage)
        sqlite_db.commit()
        print(f"  Migrated {len(usages)} usage records")

        # Migrate scheduler_tasks
        print("Migrating scheduler_tasks...")
        from app.models import SchedulerTask
        tasks = pg_db.execute(text("SELECT * FROM scheduler_tasks")).mappings().all()
        for row in tasks:
            task = SchedulerTask(
                task_id=row["task_id"],
                user_id=row["user_id"],
                page_key=row["page_key"],
                task_type=row["task_type"],
                status=row["status"],
                assigned_worker_id=row.get("assigned_worker_id"),
                step_index=row["step_index"],
                step_total=row["step_total"],
                workspace_uri=row.get("workspace_uri"),
                input_payload=row.get("input_payload"),
                output_payload=row.get("output_payload"),
                updated_at=row["updated_at"],
                keep_until=row.get("keep_until"),
                needs_post=row["needs_post"],
                last_error_code=row.get("last_error_code"),
                last_error_message=row.get("last_error_message"),
                created_at=row["created_at"],
            )
            sqlite_db.add(task)
        sqlite_db.commit()
        print(f"  Migrated {len(tasks)} scheduler tasks")

        # Migrate scheduler_workers
        print("Migrating scheduler_workers...")
        from app.models import SchedulerWorker
        workers = pg_db.execute(text("SELECT * FROM scheduler_workers")).mappings().all()
        for row in workers:
            import json
            worker = SchedulerWorker(
                worker_id=row["worker_id"],
                worker_name=row["worker_name"],
                supported_task_types=json.loads(row["supported_task_types"]) if isinstance(row["supported_task_types"], str) else row["supported_task_types"] or [],
                status=row["status"],
                current_task_id=row.get("current_task_id"),
                heartbeat_at=row["heartbeat_at"],
                created_at=row["created_at"],
            )
            sqlite_db.add(worker)
        sqlite_db.commit()
        print(f"  Migrated {len(workers)} scheduler workers")

        # Migrate scheduler_alarms
        print("Migrating scheduler_alarms...")
        from app.models import SchedulerAlarm
        alarms = pg_db.execute(text("SELECT * FROM scheduler_alarms")).mappings().all()
        for row in alarms:
            alarm = SchedulerAlarm(
                id=row["id"],
                alarm_type=row["alarm_type"],
                task_id=row.get("task_id"),
                worker_id=row.get("worker_id"),
                current_state=row["current_state"],
                message=row["message"],
                handled=row["handled"],
                created_at=row["created_at"],
            )
            sqlite_db.add(alarm)
        sqlite_db.commit()
        print(f"  Migrated {len(alarms)} scheduler alarms")

        # Migrate smart_cut_tasks
        print("Migrating smart_cut_tasks...")
        from app.models import SmartCutTask
        cut_tasks = pg_db.execute(text("SELECT * FROM smart_cut_tasks")).mappings().all()
        for row in cut_tasks:
            task = SmartCutTask(
                id=row["id"],
                user_id=row["user_id"],
                status=row["status"],
                current_stage=row.get("current_stage"),
                error_stage=row.get("error_stage"),
                error_message=row.get("error_message"),
                prepared_video_key=row.get("prepared_video_key"),
                prepared_text_key=row.get("prepared_text_key"),
                original_video_url=row.get("original_video_url"),
                original_video_tos_key=row.get("original_video_tos_key"),
                reference_text_url=row.get("reference_text_url"),
                reference_text_tos_key=row.get("reference_text_tos_key"),
                analyze_script=row.get("analyze_script"),
                analyze_script_tos_key=row.get("analyze_script_tos_key"),
                asr_result_tos_key=row.get("asr_result_tos_key"),
                active_edit_id=row.get("active_edit_id"),
                finalize_source_edit_id=row.get("finalize_source_edit_id"),
                final_video_url=row.get("final_video_url"),
                final_video_tos_key=row.get("final_video_tos_key"),
                groundtruth_url=row.get("groundtruth_url"),
                groundtruth_tos_key=row.get("groundtruth_tos_key"),
                feed_to_ai=row.get("feed_to_ai", False),
                output_mode=row.get("output_mode"),
                last_scheduler_task_id=row.get("last_scheduler_task_id"),
                updated_at=row["updated_at"],
                created_at=row["created_at"],
            )
            sqlite_db.add(task)
        sqlite_db.commit()
        print(f"  Migrated {len(cut_tasks)} smart cut tasks")

        # Migrate smart_cut_edits
        print("Migrating smart_cut_edits...")
        from app.models import SmartCutEdit
        edits = pg_db.execute(text("SELECT * FROM smart_cut_edits")).mappings().all()
        for row in edits:
            edit = SmartCutEdit(
                id=row["id"],
                task_id=row["task_id"],
                edited_script=row["edited_script"],
                status=row["status"],
                audio_b_url=row.get("audio_b_url"),
                audio_b_tos_key=row.get("audio_b_tos_key"),
                edited_delay_cuts_tos_key=row.get("edited_delay_cuts_tos_key"),
                pause_cuts_on_original_tos_key=row.get("pause_cuts_on_original_tos_key"),
                error_message=row.get("error_message"),
                updated_at=row["updated_at"],
                created_at=row["created_at"],
            )
            sqlite_db.add(edit)
        sqlite_db.commit()
        print(f"  Migrated {len(edits)} smart cut edits")

        print(f"\nMigration complete! SQLite database at: {sqlite_path}")
        return True

    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        pg_db.close()
        sqlite_db.close()
        pg_engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="PostgreSQL to SQLite migration")
    parser.add_argument("--pg-url", help="PostgreSQL connection URL")
    parser.add_argument("--sqlite-path", required=True, help="SQLite database file path")
    parser.add_argument("--admin-username", default="admin", help="Admin username for fresh init")
    parser.add_argument("--admin-password", default="Malin123456", help="Admin password for fresh init")

    args = parser.parse_args()

    if args.pg_url:
        success = migrate_from_postgres(args.pg_url, args.sqlite_path)
    else:
        success = init_sqlite_db(args.sqlite_path, args.admin_username, args.admin_password)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
