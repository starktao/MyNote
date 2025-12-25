"""
Model Business Entity
"""

from typing import Optional
from datetime import datetime


class ModelEntity:
    def __init__(
        self,
        id: str,
        provider_id: str,
        name: str,
        alias: Optional[str] = None,
        enabled: bool = True,
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.provider_id = provider_id
        self.name = name
        self.alias = alias or name
        self.enabled = enabled
        self.created_at = created_at or datetime.now()

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def update_alias(self, alias: str):
        self.alias = alias

    def get_display_name(self) -> str:
        return self.alias or self.name