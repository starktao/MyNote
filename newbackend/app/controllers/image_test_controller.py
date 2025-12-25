"""
图像识别测试API控制器
"""

import os
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.services.image_test_service import ImageTestService
from app.infrastructure.database.connection import get_db
from app.utils.response import R
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Image Test"])

image_test_service = ImageTestService()


@router.post("/image_test/create_session")
async def create_test_session(request: Dict[str, str], db: Session = Depends(get_db)):
    """创建图像识别测试会话"""
    try:
        provider_id = request.get("provider_id")
        model_name = request.get("model_name")

        if not provider_id or not model_name:
            return R.error("需要提供provider_id和model_name", 400)

        session_id = image_test_service.create_test_session(provider_id, model_name, db)

        logger.info(f"[ImageTestController] 创建测试会话成功: {session_id}")
        return R.success({
            "session_id": session_id,
            "message": "测试会话创建成功"
        })

    except ValueError as e:
        logger.error(f"[ImageTestController] 创建测试会话失败: {e}")
        return R.error(str(e), 400)
    except Exception as e:
        logger.error(f"[ImageTestController] 创建测试会话异常: {e}")
        return R.error(f"创建测试会话失败: {str(e)}", 500)


@router.post("/image_test/run_test")
async def run_vision_test(request: Dict[str, str], db: Session = Depends(get_db)):
    """运行图像识别测试"""
    try:
        session_id = request.get("session_id")
        if not session_id:
            return R.error("需要提供session_id", 400)

        logger.info(f"[ImageTestController] 开始运行图像测试: {session_id}")
        result = await image_test_service.run_vision_test(session_id, db)

        logger.info(f"[ImageTestController] 图像测试完成: {session_id}, 通过率: {result['pass_rate']}%")
        return R.success(result)

    except ValueError as e:
        logger.error(f"[ImageTestController] 运行测试失败: {e}")
        return R.error(str(e), 400)
    except Exception as e:
        logger.error(f"[ImageTestController] 运行测试异常: {e}")
        return R.error(f"运行测试失败: {str(e)}", 500)


@router.get("/image_test/session/{session_id}")
async def get_test_session(session_id: str, db: Session = Depends(get_db)):
    """获取测试会话信息"""
    try:
        session = image_test_service.get_test_session(session_id, db)
        if not session:
            return R.error("测试会话不存在", 404)

        return R.success(session)

    except Exception as e:
        logger.error(f"[ImageTestController] 获取测试会话失败: {e}")
        return R.error(f"获取测试会话失败: {str(e)}", 500)


@router.get("/image_test/sessions")
async def get_test_sessions(db: Session = Depends(get_db)):
    """获取所有测试会话列表"""
    try:
        from app.models.database.image_test import ImageTestSession

        sessions = db.query(ImageTestSession).order_by(ImageTestSession.created_at.desc()).all()

        sessions_data = []
        for session in sessions:
            sessions_data.append({
                "session_id": session.id,
                "provider_id": session.provider_id,
                "model_name": session.model_name,
                "status": session.status,
                "total_tests": session.total_tests,
                "passed_tests": session.passed_tests,
                "failed_tests": session.failed_tests,
                "pass_rate": session.pass_rate,
                "start_time": session.start_time.isoformat() if session.start_time else None,
                "end_time": session.end_time.isoformat() if session.end_time else None,
                "created_at": session.created_at.isoformat() if session.created_at else None
            })

        return R.success({
            "sessions": sessions_data,
            "total": len(sessions_data)
        })

    except Exception as e:
        logger.error(f"[ImageTestController] 获取测试会话列表失败: {e}")
        return R.error(f"获取测试会话列表失败: {str(e)}", 500)


@router.delete("/image_test/session/{session_id}")
async def delete_test_session(session_id: str, db: Session = Depends(get_db)):
    """删除测试会话"""
    try:
        from app.models.database.image_test import ImageTestSession, ImageTestResult

        # 检查会话是否存在
        session = db.query(ImageTestSession).filter(ImageTestSession.id == session_id).first()
        if not session:
            return R.error("测试会话不存在", 404)

        # 删除相关的测试结果
        db.query(ImageTestResult).filter(ImageTestResult.session_id == session_id).delete()

        # 删除会话
        db.delete(session)
        db.commit()

        logger.info(f"[ImageTestController] 删除测试会话成功: {session_id}")
        return R.success({
            "session_id": session_id,
            "message": "测试会话删除成功"
        })

    except Exception as e:
        logger.error(f"[ImageTestController] 删除测试会话失败: {e}")
        return R.error(f"删除测试会话失败: {str(e)}", 500)


@router.get("/image_test/status")
async def get_test_status(db: Session = Depends(get_db)):
    """获取图像识别测试功能状态"""
    try:
        from app.models.database.image_test import ImageTestSession

        # 获取测试图像状态
        test_images_status = []
        test_image_dir = "static/test_images"
        test_images = ["dog.jpg", "cat.jpg", "car.jpg", "building.jpg"]

        for image_name in test_images:
            image_path = f"{test_image_dir}/{image_name}"
            exists = os.path.exists(image_path)
            test_images_status.append({
                "name": image_name,
                "exists": exists,
                "path": image_path
            })

        # 获取测试统计
        total_sessions = 0
        completed_sessions = 0

        try:
            total_sessions = db.query(ImageTestSession).count()
            completed_sessions = db.query(ImageTestSession).filter(
                ImageTestSession.status == "completed"
            ).count()
        except:
            pass

        return R.success({
            "test_images": test_images_status,
            "all_images_exist": all(img["exists"] for img in test_images_status),
            "statistics": {
                "total_sessions": total_sessions,
                "completed_sessions": completed_sessions
            },
            "ready_to_test": all(img["exists"] for img in test_images_status)
        })

    except Exception as e:
        logger.error(f"[ImageTestController] 获取测试状态失败: {e}")
        return R.error(f"获取测试状态失败: {str(e)}", 500)