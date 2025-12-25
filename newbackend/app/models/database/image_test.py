"""
AI图像识别检测功能数据模型
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.infrastructure.database.db import Base


class ImageTestSession(Base):
    """图像识别测试会话表"""
    __tablename__ = "image_test_session"

    id = Column(String(36), primary_key=True)  # UUID
    provider_id = Column(String(100), nullable=False)  # Provider ID
    model_name = Column(String(100), nullable=False)  # 模型名称
    status = Column(String(20), default="created")  # created, running, completed, failed
    total_tests = Column(Integer, default=0)  # 总测试数
    passed_tests = Column(Integer, default=0)  # 通过测试数
    failed_tests = Column(Integer, default=0)  # 失败测试数
    pass_rate = Column(Integer, default=0)  # 通过率 (0-100)
    start_time = Column(DateTime, server_default=func.now())
    end_time = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    results = relationship("ImageTestResult", back_populates="session", cascade="all, delete-orphan")


class ImageTestResult(Base):
    """图像识别测试结果表"""
    __tablename__ = "image_test_result"

    id = Column(String(36), primary_key=True)  # UUID
    session_id = Column(String(36), ForeignKey("image_test_session.id"), nullable=False)
    image_name = Column(String(100), nullable=False)  # 图像名称 (dog, cat, car, building)
    image_uuid = Column(String(100), nullable=False)  # UUID文件名
    correct_answer = Column(String(1), nullable=False)  # 正确答案 (A, B, C, D)
    ai_response = Column(Text)  # AI响应内容
    is_correct = Column(Boolean)  # 是否正确
    response_time_ms = Column(Integer)  # 响应时间(毫秒)
    error_message = Column(Text)  # 错误信息
    created_at = Column(DateTime, server_default=func.now())

    # 关系
    session = relationship("ImageTestSession", back_populates="results")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "image_name": self.image_name,
            "image_uuid": self.image_uuid,
            "correct_answer": self.correct_answer,
            "ai_response": self.ai_response,
            "is_correct": self.is_correct,
            "response_time_ms": self.response_time_ms,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }