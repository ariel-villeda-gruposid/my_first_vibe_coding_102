from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, ServerSelectionTimeoutError
from datetime import datetime, timezone
from typing import Optional, List, Dict
from app.config import settings

# Global MongoDB client
_client: Optional[MongoClient] = None
_db = None


def connect_mongo():
    """Connect to MongoDB and create indexes."""
    global _client, _db
    try:
        _client = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
        _client.admin.command('ping')
        _db = _client[settings.DATABASE_NAME]
        
        # Create indexes
        _db["vehicles"].create_index("plate_number", unique=True, sparse=True)
        _db["drivers"].create_index("license_number", unique=True, sparse=True)
        
        return _db
    except ServerSelectionTimeoutError as e:
        raise ConnectionError(f"Failed to connect to MongoDB: {e}")


def disconnect_mongo():
    """Close MongoDB connection."""
    global _client
    if _client:
        _client.close()


def get_db():
    """Get MongoDB database instance."""
    if _db is None:
        raise RuntimeError("MongoDB not connected. Call connect_mongo() first.")
    return _db


class MongoStorage:
    """MongoDB-backed storage for fleet management entities."""

    def __init__(self, db=None):
        self.db = db if db is not None else get_db()

    # Vehicle operations
    def create_vehicle(self, vehicle: Dict):
        """Insert a vehicle; returns the vehicle."""
        vehicle_copy = vehicle.copy()
        vehicle_copy["deleted"] = False
        try:
            result = self.db.vehicles.insert_one(vehicle_copy)
            vehicle_copy["_id"] = result.inserted_id
            return vehicle_copy
        except DuplicateKeyError:
            raise ValueError("Duplicate plate number")

    def get_vehicle(self, vid: str) -> Optional[Dict]:
        return self.db.vehicles.find_one({"id": vid})

    def find_vehicle_by_plate(self, plate_norm: str) -> Optional[Dict]:
        return self.db.vehicles.find_one({"plate_number": plate_norm, "deleted": False})

    def update_vehicle(self, vid: str, updates: Dict) -> Optional[Dict]:
        self.db.vehicles.update_one({"id": vid}, {"$set": updates})
        return self.get_vehicle(vid)

    def soft_delete_vehicle(self, vid: str):
        self.db.vehicles.update_one({"id": vid}, {"$set": {"deleted": True}})

    def list_active_assignments_for_vehicle(self, vehicle_id: str) -> List[Dict]:
        now = datetime.now(timezone.utc)
        query = {
            "vehicle_id": vehicle_id,
            "$or": [
                {"end_datetime": None},
                {"end_datetime": {"$gte": now}}
            ]
        }
        return list(self.db.assignments.find(query))

    # Driver operations
    def create_driver(self, driver: Dict):
        driver_copy = driver.copy()
        driver_copy["deleted"] = False
        try:
            result = self.db.drivers.insert_one(driver_copy)
            driver_copy["_id"] = result.inserted_id
            return driver_copy
        except DuplicateKeyError:
            raise ValueError("Duplicate license number")

    def get_driver(self, did: str) -> Optional[Dict]:
        return self.db.drivers.find_one({"id": did})

    def find_driver_by_license(self, license_norm: str) -> Optional[Dict]:
        return self.db.drivers.find_one({"license_number": license_norm, "deleted": False})

    def update_driver(self, did: str, updates: Dict) -> Optional[Dict]:
        self.db.drivers.update_one({"id": did}, {"$set": updates})
        return self.get_driver(did)

    def soft_delete_driver(self, did: str):
        self.db.drivers.update_one({"id": did}, {"$set": {"deleted": True}})

    def list_active_assignments_for_driver(self, driver_id: str) -> List[Dict]:
        now = datetime.now(timezone.utc)
        query = {
            "driver_id": driver_id,
            "$or": [
                {"end_datetime": None},
                {"end_datetime": {"$gte": now}}
            ]
        }
        return list(self.db.assignments.find(query))

    # Assignment operations
    def create_assignment(self, assignment: Dict):
        result = self.db.assignments.insert_one(assignment)
        assignment["_id"] = result.inserted_id
        return assignment

    def get_assignment(self, aid: str) -> Optional[Dict]:
        return self.db.assignments.find_one({"id": aid})

    def update_assignment(self, aid: str, updates: Dict) -> Optional[Dict]:
        self.db.assignments.update_one({"id": aid}, {"$set": updates})
        return self.get_assignment(aid)

    def delete_assignment(self, aid: str):
        self.db.assignments.delete_one({"id": aid})

    def list_assignments(self, limit: int = 50, skip: int = 0, driver_id: Optional[str] = None, vehicle_id: Optional[str] = None) -> tuple:
        query = {}
        if driver_id:
            query["driver_id"] = driver_id
        if vehicle_id:
            query["vehicle_id"] = vehicle_id
        total = self.db.assignments.count_documents(query)
        items = list(self.db.assignments.find(query).skip(skip).limit(limit))
        return items, total
