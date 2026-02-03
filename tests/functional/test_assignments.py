from datetime import datetime, timezone, timedelta
import time
import uuid


def test_create_assignment_success(client, auth_headers):
    dv = {"plate_number": "AS1", "model": "X", "year": 2020, "type": "SEDAN", "fuel_type": "GASOLINE"}
    rv = client.post("/vehicles", json=dv, headers=auth_headers)
    assert rv.status_code == 201
    vid = rv.json()["id"]

    d = {"name": "Driver A", "license_number": "ASD1", "contact_number": "+15550009999"}
    rd = client.post("/drivers", json=d, headers=auth_headers)
    assert rd.status_code == 201
    did = rd.json()["id"]

    now = datetime.now(timezone.utc).isoformat()
    r = client.post("/assignments", json={"driver_id": did, "vehicle_id": vid, "start_datetime": now}, headers=auth_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["driver_id"] == did and body["vehicle_id"] == vid


def test_create_assignment_with_suspended_driver_409(client, auth_headers):
    dv = {"plate_number": "AS2", "model": "X", "year": 2020, "type": "SEDAN", "fuel_type": "GASOLINE"}
    rv = client.post("/vehicles", json=dv, headers=auth_headers)
    vid = rv.json()["id"]

    d = {"name": "Driver B", "license_number": "LSUSP", "contact_number": "+15550001112"}
    rd = client.post("/drivers", json=d, headers=auth_headers)
    did = rd.json()["id"]

    # Suspend driver via PATCH (requires If-Match)
    g = client.get(f"/drivers/{did}", headers=auth_headers)
    etag = g.headers.get("ETag")
    headers = {**auth_headers}
    if etag:
        headers["If-Match"] = etag
    r_patch = client.patch(f"/drivers/{did}", json={"status": "SUSPENDED"}, headers=headers)
    assert r_patch.status_code in (200, 204)

    now = datetime.now(timezone.utc).isoformat()
    r = client.post("/assignments", json={"driver_id": did, "vehicle_id": vid, "start_datetime": now}, headers=auth_headers)
    assert r.status_code == 409
    err = r.json()
    assert err["error"]["code"] == "DRIVER_SUSPENDED"


def test_create_assignment_with_inactive_vehicle_409(client, auth_headers):
    dv = {"plate_number": "AS3", "model": "X", "year": 2020, "type": "SEDAN", "fuel_type": "GASOLINE"}
    rv = client.post("/vehicles", json=dv, headers=auth_headers)
    vid = rv.json()["id"]

    d = {"name": "Driver C", "license_number": "LIV", "contact_number": "+15550001113"}
    rd = client.post("/drivers", json=d, headers=auth_headers)
    did = rd.json()["id"]

    # Set vehicle to INACTIVE
    g = client.get(f"/vehicles/{vid}", headers=auth_headers)
    etag = g.headers.get("ETag")
    headers = {**auth_headers}
    if etag:
        headers["If-Match"] = etag
    r_patch = client.patch(f"/vehicles/{vid}", json={"status": "INACTIVE"}, headers=headers)
    # Expect 409 because vehicle may be unassigned, in our case it's unassigned so it should succeed
    assert r_patch.status_code in (200, 204)

    now = datetime.now(timezone.utc).isoformat()
    r = client.post("/assignments", json={"driver_id": did, "vehicle_id": vid, "start_datetime": now}, headers=auth_headers)
    assert r.status_code == 409
    err = r.json()
    assert err["error"]["code"] == "VEHICLE_INACTIVE"


def test_overlapping_assignment_conflict(client, auth_headers):
    dv = {"plate_number": "AS4", "model": "X", "year": 2020, "type": "SEDAN", "fuel_type": "GASOLINE"}
    rv = client.post("/vehicles", json=dv, headers=auth_headers)
    vid = rv.json()["id"]

    d = {"name": "Driver D", "license_number": "LAP1", "contact_number": "+15550001114"}
    rd = client.post("/drivers", json=d, headers=auth_headers)
    did = rd.json()["id"]

    now = datetime.now(timezone.utc).isoformat()
    r1 = client.post("/assignments", json={"driver_id": did, "vehicle_id": vid, "start_datetime": now}, headers=auth_headers)
    assert r1.status_code == 201

    # Attempt overlapping assignment for same driver
    r2 = client.post("/assignments", json={"driver_id": did, "vehicle_id": vid, "start_datetime": now}, headers=auth_headers)
    assert r2.status_code == 409
    err = r2.json()
    assert err["error"]["code"] in ("DRIVER_ALREADY_ASSIGNED", "VEHICLE_ALREADY_ASSIGNED", "OVERLAPPING_ASSIGNMENT")


def test_assignment_notes_length_validation(client, auth_headers):
    dv = {"plate_number": "AS5", "model": "X", "year": 2020, "type": "SEDAN", "fuel_type": "GASOLINE"}
    rv = client.post("/vehicles", json=dv, headers=auth_headers)
    vid = rv.json()["id"]

    d = {"name": "Driver E", "license_number": "LNT1", "contact_number": "+15550001115"}
    rd = client.post("/drivers", json=d, headers=auth_headers)
    did = rd.json()["id"]

    long_notes = "a" * 200
    now = datetime.now(timezone.utc).isoformat()
    r = client.post("/assignments", json={"driver_id": did, "vehicle_id": vid, "start_datetime": now, "notes": long_notes}, headers=auth_headers)
    assert r.status_code == 422
    err = r.json()
    assert err["error"]["code"] == "VALIDATION_ERROR"


def test_delete_active_assignment_autoclose(client, auth_headers):
    dv = {"plate_number": "AS6", "model": "X", "year": 2020, "type": "SEDAN", "fuel_type": "GASOLINE"}
    rv = client.post("/vehicles", json=dv, headers=auth_headers)
    vid = rv.json()["id"]

    d = {"name": "Driver F", "license_number": "LNF1", "contact_number": "+15550001116"}
    rd = client.post("/drivers", json=d, headers=auth_headers)
    did = rd.json()["id"]

    now = datetime.now(timezone.utc).isoformat()
    r = client.post("/assignments", json={"driver_id": did, "vehicle_id": vid, "start_datetime": now}, headers=auth_headers)
    assert r.status_code == 201
    aid = r.json()["id"]

    # Delete should auto-close and return 204
    rdel = client.delete(f"/assignments/{aid}", headers=auth_headers)
    assert rdel.status_code == 204

    # Ensure assignment no longer exists
    g = client.get(f"/assignments/{aid}", headers=auth_headers)
    assert g.status_code == 404


def test_assignment_error_branches(client, auth_headers):
    # missing driver
    dv = {"plate_number": "ABX1", "model": "X", "year": 2020, "type": "SEDAN", "fuel_type": "GASOLINE"}
    rv = client.post("/vehicles", json=dv, headers=auth_headers)
    vid = rv.json()["id"]
    r = client.post("/assignments", json={"driver_id": "00000000-0000-0000-0000-000000000000", "vehicle_id": vid, "start_datetime": datetime.now(timezone.utc).isoformat()}, headers=auth_headers)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "DRIVER_NOT_FOUND"

    # missing vehicle
    rd = client.post("/drivers", json={"name": "X", "license_number": "ZL1", "contact_number": "+15550001117"}, headers=auth_headers)
    did = rd.json()["id"]
    r2 = client.post("/assignments", json={"driver_id": did, "vehicle_id": "00000000-0000-0000-0000-000000000000", "start_datetime": datetime.now(timezone.utc).isoformat()}, headers=auth_headers)
    assert r2.status_code == 404
    assert r2.json()["error"]["code"] == "VEHICLE_NOT_FOUND"


def test_patch_assignment_end_datetime_parsing_and_delete_not_found(client, auth_headers):
    dv = {"plate_number": "AXP1", "model": "X", "year": 2020, "type": "SEDAN", "fuel_type": "GASOLINE"}
    rv = client.post("/vehicles", json=dv, headers=auth_headers)
    vid = rv.json()["id"]
    d = {"name": "Driver G", "license_number": "LPG1", "contact_number": "+15550001118"}
    rd = client.post("/drivers", json=d, headers=auth_headers)
    did = rd.json()["id"]
    now = datetime.now(timezone.utc).isoformat()
    r = client.post("/assignments", json={"driver_id": did, "vehicle_id": vid, "start_datetime": now}, headers=auth_headers)
    aid = r.json()["id"]

    # patch with end_datetime as ISO string
    # MongoDB stores with millisecond precision, so truncate microseconds
    now_dt = datetime.now(timezone.utc)
    now_dt_truncated = now_dt.replace(microsecond=(now_dt.microsecond // 1000) * 1000)
    end_ts = now_dt_truncated.isoformat()
    rp = client.patch(f"/assignments/{aid}", json={"end_datetime": end_ts}, headers=auth_headers)
    assert rp.status_code == 200
    assert rp.json()["end_datetime"] == end_ts

    # delete nonexistent assignment
    rdel = client.delete(f"/assignments/{str(uuid.uuid4())}", headers=auth_headers)
    assert rdel.status_code == 404
