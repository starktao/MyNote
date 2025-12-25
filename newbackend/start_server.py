#!/usr/bin/env python3
"""
启动后端服务器并启用详细日志
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    print("启动 MyNote 后端服务器...")

    # 检查日志系统
    try:
        from simple_logging_config import setup_logging, get_log_files
        setup_logging()
        print("日志系统初始化成功")

        log_files = get_log_files()
        if log_files:
            print("\n📁 日志文件位置:")
            for name, info in log_files.items():
                print(f"  {name}: {info['path']}")

        print("\n🔍 启动后查看日志:")
        print("  python show_logs.py")
        print("  tail -f logs/app_$(date +%Y-%m-%d).log")

    except Exception as e:
        print(f"⚠️ 日志系统初始化失败: {e}")

    # 启动FastAPI应用
    try:
        import uvicorn
        from app.config.settings import settings

        print(f"\n🚀 启动服务器 http://{settings.BACKEND_HOST}:{settings.BACKEND_PORT}")
        print("📖 API文档: http://localhost:8000/docs")
        print("\n按 Ctrl+C 停止服务器")

        uvicorn.run(
            "app.main:app",
            host=settings.BACKEND_HOST,
            port=settings.BACKEND_PORT,
            reload=True,
            log_level="info"
        )

    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")

if __name__ == "__main__":
    main()