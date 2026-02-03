import os
from typing import Optional

class Settings:
    """Application configuration from environment variables."""
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017/fleet_api")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "fleet_api")
    ENV: str = os.getenv("ENV", "development")
    LOG_LEVEL: str = "DEBUG" if ENV == "development" else "INFO"

settings = Settings()
