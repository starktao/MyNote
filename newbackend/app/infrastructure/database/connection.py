"""
Database Connection Management
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import event
from sqlalchemy.engine import Engine
from app.config.settings import settings
from app.infrastructure.database.db import Base
import logging

logger = logging.getLogger(__name__)

# Create engine - 优化连接池配置以解决连接池耗尽问题
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_size=20,           # 从5增加到20
    max_overflow=30,        # 从10增加到30 (总共50个连接)
    pool_timeout=60,        # 从30增加到60秒
    pool_recycle=1800,      # 从3600减少到1800秒 (30分钟)
    pool_pre_ping=True      # 新增连接健康检查
)

# 连接池监控事件
@event.listens_for(Engine, "connect")
def receive_connect(dbapi_connection, connection_record):
    logger.info("数据库连接已建立")

@event.listens_for(Engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    logger.info(f"连接已检出，使用中连接数：{engine.pool.checkedout()}")

@event.listens_for(Engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    logger.info(f"连接已归还，空闲连接数：{engine.pool.checkedin()}")

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class DatabaseManager:
    """Database connection manager"""

    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal

    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()