"""
Main Application Entry Point
包含静态文件服务和智能截图功能
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.config.settings import settings
from app.middleware.cors_middleware import add_cors_middleware
from app.middleware.error_middleware import add_error_middleware
from app.config.database import init_db
from app.controllers import note_router, provider_router, model_router, system_router, transcribe_router, image_test_router, model_capability_router
from app.utils.logger import get_logger
import os

# 初始化我们的日志系统
try:
    from simple_logging_config import setup_logging
    setup_logging()
    print("详细日志系统已启用")
except Exception as e:
    print(f"日志系统初始化失败，使用默认日志: {e}")

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("启动 MyNote 后端应用...")

    # Initialize database
    init_db()
    logger.info("数据库初始化完成")

    # 创建必要的目录
    try:
        # 创建截图输出目录
        os.makedirs(settings.screenshot_full_output_dir, exist_ok=True)
        os.makedirs(settings.screenshot_full_temp_dir, exist_ok=True)
        os.makedirs(settings.static_full_dir, exist_ok=True)

        logger.info(f"截图输出目录: {settings.screenshot_full_output_dir}")
        logger.info(f"临时截图目录: {settings.screenshot_full_temp_dir}")
        logger.info(f"静态文件目录: {settings.static_full_dir}")

    except Exception as e:
        logger.error(f"创建目录失败: {e}")

    # Preload Whisper models
    try:
        from app.services.service_manager import get_service_manager
        service_manager = get_service_manager()

        # Preload commonly used models
        models_to_preload = ["base"]  # Start with base model for good performance
        logger.info(f"预加载Whisper模型: {models_to_preload}")

        # Run preloading in a separate thread to not block startup
        import asyncio
        import threading

        def preload_models():
            service_manager.preload_models(models_to_preload)

        preload_thread = threading.Thread(target=preload_models, daemon=True)
        preload_thread.start()

        logger.info("Whisper模型后台预加载已启动")

    except Exception as e:
        logger.error(f"预加载Whisper模型失败: {e}")
        logger.warning("应用将继续运行，但首次转录可能会较慢")

    # Note: 不再需要测试图像初始化，使用简化的问答方式进行模型能力检测

    yield

    logger.info("关闭 MyNote 后端应用...")


def create_app() -> FastAPI:
    """Create and configure FastAPI application with screenshot support"""
    app = FastAPI(
        title="MyNote Backend with Smart Screenshots",
        description="AI-powered video note generation system with intelligent screenshot functionality",
        version="2.0.0",
        lifespan=lifespan
    )

    # Add middleware
    add_cors_middleware(app)
    add_error_middleware(app)

    # Register routers
    app.include_router(note_router, prefix="/api")
    app.include_router(provider_router, prefix="/api")
    app.include_router(model_router, prefix="/api")
    app.include_router(system_router, prefix="/api")
    app.include_router(transcribe_router, prefix="/api")
    app.include_router(image_test_router, prefix="/api")
    app.include_router(model_capability_router, prefix="/api")

    # Add static file serving for screenshots
    try:
        # Mount static files directory
        app.mount(
            settings.STATIC_URL_PREFIX,
            StaticFiles(directory=settings.static_full_dir),
            name="static"
        )
        logger.info(f"静态文件服务已挂载: {settings.STATIC_URL_PREFIX} -> {settings.static_full_dir}")

        # Add root health check
        @app.get("/")
        async def root():
            return {
                "message": "MyNote Backend API",
                "version": "2.0.0",
                "features": ["AI转录", "智能截图", "实时状态", "多平台支持"],
                "endpoints": {
                    "docs": "/docs",
                    "health": "/api/sys_health",
                    "static": settings.STATIC_URL_PREFIX
                }
            }

    except Exception as e:
        logger.error(f"挂载静态文件服务失败: {e}")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )