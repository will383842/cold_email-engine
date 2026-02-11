"""Shared test fixtures — SQLite in-memory database with shared connection."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import get_db
from app.models import Base

# Single shared in-memory SQLite for all test connections
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test, drop after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db():
    """Yield a fresh DB session."""
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    """FastAPI test client with overridden DB and patched lifespan engine."""

    def _override_db():
        try:
            yield db
        finally:
            pass

    from app import main as main_module

    app = main_module.app
    app.dependency_overrides[get_db] = _override_db

    with patch.object(main_module, "engine", test_engine):
        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()


@pytest.fixture
def api_headers():
    """Headers with valid API key."""
    return {"X-API-Key": settings.API_KEY}
