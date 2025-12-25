"""
Model Database Model
"""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.infrastructure.database import Base


class Model(Base):
    __tablename__ = "model"

    id = Column(String, primary_key=True)
    provider_id = Column(String, ForeignKey("provider.id"))
    name = Column(String, nullable=False)  # model_name
    alias = Column(String)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())