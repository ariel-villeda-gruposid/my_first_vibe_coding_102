from fastapi import APIRouter, Depends
from uuid import uuid4
from datetime import datetime, timezone
from typing import Optional

from app.schemas import DriverCreate
from app.storage import store
from app.utils import now_utc_iso

router = APIRouter()


from fastapi import Header, HTTPException

def require_auth(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Missing or invalid authentication"})
    return authorization


@router.post("/drivers", status_code=201)
def create_driver(payload: DriverCreate, auth=Depends(require_auth)):
    did = str(uuid4())
    now = datetime.now(timezone.utc)
    driver = {
        "id": did,
        "name": payload.name.strip(),
        "license_number": payload.license_number.strip().upper(),
        "contact_number": payload.contact_number.strip(),
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
