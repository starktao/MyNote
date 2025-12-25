"""
Provider Repository - Data Access Layer for Providers
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.database.provider import Provider
from app.repositories.base_repository import BaseRepository


class ProviderRepository(BaseRepository[Provider]):
    def get_model_class(self) -> type:
        return Provider

    def find_all_enabled(self) -> List[Provider]:
        """Find all enabled providers"""
        return self.session.query(Provider).filter(Provider.enabled == True).all()

    def find_by_type(self, provider_type: str) -> List[Provider]:
        """Find providers by type"""
        return self.session.query(Provider).filter(Provider.type == provider_type).all()

    def update_enabled(self, provider_id: str, enabled: bool) -> Optional[Provider]:
        """Update provider enabled status"""
        provider = self.find_by_id(provider_id)
        if provider:
            provider.enabled = enabled
            self.session.commit()
            self.session.refresh(provider)
        return provider

    def find_enabled_by_id(self, provider_id: str) -> Optional[Provider]:
        """Find enabled provider by ID"""
        return (
            self.session.query(Provider)
            .filter(Provider.id == provider_id, Provider.enabled == True)
            .first()
        )