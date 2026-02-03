# Storage layer - provide store instance with backward-compatible interface
from app.storage.mongo import MongoStorage, connect_mongo, disconnect_mongo, get_db as get_mongo_db
from app.storage.adapter import StorageAdapter

_store_instance = None

def get_store():
    """Get the global storage adapter instance, initializing if needed."""
    global _store_instance
    if _store_instance is None:
        try:
            connect_mongo()
            mongo_storage = MongoStorage()
            _store_instance = StorageAdapter(mongo_storage)
        except Exception as e:
            # If MongoDB init fails, _store_instance remains None
            # The app will fail when trying to use it
            raise
    return _store_instance

# Initialize store instance
try:
    store = get_store()
except:
    # For testing environments where MongoDB might not be available initially
    store = None

__all__ = ["store", "get_store", "StorageAdapter", "MongoStorage", "connect_mongo", "disconnect_mongo", "get_mongo_db"]

