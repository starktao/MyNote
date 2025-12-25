from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def init_db():
    from . import models  # noqa: F401
    import json
    import os

    Base.metadata.create_all(bind=engine)




def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

