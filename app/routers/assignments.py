from fastapi import APIRouter, HTTPException, Depends, Response, status
from uuid import uuid4
from datetime import datetime, timezone
from typing import Optional

from app.schemas import AssignmentCreate
from app.storage import store
from app.utils import serialize_datetime, truncate_to_milliseconds

router = APIRouter()


from fastapi import Header, HTTPException

def require_auth(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Missing or invalid authentication"})
    return authorization


@router.post("/assignments", status_code=201)
def create_assignment(payload: AssignmentCreate, auth=Depends(require_auth)):
    # Check foreign keys
    driver = store.get_driver(payload.driver_id)
    if not driver or driver.get("deleted"):
        raise HTTPException(status_code=404, detail={"code": "DRIVER_NOT_FOUND", "message": "Driver not found"})
    vehicle = store.get_vehicle(payload.vehicle_id)
    if not vehicle or vehicle.get("deleted"):
        raise HTTPException(status_code=404, detail={"code": "VEHICLE_NOT_FOUND", "message": "Vehicle not found"})
    # Check statuses
    if driver.get("status") == "SUSPENDED":
        raise HTTPException(status_code=409, detail={"code": "DRIVER_SUSPENDED", "message": "Driver suspended"})
    if vehicle.get("status") in ("INACTIVE", "MAINTENANCE"):
        raise HTTPException(status_code=409, detail={"code": "VEHICLE_INACTIVE", "message": "Vehicle inactive or under maintenance"})
    # Check driver and vehicle active assignments
    da = store.list_active_assignments_for_driver(payload.driver_id)
    if da:
        raise HTTPException(status_code=409, detail={"code": "DRIVER_ALREADY_ASSIGNED", "message": "Driver already has an active assignment"})
    va = store.list_active_assignments_for_vehicle(payload.vehicle_id)
    if va:
        raise HTTPException(status_code=409, detail={"code": "VEHICLE_ALREADY_ASSIGNED", "message": "Vehicle already has an active assignment"})

    aid = str(uuid4())
    now = datetime.now(timezone.utc)
    assignment = {
        "id": aid,
        "driver_id": payload.driver_id,
        "vehicle_id": payload.vehicle_id,
        "start_datetime": payload.start_datetime,
        "end_datetime": payload.end_datetime,
        "notes": payload.notes.strip() if payload.notes else None,
        "created_at": now,
        "updated_at": now,
    }
    store.add_assignment(assignment)
    resp = {**assignment}
    resp["start_datetime"] = serialize_datetime(resp["start_datetime"])
    resp["end_datetime"] = serialize_datetime(resp["end_datetime"])
    resp["created_at"] = serialize_datetime(resp["created_at"])
    resp["updated_at"] = serialize_datetime(resp["updated_at"])
    return resp


@router.patch("/assignments/{aid}")
def patch_assignment(aid: str, payload: dict, auth=Depends(require_auth)):
    a = store.get_assignment(aid)
    if not a:
        raise HTTPException(status_code=404, detail={"code": "ASSIGNMENT_NOT_FOUND", "message": "Assignment not found"})
    # Only notes and end_datetime allowed
    updates = {}
    if "notes" in payload:
        notes = payload.get("notes")
        if notes is not None:
            notes = notes.rstrip()
            if len(notes) > 127:
                raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": "notes too long"})
        updates["notes"] = notes
    if "end_datetime" in payload:
        end = payload.get("end_datetime")
        if end is None:
            updates["end_datetime"] = None
        else:
            # parse
            if isinstance(end, str):
                end_dt = datetime.fromisoformat(end)
            else:
                end_dt = end
            # Truncate to milliseconds to match MongoDB precision
            end_dt = truncate_to_milliseconds(end_dt)
            updates["end_datetime"] = end_dt
    updates["updated_at"] = datetime.now(timezone.utc)
    resp = store.update_assignment(aid, updates)
    if resp:
        resp["start_datetime"] = serialize_datetime(resp["start_datetime"])
        resp["end_datetime"] = serialize_datetime(resp["end_datetime"])
        resp["created_at"] = serialize_datetime(resp["created_at"])
        resp["updated_at"] = serialize_datetime(resp["updated_at"])
    return resp


@router.get("/assignments/{aid}")
def get_assignment(aid: str, auth=Depends(require_auth)):
    a = store.get_assignment(aid)
    if not a:
        raise HTTPException(status_code=404, detail={"code": "ASSIGNMENT_NOT_FOUND", "message": "Assignment not found"})
    resp = {**a}
    resp["start_datetime"] = serialize_datetime(resp["start_datetime"])
    resp["end_datetime"] = serialize_datetime(resp["end_datetime"])
    resp["created_at"] = serialize_datetime(resp["created_at"])
    resp["updated_at"] = serialize_datetime(resp["updated_at"])
    return resp


@router.delete("/assignments/{aid}", status_code=204)
def delete_assignment(aid: str, auth=Depends(require_auth)):
    a = store.get_assignment(aid)
    if not a:
        raise HTTPException(status_code=404, detail={"code": "ASSIGNMENT_NOT_FOUND", "message": "Assignment not found"})
    # If active (end_datetime is None), auto-close it first
    now = datetime.now(timezone.utc)
    if a.get("end_datetime") is None:
        # Auto-close
        store.update_assignment(aid, {"end_datetime": now, "updated_at": now})
    # Then delete the assignment
    store.delete_assignment(aid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

    return Response(status_code=204)
