"""
简化的日志配置
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
LOGS_DIR = PROJECT_ROOT / "logs"

# 确保日志目录存在
LOGS_DIR.mkdir(exist_ok=True)


def setup_logging():
    """设置项目日志配置"""

    # 生成日志文件名
    today = datetime.now().strftime("%Y-%m-%d")

    # 1. 应用主日志文件
    app_log_file = LOGS_DIR / f"app_{today}.log"
    app_handler = logging.FileHandler(app_log_file, encoding='utf-8')
    app_handler.setLevel(logging.INFO)
    app_formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    app_handler.setFormatter(app_formatter)

    # 2. 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)

    # 3. 智能截图选择器专用日志
    selector_log_file = LOGS_DIR / f"intelligent_selector_{today}.log"
    selector_handler = logging.FileHandler(selector_log_file, encoding='utf-8')
    selector_handler.setLevel(logging.DEBUG)
    selector_handler.setFormatter(app_formatter)

    # 4. OCR处理专用日志
    ocr_log_file = LOGS_DIR / f"ocr_processing_{today}.log"
    ocr_handler = logging.FileHandler(ocr_log_file, encoding='utf-8')
    ocr_handler.setLevel(logging.DEBUG)
    ocr_handler.setFormatter(app_formatter)

    # 5. AI模型交互专用日志
    ai_log_file = LOGS_DIR / f"ai_model_interaction_{today}.log"
    ai_handler = logging.FileHandler(ai_log_file, encoding='utf-8')
    ai_handler.setLevel(logging.DEBUG)
    ai_handler.setFormatter(app_formatter)

    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # 清除现有处理器
    root_logger.handlers.clear()

    # 添加通用处理器
    root_logger.addHandler(console_handler)
    root_logger.addHandler(app_handler)

    # 为特定模块添加专用日志处理器
    add_specialized_handler('app.services.intelligent_screenshot_selector', selector_handler)
    add_specialized_handler('app.services.ocr_fallback_processor', ocr_handler)
    add_specialized_handler('app.services.multimodal_ai_processor', ai_handler)
    add_specialized_handler('app.services.model_capability_detector', ai_handler)

    # 设置第三方库日志级别
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)

    print("日志系统初始化完成")
    print(f"   日志目录: {LOGS_DIR}")
    print(f"   应用日志: {app_log_file}")
    print(f"   智能选择器日志: {selector_log_file}")
    print(f"   OCR处理日志: {ocr_log_file}")
    print(f"   AI交互日志: {ai_log_file}")


def add_specialized_handler(logger_name: str, handler: logging.Handler):
    """为特定logger添加专用处理器"""
    logger = logging.getLogger(logger_name)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)


def get_log_files() -> dict:
    """获取当前日志文件列表"""
    log_files = {}

    # 主日志文件
    today = datetime.now().strftime("%Y-%m-%d")
    main_files = [
        ("应用主日志", f"app_{today}.log"),
        ("智能选择器日志", f"intelligent_selector_{today}.log"),
        ("OCR处理日志", f"ocr_processing_{today}.log"),
        ("AI交互日志", f"ai_model_interaction_{today}.log"),
    ]

    for name, filename in main_files:
        file_path = LOGS_DIR / filename
        if file_path.exists():
            stat = file_path.stat()
            log_files[name] = {
                'path': str(file_path),
                'size': f"{stat.st_size / 1024:.1f} KB",
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            }

    return log_files


def tail_log_file(log_type: str, lines: int = 50) -> list:
    """读取日志文件的最后几行"""
    today = datetime.now().strftime("%Y-%m-%d")

    log_files = {
        'app': f"app_{today}.log",
        'selector': f"intelligent_selector_{today}.log",
        'ocr': f"ocr_processing_{today}.log",
        'ai': f"ai_model_interaction_{today}.log",
    }

    filename = log_files.get(log_type)
    if not filename:
        return [f"未知的日志类型: {log_type}"]

    file_path = LOGS_DIR / filename
    if not file_path.exists():
        return [f"日志文件不存在: {file_path}"]

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            return all_lines[-lines:] if len(all_lines) > lines else all_lines
    except Exception as e:
        return [f"读取日志文件失败: {e}"]


# 不自动初始化，需要手动调用