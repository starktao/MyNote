"""
System Related DTOs
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel


class SystemStatusDTO(BaseModel):
    status: str
    uptime: str
    version: str
    database_status: str
    external_services: Dict[str, str]


class HealthCheckDTO(BaseModel):
    healthy: bool
    checks: Dict[str, bool]
    details: Dict[str, str]


class APIResponseDTO(BaseModel):
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None