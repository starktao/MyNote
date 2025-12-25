"""
Provider Business Entity
"""

from typing import Optional, List
from datetime import datetime


class ProviderEntity:
    def __init__(
        self,
        id: str,
        name: str,
        logo: str = "default",
        type: str = "custom",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        enabled: bool = True,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id
        self.name = name
        self.logo = logo
        self.type = type
        self.api_key = api_key
        self.base_url = base_url
        self.enabled = enabled
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def enable(self):
        self.enabled = True
        self.updated_at = datetime.now()

    def disable(self):
        self.enabled = False
        self.updated_at = datetime.now()

    def update_credentials(self, api_key: str, base_url: Optional[str] = None):
        self.api_key = api_key
        if base_url:
            self.base_url = base_url
        self.updated_at = datetime.now()

    def is_configured(self) -> bool:
        return bool(self.api_key)