"""
测试图像管理器
"""

import os
import requests
from typing import List
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TestImageManager:
    """测试图像管理器"""

    def __init__(self):
        self.test_image_dir = os.path.join(settings.BASE_DIR, "static", "test_images")
        os.makedirs(self.test_image_dir, exist_ok=True)

    def ensure_test_images(self) -> bool:
        """确保测试图像存在"""
        # 定义测试图像（使用在线图片作为测试）
        test_images = {
            "dog": "https://images.unsplash.com/photo-1552053831-71594a27632d?w=400&h=300&fit=crop",
            "cat": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=400&h=300&fit=crop",
            "car": "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400&h=300&fit=crop",
            "building": "https://images.unsplash.com/photo-1448630360428-65456885c650?w=400&h=300&fit=crop"
        }

        all_exist = True
        for name, url in test_images.items():
            image_path = os.path.join(self.test_image_dir, f"{name}.jpg")
            if not os.path.exists(image_path):
                logger.info(f"[TestImageManager] 下载测试图像: {name}")
                if self._download_image(url, image_path):
                    logger.info(f"[TestImageManager] 测试图像下载成功: {name}")
                else:
                    logger.error(f"[TestImageManager] 测试图像下载失败: {name}")
                    all_exist = False
            else:
                logger.info(f"[TestImageManager] 测试图像已存在: {name}")

        return all_exist

    def _download_image(self, url: str, path: str) -> bool:
        """下载图像"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            with open(path, 'wb') as f:
                f.write(response.content)

            return True
        except Exception as e:
            logger.error(f"[TestImageManager] 下载图像失败: {e}")
            return False

    def get_test_images(self) -> List[str]:
        """获取测试图像列表"""
        images = []
        for filename in ["dog.jpg", "cat.jpg", "car.jpg", "building.jpg"]:
            path = os.path.join(self.test_image_dir, filename)
            if os.path.exists(path):
                images.append(path)
        return images

    def get_image_status(self) -> dict:
        """获取图像状态信息"""
        test_images = ["dog.jpg", "cat.jpg", "car.jpg", "building.jpg"]
        status = {}

        for image_name in test_images:
            image_path = os.path.join(self.test_image_dir, image_name)
            status[image_name] = {
                "exists": os.path.exists(image_path),
                "path": image_path,
                "size": os.path.getsize(image_path) if os.path.exists(image_path) else 0
            }

        return status

    def create_placeholder_images(self) -> bool:
        """创建占位符图像（如果下载失败）"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import textwrap

            # 创建占位符图像配置
            placeholder_configs = {
                "dog": {
                    "text": "DOG",
                    "color": (139, 69, 19),  # 棕色
                    "bg_color": (255, 248, 220)  # 浅黄色
                },
                "cat": {
                    "text": "CAT",
                    "color": (70, 130, 180),  # 钢色
                    "bg_color": (240, 248, 255)  # 浅蓝色
                },
                "car": {
                    "text": "CAR",
                    "color": (34, 139, 34),   # 绿色
                    "bg_color": (240, 255, 240)  # 浅绿色
                },
                "building": {
                    "text": "BUILDING",
                    "color": (128, 0, 128),    # 紫色
                    "bg_color": (248, 240, 255)  # 浅紫色
                }
            }

            all_success = True

            for name, config in placeholder_configs.items():
                image_path = os.path.join(self.test_image_dir, f"{name}.jpg")

                if not os.path.exists(image_path):
                    try:
                        # 创建400x300的图像
                        img = Image.new('RGB', (400, 300), config["bg_color"])
                        draw = ImageDraw.Draw(img)

                        # 尝试使用系统字体
                        try:
                            font = ImageFont.truetype("arial.ttf", 60)
                        except:
                            try:
                                font = ImageFont.load_default()
                            except:
                                font = None

                        # 绘制文本
                        text = config["text"]
                        if font:
                            bbox = draw.textbbox((0, 0), text, font=font)
                            text_width = bbox[2] - bbox[0]
                            text_height = bbox[3] - bbox[1]
                        else:
                            text_width = len(text) * 30
                            text_height = 60

                        # 计算位置（居中）
                        x = (400 - text_width) // 2
                        y = (300 - text_height) // 2

                        # 绘制文本
                        draw.text((x, y), text, fill=config["color"], font=font)

                        # 添加边框
                        draw.rectangle([10, 10, 390, 290], outline=config["color"], width=3)

                        # 保存图像
                        img.save(image_path, "JPEG", quality=85)
                        logger.info(f"[TestImageManager] 创建占位符图像: {name}")

                    except Exception as e:
                        logger.error(f"[TestImageManager] 创建占位符图像失败 {name}: {e}")
                        all_success = False

            return all_success

        except ImportError:
            logger.warning("[TestImageManager] PIL未安装，无法创建占位符图像")
            return False
        except Exception as e:
            logger.error(f"[TestImageManager] 创建占位符图像失败: {e}")
            return False

    def check_images_ready(self) -> dict:
        """检查图像是否准备好进行测试"""
        status = self.get_image_status()
        all_exist = all(info["exists"] for info in status.values())

        return {
            "ready": all_exist,
            "missing_images": [name for name, info in status.items() if not info["exists"]],
            "total_images": len(status),
            "available_images": len([name for name, info in status.items() if info["exists"]]),
            "status": status
        }


# 全局实例
test_image_manager = TestImageManager()

# 应用启动时检查图像
def initialize_test_images():
    """初始化测试图像"""
    logger.info("[TestImageManager] 初始化测试图像...")

    if test_image_manager.ensure_test_images():
        logger.info("[TestImageManager] 所有测试图像已准备就绪")
    else:
        logger.warning("[TestImageManager] 部分测试图像缺失，尝试创建占位符图像...")
        test_image_manager.create_placeholder_images()