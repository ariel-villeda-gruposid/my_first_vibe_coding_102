from fastapi import APIRouter, HTTPException, Header, Request, Response, status, Depends
from typing import Optional
from uuid import uuid4
from datetime import datetime, timezone

from app.schemas import VehicleCreate, Vehicle
from app.storage import store
from app.utils import now_utc_iso, make_etag, normalize_plate, serialize_datetime

router = APIRouter()


def require_auth(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return authorization


@router.get("/vehicles")
def list_vehicles(request: Request, limit: int = 50, skip: int = 0, status: Optional[str] = None, include_deleted: bool = False, auth=Depends(require_auth)):
    all_vehicles = [v for v in store.vehicles.values() if include_deleted or not v.get("deleted")]
    if status:
        all_vehicles = [v for v in all_vehicles if v.get("status") == status]
    total = len(all_vehicles)
    sliced = all_vehicles[skip: skip + limit]
    data = []
    for v in sliced:
        item = {**v}
        item["created_at"] = serialize_datetime(item["created_at"])
        item["updated_at"] = serialize_datetime(item["updated_at"])
        data.append(item)
    has_more = skip + len(sliced) < total
    return {"success": True, "data": data, "pagination": {"total": total, "limit": limit, "skip": skip, "has_more": has_more}, "meta": {"timestamp": datetime.now(timezone.utc).isoformat(), "request_id": getattr(request.state, 'request_id', None), "correlation_id": getattr(request.state, 'correlation_id', None)}}


@router.post("/vehicles", status_code=201)
def create_vehicle(payload: VehicleCreate, auth=Depends(require_auth)):
    plate_norm = normalize_plate(payload.plate_number)
    # validate alnum/no whitespace already in schema validator
    if store.find_vehicle_by_plate(plate_norm):
        raise HTTPException(status_code=409, detail={"code": "DUPLICATE_PLATE", "message": "Plate already exists"})
    vid = str(uuid4())
    now = datetime.now(timezone.utc)
    vehicle = {
        "id": vid,
        "plate_number": plate_norm,
        "model": payload.model.strip(),
        "year": payload.year,
        "type": payload.type,
        "fuel_type": payload.fuel_type,
        "status": payload.status or "ACTIVE",
        "created_at": now,
        "updated_at": now,
        "deleted": False,
    }
    store.add_vehicle(vehicle)
    # prepare response
    resp = {**vehicle}
    # ISO format for datetimes
    resp["created_at"] = serialize_datetime(resp["created_at"])
    resp["updated_at"] = serialize_datetime(resp["updated_at"])
    return resp

@router.get("/vehicles/{vid}")
def get_vehicle(vid: str, response: Response, auth=Depends(require_auth)):
    v = store.get_vehicle(vid)
    if not v or v.get("deleted"):
        raise HTTPException(status_code=404, detail={"code": "VEHICLE_NOT_FOUND", "message": "Vehicle not found"})
    resp = {**v}
    resp["created_at"] = serialize_datetime(resp["created_at"])
    resp["updated_at"] = serialize_datetime(resp["updated_at"])
    etag = make_etag(resp["updated_at"])
    response.headers["ETag"] = etag
    return resp


@router.patch("/vehicles/{vid}")
def patch_vehicle(vid: str, payload: dict, if_match: Optional[str] = Header(None, alias="If-Match"), auth=Depends(require_auth)):
    # Require If-Match header
    if if_match is None:
        raise HTTPException(status_code=412, detail={"code": "MISSING_IF_MATCH", "message": "If-Match header required"})
    v = store.get_vehicle(vid)
    if not v or v.get("deleted"):
        raise HTTPException(status_code=404, detail={"code": "VEHICLE_NOT_FOUND", "message": "Vehicle not found"})
    current_etag = make_etag(serialize_datetime(v["updated_at"]))
    if if_match != current_etag:
        raise HTTPException(status_code=409, detail={"code": "CONCURRENCY_CONFLICT", "message": "ETag mismatch"})
    # Business rule: cannot set to INACTIVE or MAINTENANCE if assigned
    new_status = payload.get("status")
    if new_status in ("INACTIVE", "MAINTENANCE"):
        active_assigns = store.list_active_assignments_for_vehicle(vid)
        if active_assigns:
            raise HTTPException(status_code=409, detail={"code": "VEHICLE_HAS_ACTIVE_ASSIGNMENTS", "message": "Vehicle has active assignments"})
    # handle plate change
    if "plate_number" in payload:
        plate_norm = normalize_plate(payload.get("plate_number"))
        existing = store.find_vehicle_by_plate(plate_norm)
        if existing and existing["id"] != vid:
            raise HTTPException(status_code=409, detail={"code": "DUPLICATE_PLATE", "message": "Plate already exists"})
        v["plate_number"] = plate_norm
    for field in ("model", "year", "type", "fuel_type", "status"):
        if field in payload:
            v[field] = payload[field]
    v["updated_at"] = datetime.now(timezone.utc)
    # Persist updates to MongoDB
    updates = {k: v_val for k, v_val in v.items() if k not in ("created_at", "deleted")}
    resp = store.update_vehicle(vid, updates)
    if resp:
        resp["created_at"] = serialize_datetime(resp["created_at"])
        resp["updated_at"] = serialize_datetime(resp["updated_at"])
    return resp


@router.delete("/vehicles/{vid}", status_code=204)
def delete_vehicle(vid: str, if_match: Optional[str] = Header(None, alias="If-Match"), auth=Depends(require_auth)):
    if if_match is None:
        raise HTTPException(status_code=412, detail={"code": "MISSING_IF_MATCH", "message": "If-Match header required"})
    v = store.get_vehicle(vid)
    if not v or v.get("deleted"):
        raise HTTPException(status_code=404, detail={"code": "VEHICLE_NOT_FOUND", "message": "Vehicle not found"})
    # check active assignments
    active = store.list_active_assignments_for_vehicle(vid)
    if active:
        raise HTTPException(status_code=409, detail={"code": "VEHICLE_HAS_ACTIVE_ASSIGNMENTS", "message": "Vehicle has active assignments"})
    store.soft_delete_vehicle(vid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
