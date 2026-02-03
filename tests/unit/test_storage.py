"""Unit tests for storage layer."""
# These tests validate basic storage interface behavior
# Note: MongoStorage is tested in integration tests with real MongoDB
# This file is kept for backward compatibility with the test suite

from app.storage.mongo import MongoStorage
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4


def make_vehicle(id_="v1", plate="ABC1"):
    now = datetime.now(timezone.utc)
    return {
        "id": id_,
        "plate_number": plate,
        "model": "Test",
        "year": 2020,
        "type": "SEDAN",
        "fuel_type": "GASOLINE",
        "status": "ACTIVE",
        "created_at": now,
        "updated_at": now,
        "deleted": False
    }


def make_assignment(id_="a1", vehicle_id="v1", driver_id="d1", end=None):
    now = datetime.now(timezone.utc)
    return {
        "id": id_,
        "vehicle_id": vehicle_id,
        "driver_id": driver_id,
        "start_datetime": now,
        "end_datetime": end,
        "notes": None,
        "created_at": now,
        "updated_at": now
    }


def test_mongo_storage_initialization():
    """Test that MongoStorage can be initialized with a mock database."""
    mock_db = MagicMock()
    storage = MongoStorage(mock_db)
    assert storage.db == mock_db


def test_mongo_storage_create_vehicle_handles_duplicate():
    """Test that create_vehicle raises ValueError on duplicate plate."""
    from pymongo.errors import DuplicateKeyError
    
    mock_db = MagicMock()
    mock_db.vehicles.insert_one.side_effect = DuplicateKeyError("E11000")
    
    storage = MongoStorage(mock_db)
    v = make_vehicle()
    
    try:
        storage.create_vehicle(v)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Duplicate" in str(e)


def test_mongo_storage_soft_delete():
    """Test soft delete functionality."""
    mock_db = MagicMock()
    mock_db.vehicles.find_one.return_value = None  # After soft delete, should not find
    
    storage = MongoStorage(mock_db)
    
    # Call soft_delete
    storage.soft_delete_vehicle("v1")
    
    # Verify it called update with deleted=True
    mock_db.vehicles.update_one.assert_called_once()
    call_args = mock_db.vehicles.update_one.call_args
    assert call_args[0][0] == {"id": "v1"}
    assert call_args[0][1]["$set"]["deleted"] is True
