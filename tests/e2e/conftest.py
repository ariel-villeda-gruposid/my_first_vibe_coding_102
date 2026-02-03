"""E2E test configuration with real MongoDB backend."""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from app.main import app
from app.storage import store
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function", autouse=True)
def cleanup_db():
    """Clear database before and after each E2E test."""
    # Clear before test
    store.mongo.db.vehicles.delete_many({})
    store.mongo.db.drivers.delete_many({})
    store.mongo.db.assignments.delete_many({})
    yield
    # Clear after test
    store.mongo.db.vehicles.delete_many({})
    store.mongo.db.drivers.delete_many({})
    store.mongo.db.assignments.delete_many({})


@pytest.fixture
def client():
    """FastAPI test client with real MongoDB backend."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Standard authorization headers for API requests."""
    return {"Authorization": "Bearer test-token-12345"}
