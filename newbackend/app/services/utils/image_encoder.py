"""
图像Base64编码工具
基于comprehensive_test2.py验证成功的实现
"""

import os
import base64
import io
from typing import Optional, Dict, Any
import logging
from PIL import Image
from app.config.settings import settings

logger = logging.getLogger(__name__)


class ImageEncoder:
    """图像Base64编码器，支持优化和压缩"""

    def __init__(self, max_size: int = None, quality: int = None):
        """
        初始化图像编码器

        Args:
            max_size: 图像最大尺寸，默认从配置读取
            quality: JPEG压缩质量，默认从配置读取
        """
        self.max_size = max_size or settings.IMAGE_MAX_SIZE
        self.quality = quality or settings.IMAGE_COMPRESSION_QUALITY

        logger.info(f"图像编码器初始化: 最大尺寸={self.max_size}, 压缩质量={self.quality}")

    def encode_image_to_base64(self, image_path: str) -> Optional[str]:
        """
        将图像编码为Base64格式，自动优化尺寸

        Args:
            image_path: 图像文件路径

        Returns:
            Base64编码的图像字符串，失败返回None
        """
        try:
            if not os.path.exists(image_path):
                logger.warning(f"图片文件不存在: {image_path}")
                return None

            # 记录原始图像信息
            original_size = os.path.getsize(image_path)
            logger.debug(f"开始编码图像: {image_path}, 原始大小: {original_size / 1024 / 1024:.2f}MB")

            with Image.open(image_path) as img:
                # 转换为RGB模式
                original_mode = img.mode
                original_size_pixels = img.size

                if img.mode != 'RGB':
                    logger.debug(f"图像模式转换: {original_mode} -> RGB")
                    img = img.convert('RGB')

                # 智能压缩图片尺寸
                width, height = img.size
                max_dimension = max(width, height)

                if max_dimension > self.max_size:
                    # 计算最优尺寸比例
                    ratio = self.max_size / max_dimension
                    new_width = int(width * ratio)
                    new_height = int(height * ratio)

                    logger.debug(f"图像尺寸调整: {width}x{height} -> {new_width}x{new_height} (比例: {ratio:.3f})")
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                else:
                    logger.debug(f"图像尺寸无需调整: {width}x{height} (最大: {self.max_size})")

                # 编码为JPEG格式
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=self.quality, optimize=True)
                img_str = base64.b64encode(buffer.getvalue()).decode()

                # 计算压缩统计
                compressed_size = len(img_str) / 1024 / 1024  # MB
                compression_ratio = (original_size - len(img_str)) / original_size * 100 if original_size > 0 else 0

                logger.debug(f"图像编码完成: {os.path.basename(image_path)}")
                logger.debug(f"  原始: {original_size / 1024 / 1024:.2f}MB ({original_mode}, {original_size_pixels[0]}x{original_size_pixels[1]})")
                logger.debug(f"  压缩: {compressed_size:.2f}MB (压缩率: {compression_ratio:.1f}%)")
                logger.debug(f"  Base64长度: {len(img_str)} 字符")

                return f"data:image/jpeg;base64,{img_str}"

        except Exception as e:
            logger.error(f"图像编码失败 {image_path}: {e}", exc_info=True)
            return None

    def analyze_image_info(self, image_path: str) -> Dict[str, Any]:
        """
        分析图像基本信息

        Args:
            image_path: 图像文件路径

        Returns:
            图像信息字典
        """
        try:
            if not os.path.exists(image_path):
                logger.warning(f"图片文件不存在: {image_path}")
                return {
                    'path': image_path,
                    'exists': False,
                    'error': '文件不存在'
                }

            with Image.open(image_path) as img:
                file_size = os.path.getsize(image_path)

                info = {
                    'path': image_path,
                    'filename': os.path.basename(image_path),
                    'exists': True,
                    'size': [img.width, img.height],
                    'mode': img.mode,
                    'format': img.format,
                    'file_size': file_size,
                    'file_size_mb': round(file_size / 1024 / 1024, 2),
                    'aspect_ratio': round(img.width / img.height, 3) if img.height > 0 else 0,
                    'megapixels': round((img.width * img.height) / 1000000, 2)
                }

                logger.debug(f"图像分析完成: {info['filename']}")
                logger.debug(f"  尺寸: {info['size'][0]}x{info['size'][1]}, 格式: {info['format']}")
                logger.debug(f"  文件大小: {info['file_size_mb']}MB, 像素: {info['megapixels']}MP")

                return info

        except Exception as e:
            logger.error(f"图像信息分析失败 {image_path}: {e}", exc_info=True)
            return {
                'path': image_path,
                'exists': True,
                'error': str(e)
            }

    def encode_multiple_images(self, image_paths: list) -> Dict[str, Any]:
        """
        批量编码多个图像

        Args:
            image_paths: 图像路径列表

        Returns:
            编码结果字典
        """
        logger.info(f"开始批量编码 {len(image_paths)} 张图像")

        results = {
            'total': len(image_paths),
            'success': 0,
            'failed': 0,
            'images': [],
            'errors': []
        }

        for image_path in image_paths:
            try:
                # 分析图像信息
                info = self.analyze_image_info(image_path)

                if not info.get('exists', False):
                    results['failed'] += 1
                    results['errors'].append(f"文件不存在: {image_path}")
                    results['images'].append({
                        'path': image_path,
                        'success': False,
                        'error': '文件不存在',
                        'info': info
                    })
                    continue

                # 编码图像
                base64_data = self.encode_image_to_base64(image_path)

                if base64_data:
                    results['success'] += 1
                    results['images'].append({
                        'path': image_path,
                        'success': True,
                        'base64_data': base64_data,
                        'info': info
                    })
                    logger.debug(f"批量编码成功: {os.path.basename(image_path)}")
                else:
                    results['failed'] += 1
                    results['errors'].append(f"编码失败: {image_path}")
                    results['images'].append({
                        'path': image_path,
                        'success': False,
                        'error': '编码失败',
                        'info': info
                    })
                    logger.warning(f"批量编码失败: {os.path.basename(image_path)}")

            except Exception as e:
                results['failed'] += 1
                error_msg = f"处理异常: {image_path} - {str(e)}"
                results['errors'].append(error_msg)
                results['images'].append({
                    'path': image_path,
                    'success': False,
                    'error': str(e),
                    'info': None
                })
                logger.error(error_msg)

        # 记录批量处理统计
        success_rate = results['success'] / results['total'] * 100 if results['total'] > 0 else 0
        logger.info(f"批量编码完成: 成功 {results['success']}/{results['total']} ({success_rate:.1f}%)")

        if results['failed'] > 0:
            logger.warning(f"编码失败的图像: {results['failed']} 个")
            for error in results['errors']:
                logger.warning(f"  {error}")

        return results

    def get_optimal_encoding_params(self, image_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据图像信息获取最优编码参数

        Args:
            image_info: 图像信息字典

        Returns:
            最优编码参数
        """
        try:
            file_size_mb = image_info.get('file_size_mb', 0)
            megapixels = image_info.get('megapixels', 0)

            # 根据文件大小和像素数动态调整参数
            if file_size_mb > 10 or megapixels > 5:
                # 大文件：更激进的压缩
                optimal_size = min(1024, self.max_size)
                optimal_quality = min(75, self.quality)
            elif file_size_mb > 5 or megapixels > 2:
                # 中等文件：平衡压缩
                optimal_size = min(1536, self.max_size)
                optimal_quality = min(80, self.quality)
            else:
                # 小文件：保持较高质量
                optimal_size = self.max_size
                optimal_quality = self.quality

            return {
                'max_size': optimal_size,
                'quality': optimal_quality,
                'reason': f"基于文件大小({file_size_mb}MB)和像素数({megapixels}MP)的动态调整"
            }

        except Exception as e:
            logger.error(f"获取最优编码参数失败: {e}")
            return {
                'max_size': self.max_size,
                'quality': self.quality,
                'reason': "使用默认参数"
            }

    @staticmethod
    def decode_base64_size(base64_data: str) -> Optional[int]:
        """
        估算Base64图像数据的原始大小

        Args:
            base64_data: Base64编码的图像数据

        Returns:
            估算的原始文件大小（字节）
        """
        try:
            # 移除data:image/jpeg;base64,前缀
            if 'base64,' in base64_data:
                base64_content = base64_data.split('base64,')[1]
            else:
                base64_content = base64_data

            # Base64编码大约比原始数据大33%
            estimated_size = len(base64_content) * 3 // 4
            return estimated_size

        except Exception as e:
            logger.error(f"估算Base64大小失败: {e}")
            return None


def create_image_encoder(max_size: int = None, quality: int = None) -> ImageEncoder:
    """
    创建图像编码器实例

    Args:
        max_size: 最大图像尺寸
        quality: 压缩质量

    Returns:
        ImageEncoder实例
    """
    encoder = ImageEncoder(max_size=max_size, quality=quality)
    logger.info("图像编码器实例创建完成")
    return encoder