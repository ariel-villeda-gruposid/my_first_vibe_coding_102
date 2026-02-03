from datetime import datetime, timezone


def make_driver_payload(name="Alice", license_number="LIC123", contact_number="+15550001111"):
    return {"name": name, "license_number": license_number, "contact_number": contact_number}


def test_create_driver_success(client, auth_headers):
    payload = make_driver_payload(license_number=" ln100 ")
    r = client.post("/drivers", json=payload, headers=auth_headers)
    assert r.status_code == 201
    body = r.json()
    # license normalized to uppercase and trimmed
    assert body["license_number"] == "LN100"
    assert "created_at" in body and "updated_at" in body


def test_create_driver_duplicate_license_conflict(client, auth_headers):
    payload = make_driver_payload(license_number="dup1")
    r1 = client.post("/drivers", json=payload, headers=auth_headers)
    assert r1.status_code == 201

    # attempt duplicate with different casing/whitespace
    payload2 = make_driver_payload(license_number=" DUP1 ")
    r2 = client.post("/drivers", json=payload2, headers=auth_headers)
    assert r2.status_code == 409
    err = r2.json()
    assert err["success"] is False
    assert err["error"]["code"] in ("DUPLICATE_LICENSE", "DUPLICATE_DRIVER")


def test_create_driver_invalid_contact_422(client, auth_headers):
    payload = make_driver_payload(contact_number="not-a-phone")
    r = client.post("/drivers", json=payload, headers=auth_headers)
    assert r.status_code == 422
    err = r.json()
    assert err["success"] is False
    assert "contact_number" in err["error"]["details"]


def test_suspend_driver_with_active_assignment_conflict(client, auth_headers):
    # create vehicle
    v_payload = {"plate_number": "SUSP1", "model": "X", "year": 2020, "type": "SEDAN", "fuel_type": "GASOLINE"}
    rv = client.post("/vehicles", json=v_payload, headers=auth_headers)
    assert rv.status_code == 201
    vid = rv.json()["id"]

    # create driver
    d_payload = make_driver_payload(license_number="LS1")
    rd = client.post("/drivers", json=d_payload, headers=auth_headers)
    assert rd.status_code == 201
    did = rd.json()["id"]

    # create assignment
    now = datetime.now(timezone.utc).isoformat()
    ra = client.post("/assignments", json={"driver_id": did, "vehicle_id": vid, "start_datetime": now}, headers=auth_headers)
    assert ra.status_code == 201

    # attempt to suspend driver
    # fetch ETag for driver (server should return one on GET)
    g = client.get(f"/drivers/{did}", headers=auth_headers)
    etag = g.headers.get("ETag")
    headers = {**auth_headers}
    if etag:
        headers["If-Match"] = etag
    r = client.patch(f"/drivers/{did}", json={"status": "SUSPENDED"}, headers=headers)
    assert r.status_code == 409
    err = r.json()
    assert err["error"]["code"] in ("DRIVER_HAS_ACTIVE_ASSIGNMENTS", "CONFLICT")


def test_delete_driver_only_when_not_assigned(client, auth_headers):
    d_payload = make_driver_payload(license_number="DELDRV")
    rd = client.post("/drivers", json=d_payload, headers=auth_headers)
    assert rd.status_code == 201
    did = rd.json()["id"]

    v_payload = {"plate_number": "VDEL1", "model": "M", "year": 2021, "type": "VAN", "fuel_type": "DIESEL"}
    rv = client.post("/vehicles", json=v_payload, headers=auth_headers)
    assert rv.status_code == 201
    vid = rv.json()["id"]

    now = datetime.now(timezone.utc).isoformat()
    ra = client.post("/assignments", json={"driver_id": did, "vehicle_id": vid, "start_datetime": now}, headers=auth_headers)
    assert ra.status_code == 201

    # attempt delete driver -> expect 409
    g = client.get(f"/drivers/{did}", headers=auth_headers)
    etag = g.headers.get("ETag")
    headers = {**auth_headers}
    if etag:
        headers["If-Match"] = etag
    rdel = client.delete(f"/drivers/{did}", headers=headers)
    assert rdel.status_code == 409

    # close assignment
    assign_id = ra.json()["id"]
    r_close = client.patch(f"/assignments/{assign_id}", json={"end_datetime": datetime.now(timezone.utc).isoformat()}, headers=headers)
    assert r_close.status_code in (200, 204)

    # now delete should succeed
    g2 = client.get(f"/drivers/{did}", headers=auth_headers)
    etag2 = g2.headers.get("ETag")
    headers2 = {**auth_headers}
    if etag2:
        headers2["If-Match"] = etag2
    rdel2 = client.delete(f"/drivers/{did}", headers=headers2)
    assert rdel2.status_code == 204
