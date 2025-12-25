"""
模型能力检测控制器
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from pydantic import BaseModel
import time
import asyncio

from app.infrastructure.database.connection import get_db
from app.repositories.provider_repository import ProviderRepository
from app.services.model_capability_detector import ModelCapabilityDetector
from app.utils.response import R

router = APIRouter()

class CapabilityCheckRequest(BaseModel):
    """能力检测请求"""
    model_config = {"protected_namespaces": ()}  # 允许 model_ 开头的字段名

    provider_id: str
    model_name: str

class CapabilityCheckResponse(BaseModel):
    """能力检测响应"""
    model_config = {"protected_namespaces": ()}  # 允许 model_ 开头的字段名

    has_vision_capability: bool
    model_answer: str
    provider_id: str
    model_name: str
    confidence: str
    error: str = None

@router.post("/check")
async def check_model_capability(
    request: CapabilityCheckRequest,
    db: Session = Depends(get_db)
):
    """
    检测模型的图像理解能力
    使用128x128红色图片测试，要求模型识别出颜色
    只有真正识别出"红色"的模型才会被判定为支持视觉能力
    """
    try:
        start_time = time.time()

        # 获取Provider配置
        provider_repo = ProviderRepository(db)
        provider = provider_repo.find_by_id(request.provider_id)

        if not provider or not provider.api_key:
            return R.error(msg="Provider配置不存在或API密钥未配置", code=404)

        # 创建模型能力检测器
        detector = ModelCapabilityDetector()

        # 构建Provider配置
        provider_config = {
            'id': request.provider_id,
            'model_name': request.model_name,
            'api_key': provider.api_key,
            'base_url': provider.base_url or ""
        }

        # 调用检测方法（使用图像输入测试）
        detection_result = await detector._test_model_capability(provider_config)

        response_time = int((time.time() - start_time) * 1000)

        # 将检测结果转换为前端需要的格式
        has_vision = detection_result.get('supports_images', False)
        error_msg = detection_result.get('error', '')

        result = {
            "provider_id": request.provider_id,
            "model_name": request.model_name,
            "has_vision_capability": has_vision,
            "confidence": "high" if has_vision else "low",
            "model_answer": detection_result.get('response_text', error_msg or '无响应'),
            "interpretation": detection_result.get('interpretation', '未能获取判定结果'),
            "response_time_ms": response_time,
            "detection_method": "red_color_recognition"
        }

        return R.success(data=result, msg="能力检测完成")

    except Exception as e:
        return R.error(msg=f"能力检测失败: {str(e)}", code=500)

@router.get("/test")
async def test_capability_endpoint():
    """测试能力检测端点是否可用"""
    return {"message": "模型能力检测API运行正常", "status": "active"}