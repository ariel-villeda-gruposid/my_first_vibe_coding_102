import uuid
from datetime import datetime, timezone, timedelta


def make_vehicle_payload(plate="AB123", model="Model-X", year=2020, type_="SEDAN", fuel_type="GASOLINE"):
    return {
        "plate_number": plate,
        "model": model,
        "year": year,
        "type": type_,
        "fuel_type": fuel_type,
    }


def test_create_vehicle_success(client, auth_headers):
    """POST /vehicles - valid payload -> 201 and normalized plate, timestamps present"""
    payload = make_vehicle_payload(plate=" ab123 ")
    r = client.post("/vehicles", json=payload, headers=auth_headers)
    assert r.status_code == 201
    body = r.json()
    assert body.get("plate_number") == "AB123"
    assert "created_at" in body and "updated_at" in body


def test_create_vehicle_duplicate_plate_conflict(client, auth_headers):
    """Duplicate plates (differing by case/whitespace) return 409 DUPLICATE_PLATE"""
    payload = make_vehicle_payload(plate="xy999")
    r1 = client.post("/vehicles", json=payload, headers=auth_headers)
    assert r1.status_code == 201

    # Attempt duplicate with different casing/whitespace
    payload2 = make_vehicle_payload(plate=" XY999 ")
    r2 = client.post("/vehicles", json=payload2, headers=auth_headers)
    assert r2.status_code == 409
    err = r2.json()
    assert err["success"] is False
    assert err["error"]["code"] in ("DUPLICATE_PLATE", "DUPLICATE_VEHICLE")


def test_create_vehicle_invalid_plate_422(client, auth_headers):
    """Invalid plate (contains whitespace or non-alphanumeric) -> 422 with per-field details"""
    payload = make_vehicle_payload(plate="ABC 123")
    r = client.post("/vehicles", json=payload, headers=auth_headers)
    assert r.status_code == 422
    err = r.json()
    assert err["success"] is False
    assert "plate_number" in err["error"]["details"]


def test_get_vehicle_not_found_404(client, auth_headers):
    """GET unknown vehicle -> 404 VEHICLE_NOT_FOUND"""
    vid = str(uuid.uuid4())
    r = client.get(f"/vehicles/{vid}", headers=auth_headers)
    assert r.status_code == 404
    err = r.json()
    assert err["error"]["code"] == "VEHICLE_NOT_FOUND"


def test_get_vehicle_success(client, auth_headers):
    """Create then GET vehicle returns expected fields"""
    payload = make_vehicle_payload(plate="zz100")
    r = client.post("/vehicles", json=payload, headers=auth_headers)
    assert r.status_code == 201
    created = r.json()
    vid = created["id"]

    g = client.get(f"/vehicles/{vid}", headers=auth_headers)
    assert g.status_code == 200
    body = g.json()
    assert body["id"] == vid
    assert body["plate_number"] == "ZZ100"


def test_patch_vehicle_requires_if_match_and_updates(client, auth_headers):
    """PATCH /vehicles requires If-Match ETag and updates fields on success"""
    payload = make_vehicle_payload(plate="pt1")
    r = client.post("/vehicles", json=payload, headers=auth_headers)
    assert r.status_code == 201
    created = r.json()
    vid = created["id"]

    # Attempt patch without If-Match -> expect 412 or 409 (concurrency policy)
    patch = {"model": "Model-Updated"}
    r_no_etag = client.patch(f"/vehicles/{vid}", json=patch, headers=auth_headers)
    assert r_no_etag.status_code in (400, 409, 412)

    # When providing If-Match header (spec requires ETag/If-Match), expect 200
    # In TDD, server must return an ETag on GET; we simulate by fetching and using returned ETag header
    get_r = client.get(f"/vehicles/{vid}", headers=auth_headers)
    etag = get_r.headers.get("ETag")
    if etag:
        r2 = client.patch(f"/vehicles/{vid}", json=patch, headers={**auth_headers, "If-Match": etag})
        assert r2.status_code == 200
        body = r2.json()
        assert body["model"] == "Model-Updated"


def test_change_status_to_inactive_when_assigned_is_conflict(client, auth_headers):
    """Changing vehicle status to INACTIVE while assigned should return 409"""
    # Create vehicle
    payload = make_vehicle_payload(plate="ASSIGN1")
    r = client.post("/vehicles", json=payload, headers=auth_headers)
    assert r.status_code == 201
    vehicle = r.json()
    vid = vehicle["id"]

    # Create driver
    d_payload = {"name": "John Doe", "license_number": "LN123", "contact_number": "+15551234567"}
    rd = client.post("/drivers", json=d_payload, headers=auth_headers)
    assert rd.status_code == 201
    driver = rd.json()
    did = driver["id"]

    # Create assignment linking them (ongoing)
    now = datetime.now(timezone.utc).isoformat()
    assign_payload = {"driver_id": did, "vehicle_id": vid, "start_datetime": now}
    ra = client.post("/assignments", json=assign_payload, headers=auth_headers)
    assert ra.status_code == 201

    # Attempt to change status to INACTIVE -> expect 409 with VEHICLE_HAS_ACTIVE_ASSIGNMENTS or similar
    patch = {"status": "INACTIVE"}
    # Get ETag
    etag = client.get(f"/vehicles/{vid}", headers=auth_headers).headers.get("ETag")
    headers = {**auth_headers}
    if etag:
        headers["If-Match"] = etag
    r_change = client.patch(f"/vehicles/{vid}", json=patch, headers=headers)
    assert r_change.status_code == 409
    err = r_change.json()
    assert err["error"]["code"] in ("VEHICLE_HAS_ACTIVE_ASSIGNMENTS", "CONFLICT")


def test_delete_vehicle_only_when_not_assigned(client, auth_headers):
    """DELETE vehicle with active assignment -> 409; after closing assignment -> 204"""
    payload = make_vehicle_payload(plate="DELTEST")
    r = client.post("/vehicles", json=payload, headers=auth_headers)
    assert r.status_code == 201
    vehicle = r.json()
    vid = vehicle["id"]

    # create driver and assignment
    d_payload = {"name": "Jane", "license_number": "LNX1", "contact_number": "+15559990000"}
    rd = client.post("/drivers", json=d_payload, headers=auth_headers)
    assert rd.status_code == 201
    did = rd.json()["id"]

    now = datetime.now(timezone.utc).isoformat()
    ra = client.post("/assignments", json={"driver_id": did, "vehicle_id": vid, "start_datetime": now}, headers=auth_headers)
    assert ra.status_code == 201

    # attempt delete -> 409
    etag = client.get(f"/vehicles/{vid}", headers=auth_headers).headers.get("ETag")
    headers = {**auth_headers}
    if etag:
        headers["If-Match"] = etag
    rdel = client.delete(f"/vehicles/{vid}", headers=headers)
    assert rdel.status_code == 409

    # Close assignment (PATCH assignment end_datetime = now)
    assign_id = ra.json()["id"]
    r_close = client.patch(f"/assignments/{assign_id}", json={"end_datetime": datetime.now(timezone.utc).isoformat()}, headers=headers)
    # allow either 200 or 204 depending on implementation
    assert r_close.status_code in (200, 204)

    # Now delete should succeed
    etag2 = client.get(f"/vehicles/{vid}", headers=auth_headers).headers.get("ETag")
    headers2 = {**auth_headers}
    if etag2:
        headers2["If-Match"] = etag2
    rdel2 = client.delete(f"/vehicles/{vid}", headers=headers2)
    assert rdel2.status_code == 204


def test_list_vehicles_pagination(client, auth_headers):
    """Create multiple vehicles and verify pagination fields in list response"""
    # create 3 vehicles
    for i in range(3):
        payload = make_vehicle_payload(plate=f"LP{i}")
        r = client.post("/vehicles", json=payload, headers=auth_headers)
        assert r.status_code == 201

    r_list = client.get("/vehicles?limit=2&skip=0", headers=auth_headers)
    assert r_list.status_code == 200
    body = r_list.json()
    assert "pagination" in body and "total" in body["pagination"] and "has_more" in body["pagination"]
