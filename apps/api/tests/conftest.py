from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
import types

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

if "tenacity" not in sys.modules:
    tenacity = types.ModuleType("tenacity")

    def retry(*args, **kwargs):
        def decorator(fn):
            return fn

        return decorator

    def retry_if_exception_type(*args, **kwargs):
        return None

    def stop_after_attempt(*args, **kwargs):
        return None

    def wait_exponential(*args, **kwargs):
        return None

    tenacity.retry = retry
    tenacity.retry_if_exception_type = retry_if_exception_type
    tenacity.stop_after_attempt = stop_after_attempt
    tenacity.wait_exponential = wait_exponential
    sys.modules["tenacity"] = tenacity

from app.database import Base
from app.dependencies import get_current_user
from app.main import app
import app.database as database_module
import app.dependencies as dependencies_module
import app.main as main_module


@pytest.fixture
def user():
    return SimpleNamespace(id=101, username="user_a", role="user", company_id=None)


@pytest.fixture
def admin():
    return SimpleNamespace(id=1, username="admin", role="admin", company_id=None)


@pytest.fixture
def db_factory(tmp_path, monkeypatch):
    db_path = tmp_path / "scheduler-test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    monkeypatch.setattr(database_module, "engine", engine)
    monkeypatch.setattr(database_module, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(dependencies_module, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(main_module, "engine", engine)
    monkeypatch.setattr(main_module, "SessionLocal", TestingSessionLocal)

    Base.metadata.create_all(bind=engine)
    yield TestingSessionLocal
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(db_factory):
    session = db_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def api_client(db_factory):
    app.dependency_overrides.clear()
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def as_user(user):
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        yield user
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def as_admin(admin):
    app.dependency_overrides[get_current_user] = lambda: admin
    try:
        yield admin
    finally:
        app.dependency_overrides.clear()
