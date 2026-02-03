from pymongo import MongoClient, ReturnDocument
from typing import Optional, List
from datetime import datetime, timezone


class MongoStore:
    def __init__(self, mongo_url: str = "mongodb://localhost:27017", db_name: str = "fleet_db"):
        self.client = MongoClient(mongo_url)
        self.db = self.client[db_name]
        # ensure indexes
        self.db.vehicles.create_index([("plate_number", 1)], unique=True, name="plate_idx")
        self.db.drivers.create_index([("license_number", 1)], unique=True, name="license_idx")

    # Vehicle helpers
    def add_vehicle(self, vehicle: dict):
        # expect datetimes
        self.db.vehicles.insert_one(vehicle)

    def get_vehicle(self, vid: str) -> Optional[dict]:
        return self.db.vehicles.find_one({"id": vid})

    def find_vehicle_by_plate(self, plate_normalized: str) -> Optional[dict]:
        return self.db.vehicles.find_one({"plate_number": plate_normalized, "deleted": {"$ne": True}})

    def soft_delete_vehicle(self, vid: str):
        self.db.vehicles.update_one({"id": vid}, {"$set": {"deleted": True}})

    # Driver helpers
    def add_driver(self, driver: dict):
        self.db.drivers.insert_one(driver)

    def get_driver(self, did: str) -> Optional[dict]:
        return self.db.drivers.find_one({"id": did})

    # Assignment helpers
    def add_assignment(self, assignment: dict):
        self.db.assignments.insert_one(assignment)

    def get_assignment(self, aid: str) -> Optional[dict]:
        return self.db.assignments.find_one({"id": aid})

    def list_active_assignments_for_vehicle(self, vehicle_id: str) -> List[dict]:
        now = datetime.now(timezone.utc)
        cursor = self.db.assignments.find({"vehicle_id": vehicle_id, "$or": [{"end_datetime": None}, {"end_datetime": {"$gte": now}}]})
        return list(cursor)

    def list_active_assignments_for_driver(self, driver_id: str) -> List[dict]:
        now = datetime.now(timezone.utc)
        cursor = self.db.assignments.find({"driver_id": driver_id, "$or": [{"end_datetime": None}, {"end_datetime": {"$gte": now}}]})
        return list(cursor)

    # Utilities for tests
    def drop_collections(self):
        self.db.vehicles.drop()
        self.db.drivers.drop()
        self.db.assignments.drop()
