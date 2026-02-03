import pytest
from pymongo import MongoClient
from app.storage.mongo import MongoStorage
from datetime import datetime, timezone
from uuid import uuid4


@pytest.fixture(scope="session")
def mongo_client():
    """Create and connect to test MongoDB."""
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
    yield client
    # cleanup
    client.drop_database("fleet_api_test")
    client.close()


@pytest.fixture
def test_db(mongo_client):
    """Get test database, cleared before each test."""
    db = mongo_client["fleet_api_test"]
    # Clear collections
    db.vehicles.delete_many({})
    db.drivers.delete_many({})
    db.assignments.delete_many({})
    yield db


@pytest.fixture
def mongo_storage(test_db):
    return MongoStorage(test_db)


def test_create_and_get_vehicle(mongo_storage):
    """Traceability: FUNC_VEHICLES_CREATE, FUNC_VEHICLES_GET"""
    vehicle = {
        "id": str(uuid4()),
        "plate_number": "ABC123",
        "model": "Tesla",
        "year": 2020,
        "type": "SEDAN",
        "fuel_type": "ELECTRIC",
        "status": "ACTIVE",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    result = mongo_storage.create_vehicle(vehicle)
    assert result["plate_number"] == "ABC123"

    fetched = mongo_storage.get_vehicle(vehicle["id"])
    assert fetched is not None
    assert fetched["plate_number"] == "ABC123"


def test_duplicate_plate_raises_error(mongo_storage, test_db):
    """Traceability: FUNC_VEHICLES_DUPLICATE_ERROR"""
    # Ensure indexes are created
    test_db["vehicles"].create_index("plate_number", unique=True, sparse=True)
    
    v1 = {
        "id": str(uuid4()),
        "plate_number": "DUP001",
        "model": "Car",
        "year": 2020,
        "type": "SEDAN",
        "fuel_type": "GASOLINE",
        "status": "ACTIVE",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    mongo_storage.create_vehicle(v1)

    v2 = v1.copy()
    v2["id"] = str(uuid4())
    with pytest.raises(ValueError, match="Duplicate"):
        mongo_storage.create_vehicle(v2)


def test_soft_delete_vehicle(mongo_storage):
    """Traceability: FUNC_VEHICLES_SOFT_DELETE"""
    vehicle = {
        "id": str(uuid4()),
        "plate_number": "SDEL",
        "model": "Car",
        "year": 2020,
        "type": "SEDAN",
        "fuel_type": "GASOLINE",
        "status": "ACTIVE",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    mongo_storage.create_vehicle(vehicle)
    mongo_storage.soft_delete_vehicle(vehicle["id"])

    # Soft-deleted should not be found by plate lookup
    found = mongo_storage.find_vehicle_by_plate("SDEL")
    assert found is None


def test_create_and_get_driver(mongo_storage):
    """Traceability: FUNC_DRIVERS_CREATE, FUNC_DRIVERS_GET"""
    driver = {
        "id": str(uuid4()),
        "name": "John Doe",
        "license_number": "LIC001",
        "contact_number": "+15551234567",
        "status": "ACTIVE",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    result = mongo_storage.create_driver(driver)
    assert result["name"] == "John Doe"

    fetched = mongo_storage.get_driver(driver["id"])
    assert fetched is not None
    assert fetched["license_number"] == "LIC001"


def test_create_and_get_assignment(mongo_storage):
    """Traceability: FUNC_ASSIGNMENTS_CREATE, FUNC_ASSIGNMENTS_GET"""
    did = str(uuid4())
    vid = str(uuid4())
    now = datetime.now(timezone.utc)
    
    assignment = {
        "id": str(uuid4()),
        "driver_id": did,
        "vehicle_id": vid,
        "start_datetime": now,
        "end_datetime": None,
        "notes": None,
        "created_at": now,
        "updated_at": now,
    }
    result = mongo_storage.create_assignment(assignment)
    assert result["driver_id"] == did

    fetched = mongo_storage.get_assignment(assignment["id"])
    assert fetched is not None


def test_list_active_assignments_for_vehicle(mongo_storage):
    """Traceability: FUNC_ASSIGNMENTS_ACTIVE_DETECTION"""
    vid = str(uuid4())
    now = datetime.now(timezone.utc)
    
    # Active (no end)
    a1 = {
        "id": str(uuid4()),
        "vehicle_id": vid,
        "driver_id": str(uuid4()),
        "start_datetime": now,
        "end_datetime": None,
        "created_at": now,
        "updated_at": now,
    }
    mongo_storage.create_assignment(a1)

    active = mongo_storage.list_active_assignments_for_vehicle(vid)
    assert len(active) == 1
    assert active[0]["id"] == a1["id"]


def test_update_vehicle(mongo_storage):
    """Traceability: FUNC_VEHICLES_UPDATE"""
    vehicle = {
        "id": str(uuid4()),
        "plate_number": "UPD001",
        "model": "Car",
        "year": 2020,
        "type": "SEDAN",
        "fuel_type": "GASOLINE",
        "status": "ACTIVE",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    mongo_storage.create_vehicle(vehicle)
    
    updated = mongo_storage.update_vehicle(vehicle["id"], {"status": "INACTIVE", "updated_at": datetime.now(timezone.utc)})
    assert updated["status"] == "INACTIVE"


def test_update_assignment(mongo_storage):
    """Traceability: FUNC_ASSIGNMENTS_UPDATE"""
    now = datetime.now(timezone.utc)
    assignment = {
        "id": str(uuid4()),
        "driver_id": str(uuid4()),
        "vehicle_id": str(uuid4()),
        "start_datetime": now,
        "end_datetime": None,
        "notes": None,
        "created_at": now,
        "updated_at": now,
    }
    mongo_storage.create_assignment(assignment)
    
    updated = mongo_storage.update_assignment(assignment["id"], {"notes": "Test", "updated_at": datetime.now(timezone.utc)})
    assert updated["notes"] == "Test"
