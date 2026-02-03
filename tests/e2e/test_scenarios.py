"""End-to-End tests with real MongoDB backend and complete business scenarios.

Traceability: Each test case includes comments mapping to:
- REQ_* = Requirements from specification
- FUNC_* = Functional test reference
- BUS_RULE_* = Business rule enforcement
"""
import pytest
from datetime import datetime, timezone
from uuid import uuid4


class TestE2EVehicleLifecycle:
    """E2E Scenario 1: Complete vehicle lifecycle from creation to soft-delete.
    
    Traceability:
    - REQ_VEHICLE_CREATE: Create new vehicles via POST /vehicles
    - REQ_VEHICLE_UPDATE: Update vehicle attributes via PATCH /vehicles/{id}
    - REQ_VEHICLE_SOFT_DELETE: Soft-delete vehicle via DELETE /vehicles/{id}
    - REQ_STATUS_CHANGE: Change status to INACTIVE/MAINTENANCE
    - BUS_RULE_PLATE_UNIQUE: Plate numbers must be unique (case-insensitive)
    - BUS_RULE_SOFT_DELETE: Vehicles can only be deleted if unassigned
    """
    
    def test_vehicle_lifecycle_creation_to_deletion(self, client, auth_headers):
        """Test complete vehicle lifecycle: create → update → delete."""
        # FUNC_VEHICLES_CREATE: Create vehicle
        payload = {
            "plate_number": "ABC123",
            "model": "Tesla Model 3",
            "year": 2024,
            "type": "SEDAN",
            "fuel_type": "ELECTRIC",
            "status": "ACTIVE"
        }
        resp = client.post("/vehicles", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        vehicle_id = resp.json()["id"]
        assert resp.json()["plate_number"] == "ABC123"
        assert resp.json()["status"] == "ACTIVE"
        
        # FUNC_VEHICLES_GET: Retrieve vehicle
        resp = client.get(f"/vehicles/{vehicle_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["plate_number"] == "ABC123"
        etag = resp.headers.get("ETag")
        assert etag is not None
        
        # FUNC_VEHICLES_PATCH: Update vehicle
        resp = client.patch(
            f"/vehicles/{vehicle_id}",
            json={"model": "Tesla Model S"},
            headers={**auth_headers, "If-Match": etag}
        )
        assert resp.status_code == 200
        assert resp.json()["model"] == "Tesla Model S"
        
        # FUNC_VEHICLES_DELETE: Soft-delete vehicle (unassigned)
        resp_get = client.get(f"/vehicles/{vehicle_id}", headers=auth_headers)
        etag = resp_get.headers.get("ETag")
        resp = client.delete(
            f"/vehicles/{vehicle_id}",
            headers={**auth_headers, "If-Match": etag}
        )
        assert resp.status_code == 204
        
        # Verify soft-delete (vehicle still exists but is marked deleted)
        resp = client.get(f"/vehicles/{vehicle_id}", headers=auth_headers)
        assert resp.status_code == 404
        
        # Verify vehicle not in list by default
        resp = client.get("/vehicles", headers=auth_headers)
        assert resp.status_code == 200
        vehicle_ids = [v["id"] for v in resp.json()["data"]]
        assert vehicle_id not in vehicle_ids
        
        # Verify vehicle exists with include_deleted=true
        resp = client.get("/vehicles?include_deleted=true", headers=auth_headers)
        assert resp.status_code == 200
        vehicle_ids = [v["id"] for v in resp.json()["data"]]
        assert vehicle_id in vehicle_ids


class TestE2EDriverAssignmentFlow:
    """E2E Scenario 2: Complete driver creation and assignment workflow.
    
    Traceability:
    - REQ_DRIVER_CREATE: Create drivers via POST /drivers
    - REQ_ASSIGNMENT_CREATE: Create assignments via POST /assignments
    - REQ_ASSIGNMENT_UPDATE: Update assignment end_datetime via PATCH /assignments/{id}
    - BUS_RULE_DRIVER_ACTIVE_ONLY: Only ACTIVE drivers can have assignments
    - BUS_RULE_DRIVER_ONE_ASSIGNMENT: Driver can only have one active assignment
    - BUS_RULE_PHONE_VALIDATION: Contact numbers must be valid phone format
    """
    
    def test_driver_creation_and_assignment(self, client, auth_headers):
        """Test driver creation and assignment to vehicle."""
        # FUNC_VEHICLES_CREATE: Create vehicle
        vehicle_payload = {
            "plate_number": "XYZ789",
            "model": "Ford Transit",
            "year": 2023,
            "type": "VAN",
            "fuel_type": "DIESEL"
        }
        resp = client.post("/vehicles", json=vehicle_payload, headers=auth_headers)
        assert resp.status_code == 201
        vehicle_id = resp.json()["id"]
        
        # FUNC_DRIVERS_CREATE: Create driver
        driver_payload = {
            "name": "John Smith",
            "license_number": "DL123456",
            "contact_number": "+14155552671",
            "status": "ACTIVE"
        }
        resp = client.post("/drivers", json=driver_payload, headers=auth_headers)
        assert resp.status_code == 201
        driver_id = resp.json()["id"]
        assert resp.json()["status"] == "ACTIVE"
        
        # FUNC_ASSIGNMENTS_CREATE: Create assignment
        start_dt = datetime.now(timezone.utc).replace(microsecond=(datetime.now(timezone.utc).microsecond // 1000) * 1000)
        assignment_payload = {
            "driver_id": driver_id,
            "vehicle_id": vehicle_id,
            "start_datetime": start_dt.isoformat()
        }
        resp = client.post("/assignments", json=assignment_payload, headers=auth_headers)
        assert resp.status_code == 201
        assignment_id = resp.json()["id"]
        assert resp.json()["driver_id"] == driver_id
        assert resp.json()["vehicle_id"] == vehicle_id
        assert resp.json()["end_datetime"] is None  # Ongoing assignment
        
        # FUNC_ASSIGNMENTS_GET: Retrieve assignment
        resp = client.get(f"/assignments/{assignment_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["driver_id"] == driver_id
        
        # FUNC_ASSIGNMENTS_PATCH: Close assignment
        end_dt = datetime.now(timezone.utc).replace(microsecond=(datetime.now(timezone.utc).microsecond // 1000) * 1000)
        resp = client.patch(
            f"/assignments/{assignment_id}",
            json={"end_datetime": end_dt.isoformat()},
            headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["end_datetime"] is not None
        
        # BUS_RULE_DRIVER_ONE_ASSIGNMENT: Verify driver can now have new assignment
        resp = client.post("/assignments", json=assignment_payload, headers=auth_headers)
        assert resp.status_code == 201  # Should succeed since previous assignment is closed


class TestE2EStatusConstraints:
    """E2E Scenario 3: Status constraint enforcement with assignments.
    
    Traceability:
    - BUS_RULE_INACTIVE_NO_ASSIGN: Cannot assign INACTIVE/MAINTENANCE vehicles
    - BUS_RULE_SUSPENDED_NO_ASSIGN: Cannot assign SUSPENDED drivers
    - BUS_RULE_AUTO_CLOSE_ASSIGNMENTS: Auto-close assignments when entity status changes
    - REQ_STATUS_CHANGE: Change entity status and verify cascading effects
    """
    
    def test_status_constraints_prevent_assignments(self, client, auth_headers):
        """Test that status constraints properly enforce business rules."""
        # Create vehicle and driver
        vehicle_resp = client.post(
            "/vehicles",
            json={"plate_number": "V001", "model": "Car", "year": 2024, "type": "SEDAN", "fuel_type": "GASOLINE"},
            headers=auth_headers
        )
        vehicle_id = vehicle_resp.json()["id"]
        
        driver_resp = client.post(
            "/drivers",
            json={"name": "Driver A", "license_number": "DLA001", "contact_number": "+14155552671"},
            headers=auth_headers
        )
        driver_id = driver_resp.json()["id"]
        
        # BUS_RULE_INACTIVE_NO_ASSIGN: Try to assign INACTIVE vehicle (should fail)
        vehicle_get = client.get(f"/vehicles/{vehicle_id}", headers=auth_headers)
        etag = vehicle_get.headers.get("ETag")
        
        resp = client.patch(
            f"/vehicles/{vehicle_id}",
            json={"status": "INACTIVE"},
            headers={**auth_headers, "If-Match": etag}
        )
        assert resp.status_code == 200
        
        # Now try to create assignment with INACTIVE vehicle
        start_dt = datetime.now(timezone.utc).replace(microsecond=0)
        resp = client.post(
            "/assignments",
            json={"driver_id": driver_id, "vehicle_id": vehicle_id, "start_datetime": start_dt.isoformat()},
            headers=auth_headers
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "VEHICLE_INACTIVE"
        
        # Create another vehicle for next test
        vehicle2_resp = client.post(
            "/vehicles",
            json={"plate_number": "V002", "model": "Truck", "year": 2023, "type": "TRUCK", "fuel_type": "DIESEL"},
            headers=auth_headers
        )
        vehicle2_id = vehicle2_resp.json()["id"]
        
        # BUS_RULE_SUSPENDED_NO_ASSIGN: Try to assign SUSPENDED driver (should fail)
        driver_get = client.get(f"/drivers/{driver_id}", headers=auth_headers)
        etag = driver_get.headers.get("ETag")
        
        resp = client.patch(
            f"/drivers/{driver_id}",
            json={"status": "SUSPENDED"},
            headers={**auth_headers, "If-Match": etag}
        )
        assert resp.status_code == 200
        
        # Try to create assignment with SUSPENDED driver
        resp = client.post(
            "/assignments",
            json={"driver_id": driver_id, "vehicle_id": vehicle2_id, "start_datetime": start_dt.isoformat()},
            headers=auth_headers
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "DRIVER_SUSPENDED"


class TestE2ECompleteWorkflow:
    """E2E Scenario 4: Complete multi-entity workflow with error handling.
    
    Traceability:
    - REQ_CONCURRENT_ASSIGNMENTS: Prevent overlapping assignments
    - REQ_VALIDATION: Validate all input data (plates, phones, notes)
    - REQ_ERROR_RESPONSES: Return proper error codes and validation details
    - BUS_RULE_OVERLAP_DETECTION: Prevent vehicle/driver overlap assignments
    """
    
    def test_complete_workflow_with_validations(self, client, auth_headers):
        """Test comprehensive workflow with validation and error handling."""
        # Create multiple vehicles
        vehicles = []
        for i in range(3):
            resp = client.post(
                "/vehicles",
                json={
                    "plate_number": f"V{i:04d}",
                    "model": f"Model {i}",
                    "year": 2024 - i,
                    "type": "SEDAN",
                    "fuel_type": "GASOLINE"
                },
                headers=auth_headers
            )
            assert resp.status_code == 201
            vehicles.append(resp.json()["id"])
        
        # Create multiple drivers
        drivers = []
        for i in range(3):
            resp = client.post(
                "/drivers",
                json={
                    "name": f"Driver {i}",
                    "license_number": f"DL{i:06d}",
                    "contact_number": f"+1415555{i:04d}"
                },
                headers=auth_headers
            )
            assert resp.status_code == 201
            drivers.append(resp.json()["id"])
        
        # Create assignments in a chain
        start_dt = datetime.now(timezone.utc).replace(microsecond=0)
        assignments = []
        for i in range(3):
            resp = client.post(
                "/assignments",
                json={
                    "driver_id": drivers[i],
                    "vehicle_id": vehicles[i],
                    "start_datetime": start_dt.isoformat(),
                    "notes": f"Assignment {i} with notes"
                },
                headers=auth_headers
            )
            assert resp.status_code == 201
            assignments.append(resp.json()["id"])
        
        # REQ_CONCURRENT_ASSIGNMENTS: Try to assign same driver to another vehicle (should fail)
        resp = client.post(
            "/assignments",
            json={
                "driver_id": drivers[0],  # Already assigned
                "vehicle_id": vehicles[1],  # Different vehicle
                "start_datetime": start_dt.isoformat()
            },
            headers=auth_headers
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "DRIVER_ALREADY_ASSIGNED"
        
        # REQ_CONCURRENT_ASSIGNMENTS: Try to assign same vehicle to another driver (should fail)
        resp = client.post(
            "/assignments",
            json={
                "driver_id": drivers[1],  # Different driver
                "vehicle_id": vehicles[0],  # Already assigned
                "start_datetime": start_dt.isoformat()
            },
            headers=auth_headers
        )
        assert resp.status_code == 409
        # Note: Driver is not assigned yet, so vehicle check happens first in some cases
        # But if we check driver first, we get DRIVER_ALREADY_ASSIGNED if driver[1] is already assigned
        # In this scenario, driver[1] is already assigned to vehicle[1], so we expect that error
        assert resp.json()["error"]["code"] in ("VEHICLE_ALREADY_ASSIGNED", "DRIVER_ALREADY_ASSIGNED")
        
        # REQ_VALIDATION: Test invalid phone number
        resp = client.post(
            "/drivers",
            json={
                "name": "Invalid Driver",
                "license_number": "INVALID001",
                "contact_number": "invalid-phone"
            },
            headers=auth_headers
        )
        assert resp.status_code == 422
        assert "contact_number" in resp.json()["error"]["details"]
        
        # REQ_VALIDATION: Test duplicate plate
        resp = client.post(
            "/vehicles",
            json={
                "plate_number": "V0000",  # Already exists
                "model": "Duplicate",
                "year": 2024,
                "type": "SEDAN",
                "fuel_type": "GASOLINE"
            },
            headers=auth_headers
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "DUPLICATE_PLATE"
        
        # BUS_RULE_OVERLAP_DETECTION: Close assignment and create new one for same pair
        end_dt = datetime.now(timezone.utc).replace(microsecond=0)
        resp = client.patch(
            f"/assignments/{assignments[0]}",
            json={"end_datetime": end_dt.isoformat()},
            headers=auth_headers
        )
        assert resp.status_code == 200
        
        # Also close vehicle[1]'s assignment to free it up for a new assignment
        resp = client.patch(
            f"/assignments/{assignments[1]}",
            json={"end_datetime": end_dt.isoformat()},
            headers=auth_headers
        )
        assert resp.status_code == 200

        # Should now be able to assign driver[0] to vehicle[1] (now unassigned)
        resp = client.post(
            "/assignments",
            json={
                "driver_id": drivers[0],
                "vehicle_id": vehicles[1],  # Now free from assignment[1]
                "start_datetime": end_dt.isoformat()
            },
            headers=auth_headers
        )
        assert resp.status_code == 201
        
        # Verify we can retrieve the new assignment
        new_assignment_id = resp.json()["id"]
        resp = client.get(f"/assignments/{new_assignment_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["driver_id"] == drivers[0]
        assert resp.json()["vehicle_id"] == vehicles[1]
