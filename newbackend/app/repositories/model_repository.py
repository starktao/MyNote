"""
Model Repository - Data Access Layer for Models
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.database.model import Model
from app.models.database.provider import Provider
from app.repositories.base_repository import BaseRepository


class ModelRepository(BaseRepository[Model]):
    def get_model_class(self) -> type:
        return Model

    def find_by_provider_id(self, provider_id: str) -> List[Model]:
        """Find models by provider ID"""
        return (
            self.session.query(Model)
            .filter(Model.provider_id == provider_id)
            .all()
        )

    def find_enabled_by_provider_id(self, provider_id: str) -> List[Model]:
        """Find enabled models by provider ID"""
        return (
            self.session.query(Model)
            .filter(Model.provider_id == provider_id, Model.enabled == True)
            .all()
        )

    def find_enabled_with_provider(self) -> List[tuple[Model, Provider]]:
        """Find enabled models with their providers"""
        return (
            self.session.query(Model, Provider)
            .join(Provider, Model.provider_id == Provider.id)
            .filter(Model.enabled == True, Provider.enabled == True)
            .all()
        )

    def find_by_condition(self, condition: Dict[str, Any]) -> List[Model]:
        """Find models by custom condition"""
        query = self.session.query(Model)
        for key, value in condition.items():
            if hasattr(Model, key):
                query = query.filter(getattr(Model, key) == value)
        return query.all()

    def update_enabled(self, model_id: str, enabled: bool) -> Optional[Model]:
        """Update model enabled status"""
        model = self.find_by_id(model_id)
        if model:
            model.enabled = enabled
            self.session.commit()
            self.session.refresh(model)
        return model

    def find_by_name_and_provider(self, name: str, provider_id: str) -> Optional[Model]:
        """Find model by name and provider ID"""
        return (
            self.session.query(Model)
            .filter(Model.name == name, Model.provider_id == provider_id)
            .first()
        )

    # Override update method to handle entity objects instead of dictionaries
    def update(self, entity) -> Model:
        """Update entity object"""
        self.session.commit()
        self.session.refresh(entity)
        return entity