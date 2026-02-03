from fastapi import APIRouter, Depends, Header, HTTPException, Response
from uuid import uuid4
from datetime import datetime, timezone
from typing import Optional
import re

from app.schemas import DriverCreate
from app.storage import store

router = APIRouter()


def require_auth(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Missing or invalid authentication"})
    return authorization


@router.post("/drivers", status_code=201)
def create_driver(payload: DriverCreate, auth=Depends(require_auth)):
    # validate contact number (simple E.164-ish check)
    phone = payload.contact_number.strip()
    if not re.match(r"^\+\d{7,15}$", phone):
        raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": "Invalid contact number", "details": {"contact_number": [{"code": "INVALID_PHONE", "message": "contact_number must be in international format with leading + and digits"}]}})
    license_norm = payload.license_number.strip().upper()
    existing = None
    for d in store.drivers.values():
        if d.get("license_number") == license_norm and not d.get("deleted"):
            existing = d
            break
    if existing:
        raise HTTPException(status_code=409, detail={"code": "DUPLICATE_LICENSE", "message": "License number already exists"})

    did = str(uuid4())
    now = datetime.now(timezone.utc)
    driver = {
        "id": did,
        "name": payload.name.strip(),
        "license_number": license_norm,
        "contact_number": phone,
        "status": payload.status or "ACTIVE",
        "created_at": now,
        "updated_at": now,
        "deleted": False,
    }
    store.add_driver(driver)
    resp = {**driver}
    resp["created_at"] = resp["created_at"].isoformat()
    resp["updated_at"] = resp["updated_at"].isoformat()
    return resp


@router.get("/drivers/{did}")
def get_driver(did: str, response: Response, auth=Depends(require_auth)):
    d = store.get_driver(did)
    if not d or d.get("deleted"):
        raise HTTPException(status_code=404, detail={"code": "DRIVER_NOT_FOUND", "message": "Driver not found"})
    resp = {**d}
    resp["created_at"] = resp["created_at"].isoformat()
    resp["updated_at"] = resp["updated_at"].isoformat()
    # ETag
    response.headers["ETag"] = f'"{resp["updated_at"]}"'
    return resp


@router.patch("/drivers/{did}")
def patch_driver(did: str, payload: dict, if_match: Optional[str] = Header(None, alias="If-Match"), auth=Depends(require_auth)):
    if if_match is None:
        raise HTTPException(status_code=412, detail={"code": "MISSING_IF_MATCH", "message": "If-Match header required"})
    d = store.get_driver(did)
    if not d or d.get("deleted"):
        raise HTTPException(status_code=404, detail={"code": "DRIVER_NOT_FOUND", "message": "Driver not found"})
    current_etag = f'"{d["updated_at"].isoformat()}"'
    if if_match != current_etag:
        raise HTTPException(status_code=409, detail={"code": "CONCURRENCY_CONFLICT", "message": "ETag mismatch"})
    # If changing status to SUSPENDED, ensure no active assignments
    new_status = payload.get("status")
    if new_status == "SUSPENDED":
        active = store.list_active_assignments_for_driver(did)
        if active:
            raise HTTPException(status_code=409, detail={"code": "DRIVER_HAS_ACTIVE_ASSIGNMENTS", "message": "Driver has active assignments"})
    # license change -> check duplicates
    if "license_number" in payload:
        lic = payload.get("license_number").strip().upper()
        for other in store.drivers.values():
            if other.get("license_number") == lic and other.get("id") != did and not other.get("deleted"):
                raise HTTPException(status_code=409, detail={"code": "DUPLICATE_LICENSE", "message": "License number already exists"})
        d["license_number"] = lic
    # apply other fields
    for field in ("name", "contact_number", "status"):
        if field in payload:
            if isinstance(payload[field], str):
                d[field] = payload[field].strip()
            else:
                d[field] = payload[field]
    d["updated_at"] = datetime.now(timezone.utc)
    # Persist updates to MongoDB
    updates = {k: v for k, v in d.items() if k not in ("created_at", "deleted")}
    resp = store.update_driver(did, updates)
    if resp:
        resp["created_at"] = resp["created_at"].isoformat()
        resp["updated_at"] = resp["updated_at"].isoformat()
    return resp


@router.delete("/drivers/{did}", status_code=204)
def delete_driver(did: str, if_match: Optional[str] = Header(None, alias="If-Match"), auth=Depends(require_auth)):
    if if_match is None:
        raise HTTPException(status_code=412, detail={"code": "MISSING_IF_MATCH", "message": "If-Match header required"})
    d = store.get_driver(did)
    if not d or d.get("deleted"):
        raise HTTPException(status_code=404, detail={"code": "DRIVER_NOT_FOUND", "message": "Driver not found"})
    active = store.list_active_assignments_for_driver(did)
    if active:
        raise HTTPException(status_code=409, detail={"code": "DRIVER_HAS_ACTIVE_ASSIGNMENTS", "message": "Driver has active assignments"})
    d["deleted"] = True
    return Response(status_code=204)
