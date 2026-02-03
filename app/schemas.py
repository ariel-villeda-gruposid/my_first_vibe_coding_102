from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class VehicleCreate(BaseModel):
    plate_number: str
    model: str
    year: int
    type: str
    fuel_type: str
    status: Optional[str] = "ACTIVE"

    @field_validator("plate_number")
    def plate_must_be_alnum_no_space(cls, v: str):
        v2 = v.strip()
        if not v2.isalnum():
            raise ValueError("plate_number must be alphanumeric with no whitespace")
        if len(v2) > 10:
            raise ValueError("plate_number max length is 10")
        return v2

class Vehicle(BaseModel):
    id: str
    plate_number: str
    model: str
    year: int
    type: str
    fuel_type: str
    status: str
    created_at: datetime
    updated_at: datetime


class DriverCreate(BaseModel):
    name: str
    license_number: str
    contact_number: str
    status: Optional[str] = "ACTIVE"


class Driver(BaseModel):
    id: str
    name: str
    license_number: str
    contact_number: str
    status: str
    created_at: datetime
    updated_at: datetime


class AssignmentCreate(BaseModel):
    driver_id: str
    vehicle_id: str
    start_datetime: datetime
    end_datetime: Optional[datetime] = None
    notes: Optional[str] = None

    @field_validator("notes")
    def notes_length(cls, v: Optional[str]):
        if v is None:
            return v
        s = v.rstrip()
        if len(s) > 127:
            raise ValueError("notes must be <= 127 characters after trimming")
        return s


class Assignment(BaseModel):
    id: str
    driver_id: str
    vehicle_id: str
    start_datetime: datetime
    end_datetime: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
