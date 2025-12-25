"""
System Controller - System Health and Status
"""

from fastapi import APIRouter, Depends, Query
from app.models.dto.system_dto import SystemStatusDTO, HealthCheckDTO
from app.utils.response import R
from app.config.settings import settings
from app.config.database import engine
from app.utils.health_check import test_ai_connection
from datetime import datetime
import time

router = APIRouter(tags=["System"])


@router.get("/health", response_model=HealthCheckDTO)
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        db_healthy = True
        db_message = "Database connection successful"
    except Exception as e:
        db_healthy = False
        db_message = f"Database connection failed: {str(e)}"

    checks = {
        "database": db_healthy,
        "server": True
    }

    details = {
        "database": db_message,
        "server": "Server is running"
    }

    overall_healthy = all(checks.values())

    return HealthCheckDTO(
        healthy=overall_healthy,
        checks=checks,
        details=details
    )


@router.get("/status", response_model=SystemStatusDTO)
async def system_status():
    """System status endpoint"""
    uptime = time.time() - start_time

    return SystemStatusDTO(
        status="healthy",
        uptime=f"{uptime:.2f} seconds",
        version="2.0.0",
        database_status="connected",
        external_services={
            "llm": "unknown",
            "transcription": "unknown"
        }
    )


@router.get("/")
async def root():
    """Root endpoint"""
    return R.success({
        "message": "MyNote Backend API v2.0.0",
        "docs": "/docs",
        "health": "/api/health",
        "status": "/api/status"
    })


@router.get("/sys_health/test_ai")
def test_ai_connection_api(
    provider_id: str = Query(..., description="Provider ID"),
    model_name: str = Query(..., description="Model name")
):
    """Test AI connection API"""
    try:
        result = test_ai_connection(provider_id, model_name)
        if result["status"] == "[OK]":
            return R.success({"message": result["message"]})
        else:
            return R.error(result["message"])
    except Exception as e:
        return R.error(f"AI connection test failed: {e}")


@router.get("/db_pool_status")
async def get_db_pool_status():
    """获取数据库连接池状态监控"""
    try:
        # 使用正确的数据库引擎路径
        from app.config.database import engine

        pool = engine.pool
        total_connections = pool.size() + pool.overflow()
        active_connections = pool.checkedout()

        status = {
            "pool_size": pool.size(),
            "overflow": pool.overflow(),
            "checked_in": pool.checkedin(),
            "checked_out": active_connections,
            "total_connections": total_connections,
            "usage_rate": f"{(active_connections / total_connections * 100):.1f}%" if total_connections > 0 else "0%",
            "status": "healthy" if active_connections < total_connections * 0.8 else "warning"
        }

        return R.success(status)
    except Exception as e:
        return R.error(f"获取连接池状态失败: {str(e)}")


# Application start time for uptime calculation
start_time = time.time()