"""
Base Repository - Abstract Data Access Layer with Context Manager Support
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Any, Dict
from sqlalchemy.orm import Session
from app.infrastructure.database.connection import get_db

T = TypeVar('T')


class BaseRepository(Generic[T], ABC):
    """
    Base Repository with context manager support for proper connection lifecycle management.

    Usage:
        with TaskRepository() as repo:
            task = repo.create(task_data)
        # Connection automatically released
    """
    def __init__(self, session: Optional[Session] = None):
        self._session = session
        self._owns_session = session is None

    @property
    def session(self) -> Session:
        """Get the database session, ensuring it's properly initialized"""
        if self._session is None:
            raise RuntimeError("Session not initialized - use 'with' statement or provide session")
        return self._session

    def __enter__(self):
        """Context manager entry - acquire session if needed"""
        if self._owns_session:
            self._session = next(get_db())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - release session if we own it"""
        if self._owns_session and self._session:
            self._session.close()
            self._session = None

    @abstractmethod
    def get_model_class(self) -> type:
        """Return the SQLAlchemy model class"""
        pass

    def create(self, entity_data: T) -> T:
        """Create a new entity"""
        self.session.add(entity_data)
        self.session.commit()
        self.session.refresh(entity_data)
        return entity_data

    def find_by_id(self, entity_id: str) -> Optional[T]:
        """Find entity by ID"""
        model_class = self.get_model_class()
        return self.session.query(model_class).filter(model_class.id == entity_id).first()

    def find_all(self) -> List[T]:
        """Find all entities"""
        model_class = self.get_model_class()
        return self.session.query(model_class).all()

    def update(self, entity_id: str, update_data: Dict[str, Any]) -> Optional[T]:
        """Update entity by ID"""
        db_entity = self.find_by_id(entity_id)
        if db_entity:
            for key, value in update_data.items():
                if hasattr(db_entity, key):
                    setattr(db_entity, key, value)
            self.session.commit()
            self.session.refresh(db_entity)
        return db_entity

    def delete(self, entity_id: str) -> bool:
        """Delete entity by ID"""
        db_entity = self.find_by_id(entity_id)
        if db_entity:
            self.session.delete(db_entity)
            self.session.commit()
            return True
        return False

    def count(self) -> int:
        """Count all entities"""
        model_class = self.get_model_class()
        return self.session.query(model_class).count()

    def exists(self, entity_id: str) -> bool:
        """Check if entity exists"""
        return self.find_by_id(entity_id) is not None