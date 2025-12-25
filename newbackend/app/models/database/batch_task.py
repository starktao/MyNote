"""
BatchTask Database Model
"""

from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func
from app.infrastructure.database import Base


class BatchTask(Base):
    __tablename__ = "batch_task"

    id = Column(String, primary_key=True)
    total = Column(Integer, default=0)
    finished = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())