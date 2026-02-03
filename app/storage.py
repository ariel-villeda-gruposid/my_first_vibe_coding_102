from typing import Dict, Optional, List
from datetime import datetime, timezone


class InMemoryStore:
    def __init__(self):
        self.vehicles: Dict[str, dict] = {}
        self.drivers: Dict[str, dict] = {}
        self.assignments: Dict[str, dict] = {}

    # Vehicle helpers
    def add_vehicle(self, vehicle: dict):
        self.vehicles[vehicle["id"]] = vehicle

    def get_vehicle(self, vid: str) -> Optional[dict]:
        return self.vehicles.get(vid)

    def find_vehicle_by_plate(self, plate_normalized: str) -> Optional[dict]:
        for v in self.vehicles.values():
            if v.get("plate_number") == plate_normalized and not v.get("deleted", False):
                return v
        return None

    def soft_delete_vehicle(self, vid: str):
        v = self.get_vehicle(vid)
        if v:
            v["deleted"] = True

    # Driver helpers
    def add_driver(self, driver: dict):
        self.drivers[driver["id"]] = driver

    def get_driver(self, did: str) -> Optional[dict]:
        return self.drivers.get(did)

    # Assignment helpers
    def add_assignment(self, assignment: dict):
        self.assignments[assignment["id"]] = assignment

    def get_assignment(self, aid: str) -> Optional[dict]:
        return self.assignments.get(aid)

    def list_active_assignments_for_vehicle(self, vehicle_id: str) -> List[dict]:
        now = datetime.now(timezone.utc)
        result = []
        for a in self.assignments.values():
            if a.get("vehicle_id") != vehicle_id:
                continue
            end = a.get("end_datetime")
            if end is None:
                result.append(a)
            else:
                if end >= now:
                    result.append(a)
        return result

    def list_active_assignments_for_driver(self, driver_id: str):
        now = datetime.now(timezone.utc)
        result = []
        for a in self.assignments.values():
            if a.get("driver_id") != driver_id:
                continue
            end = a.get("end_datetime")
            if end is None:
                result.append(a)
            else:
                if end >= now:
                    result.append(a)
        return result


store = InMemoryStore()
