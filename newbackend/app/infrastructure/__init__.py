"""
Infrastructure Layer - External Integrations
"""

from .database.connection import get_db, DatabaseManager

__all__ = [
    "get_db",
    "DatabaseManager"
]