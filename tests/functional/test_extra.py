from datetime import datetime, timezone
import uuid


def test_unauthorized_access_is_401(client):
    # no auth header
    r = client.get("/vehicles")
    assert r.status_code == 401


def test_patch_vehicle_duplicate_plate_conflict(client, auth_headers):
    # create two vehicles
    r1 = client.post("/vehicles", json={"plate_number": "AA01", "model": "M1", "year": 2020, "type": "SEDAN", "fuel_type": "GASOLINE"}, headers=auth_headers)
    assert r1.status_code == 201
    r2 = client.post("/vehicles", json={"plate_number": "BB02", "model": "M2", "year": 2020, "type": "SEDAN", "fuel_type": "GASOLINE"}, headers=auth_headers)
    assert r2.status_code == 201
    v2 = r2.json()

    # get ETag for v2
    etag = client.get(f"/vehicles/{v2['id']}", headers=auth_headers).headers.get("ETag")
    headers = {**auth_headers}
    if etag:
        headers["If-Match"] = etag
    # attempt to set v2 plate to AA01 -> should conflict
    r_patch = client.patch(f"/vehicles/{v2['id']}", json={"plate_number": "AA01"}, headers=headers)
    assert r_patch.status_code == 409
    err = r_patch.json()
    assert err["error"]["code"] == "DUPLICATE_PLATE" or err["error"]["code"] == "DUPLICATE_VEHICLE"


def test_delete_nonexistent_vehicle_returns_404(client, auth_headers):
    vid = str(uuid.uuid4())
    headers = {**auth_headers, "If-Match": '"dummy"'}
    r = client.delete(f"/vehicles/{vid}", headers=headers)
    assert r.status_code == 404
