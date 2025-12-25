"""
日志配置
配置详细的日志输出到文件和控制台
"""

import os
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"

# 确保日志目录存在
LOGS_DIR.mkdir(exist_ok=True)


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""

    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
    }
    RESET = '\033[0m'

    def format(self, record):
        # 添加颜色
        if hasattr(record, 'levelname'):
            color = self.COLORS.get(record.levelname, '')
            record.levelname = f"{color}{record.levelname}{self.RESET}"

        return super().format(record)


def setup_logging():
    """设置项目日志配置"""

    # 生成日志文件名
    today = datetime.now().strftime("%Y-%m-%d")

    # 创建各种日志处理器

    # 1. 控制台处理器（彩色输出）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = ColoredFormatter(
        fmt='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)

    # 2. 应用主日志文件（按天轮转）
    app_log_file = LOGS_DIR / f"app_{today}.log"
    app_handler = TimedRotatingFileHandler(
        app_log_file,
        when='midnight',
        interval=1,
        backupCount=7,  # 保留7天的日志
        encoding='utf-8'
    )
    app_handler.setLevel(logging.INFO)
    app_formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    app_handler.setFormatter(app_formatter)

    # 3. 错误日志文件（按大小轮转）
    error_log_file = LOGS_DIR / "error.log"
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(app_formatter)

    # 4. 智能截图选择器专用日志
    selector_log_file = LOGS_DIR / f"intelligent_selector_{today}.log"
    selector_handler = TimedRotatingFileHandler(
        selector_log_file,
        when='midnight',
        interval=1,
        backupCount=7,
        encoding='utf-8'
    )
    selector_handler.setLevel(logging.DEBUG)
    selector_handler.setFormatter(app_formatter)

    # 5. OCR处理专用日志
    ocr_log_file = LOGS_DIR / f"ocr_processing_{today}.log"
    ocr_handler = TimedRotatingFileHandler(
        ocr_log_file,
        when='midnight',
        interval=1,
        backupCount=7,
        encoding='utf-8'
    )
    ocr_handler.setLevel(logging.DEBUG)
    ocr_handler.setFormatter(app_formatter)

    # 6. AI模型交互专用日志
    ai_log_file = LOGS_DIR / f"ai_model_interaction_{today}.log"
    ai_handler = TimedRotatingFileHandler(
        ai_log_file,
        when='midnight',
        interval=1,
        backupCount=7,
        encoding='utf-8'
    )
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
    root_logger.addHandler(error_handler)

    # 为特定模块添加专用日志处理器
    add_specialized_handler('app.services.intelligent_screenshot_selector', selector_handler)
    add_specialized_handler('app.services.ocr_fallback_processor', ocr_handler)
    add_specialized_handler('app.services.multimodal_ai_processor', ai_handler)
    add_specialized_handler('app.services.model_capability_detector', ai_handler)

    # 设置第三方库日志级别
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('torch').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    # 打印日志配置信息
    print(f"📝 日志系统初始化完成")
    print(f"   📁 日志目录: {LOGS_DIR}")
    print(f"   📄 应用日志: {app_log_file}")
    print(f"   ❌ 错误日志: {error_log_file}")
    print(f"   🎯 智能选择器日志: {selector_log_file}")
    print(f"   🔍 OCR处理日志: {ocr_log_file}")
    print(f"   🤖 AI交互日志: {ai_log_file}")


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
        (f"应用主日志", f"app_{today}.log"),
        ("错误日志", "error.log"),
        (f"智能选择器日志", f"intelligent_selector_{today}.log"),
        (f"OCR处理日志", f"ocr_processing_{today}.log"),
        (f"AI交互日志", f"ai_model_interaction_{today}.log"),
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
        'error': "error.log",
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


# 自动初始化日志系统
setup_logging()