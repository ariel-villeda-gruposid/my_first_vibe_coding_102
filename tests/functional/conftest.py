import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def cleanup_mongo():
    """Clear MongoDB collections before each test."""
    from app.storage.mongo import get_db
    try:
        db = get_db()
        db.vehicles.delete_many({})
        db.drivers.delete_many({})
        db.assignments.delete_many({})
    except:
        # MongoDB might not be available during early test collection
        pass
    yield
    # Cleanup after test
    try:
        db = get_db()
        db.vehicles.delete_many({})
        db.drivers.delete_many({})
        db.assignments.delete_many({})
    except:
        pass


@pytest.fixture
def client():
    """Test client fixture expecting an ASGI app at `app.main:app`.

    Tests follow TDD: the app may not exist yet — creating tests first.
    """
    try:
        from app.main import app
    except Exception as exc:  # pragma: no cover - failing import is expected in TDD
        raise

    with TestClient(app) as client:
        yield client


@pytest.fixture
def auth_headers():
    # Placeholder token for tests; auth enforcement will be added in implementation
    return {"Authorization": "Bearer testtoken"}
