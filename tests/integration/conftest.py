"""Integration test configuration."""
import pytest
import os
from pymongo import MongoClient

# Use test database
os.environ["DATABASE_NAME"] = "fleet_api_test"
os.environ["MONGODB_URI"] = "mongodb://localhost:27017"
