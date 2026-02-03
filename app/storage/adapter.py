"""Adapter to bridge MongoStorage to in-memory dict interface for routers."""
from typing import Dict, Optional, List
from datetime import datetime, timezone


def _clean_doc(doc: Dict) -> Dict:
    """Remove MongoDB internal fields (_id) from document."""
    if doc is None:
        return None
    doc_copy = doc.copy()
    if "_id" in doc_copy:
        del doc_copy["_id"]
    return doc_copy


class StorageAdapter:
    """Provides a dict-like interface on top of MongoStorage for backward compatibility."""
    
    def __init__(self, mongo_storage):
        self.mongo = mongo_storage
        # Note: Not caching because MongoDB updates bypass the cache and cause stale data
    
    @property
    def vehicles(self) -> Dict:
        """Return vehicles dict. Fetches fresh from MongoDB."""
        result = {}
        docs = self.mongo.db.vehicles.find({"deleted": False})
        for doc in docs:
            result[doc["id"]] = _clean_doc(doc)
        return result
    
    @property
    def drivers(self) -> Dict:
        """Return drivers dict. Fetches fresh from MongoDB."""
        result = {}
        docs = self.mongo.db.drivers.find({"deleted": False})
        for doc in docs:
            result[doc["id"]] = _clean_doc(doc)
        return result
    
    @property
    def assignments(self) -> Dict:
        """Return assignments dict. Fetches fresh from MongoDB."""
        result = {}
        docs = self.mongo.db.assignments.find({})
        for doc in docs:
            result[doc["id"]] = _clean_doc(doc)
        return result
    
    # Delegate to MongoStorage methods
    def get_vehicle(self, vid: str):
        return _clean_doc(self.mongo.get_vehicle(vid))
    
    def add_vehicle(self, vehicle: Dict):
        return _clean_doc(self.mongo.create_vehicle(vehicle))
    
    def find_vehicle_by_plate(self, plate: str):
        return _clean_doc(self.mongo.find_vehicle_by_plate(plate))
    
    def soft_delete_vehicle(self, vid: str):
        self.mongo.soft_delete_vehicle(vid)
    
    def update_vehicle(self, vid: str, updates: Dict):
        return _clean_doc(self.mongo.update_vehicle(vid, updates))
    
    def list_active_assignments_for_vehicle(self, vid: str) -> List[Dict]:
        result = self.mongo.list_active_assignments_for_vehicle(vid)
        return [_clean_doc(a) for a in result]
    
    # Driver methods
    def get_driver(self, did: str):
        return _clean_doc(self.mongo.get_driver(did))
    
    def add_driver(self, driver: Dict):
        return _clean_doc(self.mongo.create_driver(driver))
    
    def find_driver_by_license(self, license_num: str):
        return _clean_doc(self.mongo.find_driver_by_license(license_num))
    
    def soft_delete_driver(self, did: str):
        self.mongo.soft_delete_driver(did)
    
    def update_driver(self, did: str, updates: Dict):
        return _clean_doc(self.mongo.update_driver(did, updates))
    
    def list_active_assignments_for_driver(self, did: str) -> List[Dict]:
        result = self.mongo.list_active_assignments_for_driver(did)
        return [_clean_doc(a) for a in result]
    
    # Assignment methods
    def get_assignment(self, aid: str):
        return _clean_doc(self.mongo.get_assignment(aid))
    
    def add_assignment(self, assignment: Dict):
        return _clean_doc(self.mongo.create_assignment(assignment))
    
    def update_assignment(self, aid: str, updates: Dict):
        result = _clean_doc(self.mongo.update_assignment(aid, updates))
        return result
    
    def delete_assignment(self, aid: str):
        self.mongo.delete_assignment(aid)
