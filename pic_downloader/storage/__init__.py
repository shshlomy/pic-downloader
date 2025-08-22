"""
Storage domain - handles file storage and database operations.

This package contains functionality for managing file storage,
database operations, and data persistence.
"""

from .managers.sequential_manager import SequentialStorageManager
from .database.sqlite_manager import SQLiteDatabaseManager

__all__ = [
    "SequentialStorageManager",
    "SQLiteDatabaseManager"
]
