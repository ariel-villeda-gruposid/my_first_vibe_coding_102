import pytest
from pydantic import ValidationError
from app.schemas import VehicleCreate, AssignmentCreate
from datetime import datetime


def test_vehicle_create_invalid_plate():
    with pytest.raises(ValidationError):
        VehicleCreate(plate_number="ABC 123", model="X", year=2020, type="SEDAN", fuel_type="GASOLINE")

    with pytest.raises(ValidationError):
        VehicleCreate(plate_number="TOO-LONG-PLATE-12345", model="X", year=2020, type="SEDAN", fuel_type="GASOLINE")


def test_assignment_notes_trimming_and_length():
    long = "a" * 200
    with pytest.raises(ValidationError):
        AssignmentCreate(driver_id="d", vehicle_id="v", start_datetime=datetime.now(), notes=long)
    # trimming should allow 127 chars
    valid = "a" * 127 + "   "
    a = AssignmentCreate(driver_id="d", vehicle_id="v", start_datetime=datetime.now(), notes=valid)
    assert a.notes == "a" * 127
