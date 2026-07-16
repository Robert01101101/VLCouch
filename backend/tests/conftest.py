import os

# Set test environment before any app imports
os.environ["APP_ENV"] = "test"
os.environ["TEST_MODE"] = "true"

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel
from tests.fixtures.seed import seed_library

import app.db as db
from app import models  # noqa: F401
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / "test.db"
    posters_path = tmp_path / "posters"
    posters_path.mkdir(parents=True, exist_ok=True)

    db.override_engine_for_tests(db_path)
    SQLModel.metadata.drop_all(db.engine)
    db.init_db()

    app = create_app(lifespan_scan=False)
    with TestClient(app) as test_client:
        seed_data = seed_library()
        test_client.seed_data = seed_data
        yield test_client


@pytest.fixture
def empty_client(tmp_path):
    """Client with empty database (no seeded data)."""
    db_path = tmp_path / "test.db"
    posters_path = tmp_path / "posters"
    posters_path.mkdir(parents=True, exist_ok=True)

    db.override_engine_for_tests(db_path)
    SQLModel.metadata.drop_all(db.engine)
    db.init_db()

    app = create_app(lifespan_scan=False)
    with TestClient(app) as test_client:
        yield test_client
