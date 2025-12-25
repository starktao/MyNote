"""
Provider Database Model
"""

from sqlalchemy import Column, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from app.infrastructure.database import Base


class Provider(Base):
    __tablename__ = "provider"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    logo = Column(String, nullable=False, default="default")
    type = Column(String, nullable=False, default="custom")  # built-in/custom
    api_key = Column(Text)
    base_url = Column(Text)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())