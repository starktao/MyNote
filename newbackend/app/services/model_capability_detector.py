"""
模型能力检测器
基于comprehensive_test2.py验证成功的实现
检测AI模型是否支持图像处理能力
"""

import os
import time
import base64
import io
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from PIL import Image
from openai import OpenAI

from app.config.settings import settings
from app.services.utils.image_encoder import ImageEncoder

logger = logging.getLogger(__name__)


class ModelCapabilityDetector:
    """模型能力检测器，支持缓存和并发检测"""

    def __init__(self):
        """初始化模型能力检测器"""
        self.capability_cache = {}
        self.cache_ttl = settings.CAPABILITY_CACHE_TTL
        self.image_encoder = ImageEncoder()

        logger.info("模型能力检测器初始化完成")
        logger.info(f"缓存TTL: {self.cache_ttl}秒")

    async def detect_capability_concurrent(self, provider_configs: List[Dict]) -> Dict[str, Any]:
        """
        并发检测多个Provider的模型能力

        Args:
            provider_configs: Provider配置列表

        Returns:
            检测结果字典
        """
        logger.info(f"开始并发检测 {len(provider_configs)} 个Provider的模型能力")

        start_time = time.time()
        results = []

        for config in provider_configs:
            try:
                # 并发检测单个Provider
                result = await self._detect_single_capability_cached(config)
                results.append(result)
                logger.debug(f"Provider {config.get('id', 'unknown')} 能力检测完成")

            except Exception as e:
                logger.error(f"Provider {config.get('id', 'unknown')} 能力检测异常: {e}", exc_info=True)
                # 异常情况下认为不支持图像
                results.append({
                    'provider_id': config.get('id', 'unknown'),
                    'model_name': config.get('model_name', 'unknown'),
                    'supports_images': False,
                    'confidence': 0.0,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })

        processing_time = time.time() - start_time
        successful_count = sum(1 for r in results if r.get('supports_images', False))

        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_providers': len(provider_configs),
            'successful_providers': len(results),
            'image_capable_providers': successful_count,
            'processing_time': processing_time,
            'results': results
        }

        logger.info(f"并发能力检测完成: {successful_count}/{len(provider_configs)} 个支持图像")
        logger.info(f"检测耗时: {processing_time:.2f}秒")

        return summary

    async def _detect_single_capability_cached(self, provider_config: Dict) -> Dict[str, Any]:
        """
        带缓存的单个Provider能力检测

        Args:
            provider_config: Provider配置

        Returns:
            检测结果
        """
        provider_id = provider_config.get('id', 'unknown')
        model_name = provider_config.get('model_name', 'unknown')
        cache_key = f"{provider_id}_{model_name}"

        # 检查缓存
        if cache_key in self.capability_cache:
            cached_result = self.capability_cache[cache_key]
            cache_age = time.time() - cached_result['timestamp']

            if cache_age < self.cache_ttl:
                logger.debug(f"使用缓存的能力检测结果: {cache_key}")
                logger.debug(f"缓存年龄: {cache_age:.1f}秒, TTL: {self.cache_ttl}秒")

                # 记录缓存命中
                logger.info(f"缓存访问 - capability: {cache_key} (命中)")

                # 返回缓存结果，但更新时间戳
                return {
                    **cached_result['result'],
                    'cache_hit': True,
                    'cache_age': cache_age
                }
            else:
                logger.debug(f"缓存已过期: {cache_key} (年龄: {cache_age:.1f}秒)")
                del self.capability_cache[cache_key]

        # 执行实际检测
        logger.info(f"执行能力检测: {cache_key}")
        result = await self._test_model_capability(provider_config)

        # 缓存结果
        self.capability_cache[cache_key] = {
            'result': result,
            'timestamp': time.time()
        }

        # 记录缓存未命中
        logger.info(f"缓存访问 - capability: {cache_key} (未命中)")

        return {
            **result,
            'cache_hit': False
        }

    async def _test_model_capability(self, provider_config: Dict) -> Dict[str, Any]:
        """
        基于comprehensive_test2.py的单测试用例检测

        Args:
            provider_config: Provider配置

        Returns:
            能力检测结果
        """
        provider_id = provider_config.get('id', 'unknown')
        model_name = provider_config.get('model_name', 'unknown')
        api_key = provider_config.get('api_key')
        base_url = provider_config.get('base_url')

        if not all([api_key, base_url, model_name]):
            error_msg = f"Provider配置不完整: api_key={bool(api_key)}, base_url={bool(base_url)}, model_name={bool(model_name)}"
            logger.warning(f"{provider_id} - {error_msg}")
            return {
                'provider_id': provider_id,
                'model_name': model_name,
                'supports_images': False,
                'confidence': 0.0,
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            }

        try:
            logger.info(f"开始测试 {model_name} 的图像处理能力...")

            # 创建简单的测试图像（1x1像素的PNG）
            test_image_base64 = self._create_test_image()

            # 构建测试消息（与qianwentest.py一致）
            content = [
                {
                    "type": "image_url",
                    "image_url": {"url": test_image_base64}
                },
                {"type": "text", "text": "这张图片是什么颜色？请只回答颜色名称。如果不能看到请明确说明。"}
            ]

            messages = [{"role": "user", "content": content}]

            # 调用模型API
            client = OpenAI(api_key=api_key, base_url=base_url)

            logger.debug(f"发送能力检测请求到 {model_name}")
            start_time = time.time()

            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=50,
                temperature=0.1,
                timeout=settings.MULTIMODAL_TIMEOUT
            )

            response_time = time.time() - start_time
            response_text = response.choices[0].message.content

            logger.debug(f"收到响应 (耗时: {response_time:.2f}秒)")
            logger.debug(f"模型回答: {response_text}")

            # 语义判断：检查模型是否真正识别出颜色
            vision_result = self._is_red_answer(response_text)
            interpretation = self._interpret_answer(response_text, vision_result)

            if vision_result:
                logger.info(f"{model_name} 能力检测完成: 支持图像（识别出红色）")
            else:
                logger.info(f"{model_name} 能力检测完成: 不支持图像（未识别出红色）")

            return {
                'provider_id': provider_id,
                'model_name': model_name,
                'supports_images': vision_result,
                'confidence': 1.0 if vision_result else 0.0,
                'response_text': response_text,
                'interpretation': interpretation,
                'response_time': response_time,
                'detection_time': response_time,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            # 如果出现异常，直接认为不支持图像
            error_msg = str(e)
            logger.warning(f"{model_name} 图像能力检测异常，认为不支持图像: {error_msg}")

            # 分类错误类型
            error_type = self._classify_error(error_msg)

            return {
                'provider_id': provider_id,
                'model_name': model_name,
                'supports_images': False,
                'confidence': 0.0,
                'error': error_msg,
                'error_type': error_type,
                'timestamp': datetime.now().isoformat()
            }

    def _create_test_image(self) -> str:
        """
        创建测试用的红色图像（128x128像素）
        用于真正的视觉能力检测，而不仅仅是API兼容性测试

        Returns:
            Base64编码的测试图像
        """
        try:
            # 创建一个128x128像素的纯红色图像（与qianwentest.py一致）
            img = Image.new('RGB', (128, 128), color=(255, 0, 0))

            # 转换为Base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG', optimize=True)
            img_str = base64.b64encode(buffer.getvalue()).decode()

            return f"data:image/png;base64,{img_str}"

        except Exception as e:
            logger.error(f"创建测试图像失败: {e}")
            # 返回一个最小的测试图像
            return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="

    def _is_red_answer(self, answer: str) -> bool:
        """
        判断模型是否识别出红色（与qianwentest.py一致）

        Args:
            answer: 模型的回答

        Returns:
            是否识别出红色
        """
        if not answer:
            return False

        lowered = answer.lower()
        # 检查是否包含红色相关的关键词
        has_red = "red" in lowered or "红" in answer or "赤" in answer

        # 检查是否包含否定关键词
        negative_keywords = [
            "看不到", "无法", "不能", "cannot", "unable", "can't",
            "sorry", "不好意思", "抱歉", "没有", "不", "not see",
            "无法查看", "无法识别", "无法理解", "cannot view",
            "cannot see", "无法处理", "不支持"
        ]
        has_negative = any(keyword in lowered or keyword in answer for keyword in negative_keywords)

        # 只有包含红色且不包含否定词时才判定为真正支持
        return has_red and not has_negative

    def _interpret_answer(self, answer: str, vision_result: bool) -> str:
        """
        解释判定结果

        Args:
            answer: 模型回答
            vision_result: 是否支持视觉

        Returns:
            判定解释
        """
        if not answer:
            return "模型未返回有效回答"

        lowered = answer.lower()

        if vision_result:
            # 成功识别出红色
            if "red" in lowered or "红" in answer:
                return "模型回答包含'红色'，判定为支持视觉能力"
        else:
            # 未识别出红色
            negative_keywords = [
                "看不到", "无法", "不能", "cannot", "unable", "can't",
                "sorry", "不好意思", "抱歉", "无法查看", "无法识别"
            ]

            for keyword in negative_keywords:
                if keyword in lowered or keyword in answer:
                    return f"模型回答包含'{keyword}'，判定为不支持视觉能力"

            # 没有识别出红色，也没有明确否定
            return "模型未能识别出图片颜色，判定为不支持视觉能力"

        return "判定完成"

    def _analyze_response(self, response_text: str) -> bool:
        """
        分析响应文本，判断模型是否能处理图像

        Args:
            response_text: 模型响应文本

        Returns:
            是否支持图像处理
        """
        # 期望正面响应的关键词
        positive_keywords = [
            '能看到', '看到', 'can see', 'see', '图片', '图像', '颜色', '内容',
            '描述', '清晰', '可见', '识别', 'displayed', 'visible', 'image'
        ]

        # 期望负面响应的关键词
        negative_keywords = [
            '看不到', '无法', 'cannot', 'unable', 'sorry', '不好意思', 'text only',
            '文本', 'text-only', '无法处理图片', '不能处理图像', 'not see'
        ]

        # 转换为小写以便匹配
        response_lower = response_text.lower()

        # 计算正面和负面分数
        positive_score = sum(1 for keyword in positive_keywords if keyword in response_lower)
        negative_score = sum(1 for keyword in negative_keywords if keyword in response_lower)

        logger.debug(f"响应分析: 正面分={positive_score}, 负面分={negative_score}")

        # 如果有正面关键词且负面关键词较少，认为能处理
        if positive_score > 0:
            can_process = positive_score >= negative_score
        else:
            # 如果没有正面关键词，检查是否有明确的负面关键词
            can_process = negative_score == 0

        logger.debug(f"能力判断结果: {'支持' if can_process else '不支持'}")

        return can_process

    def _classify_error(self, error_msg: str) -> str:
        """
        分类错误类型

        Args:
            error_msg: 错误消息

        Returns:
            错误类型
        """
        error_lower = error_msg.lower()

        if 'timeout' in error_lower:
            return 'timeout'
        elif 'connection' in error_lower or 'network' in error_lower:
            return 'connection'
        elif '400' in error_lower or 'bad request' in error_lower:
            return 'invalid_request'
        elif '401' in error_lower or 'unauthorized' in error_lower:
            return 'auth_error'
        elif '403' in error_lower or 'forbidden' in error_lower:
            return 'permission_error'
        elif '404' in error_lower or 'not found' in error_lower:
            return 'not_found'
        elif '429' in error_lower or 'rate limit' in error_lower:
            return 'rate_limit'
        elif '500' in error_lower or 'internal' in error_lower:
            return 'server_error'
        elif '502' in error_lower or '503' in error_lower or '504' in error_lower:
            return 'service_unavailable'
        else:
            return 'unknown'

    def clear_cache(self):
        """清除能力检测缓存"""
        cache_size = len(self.capability_cache)
        self.capability_cache.clear()
        logger.info(f"能力检测缓存已清除: {cache_size} 个条目")

    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        current_time = time.time()
        valid_entries = 0
        expired_entries = 0

        for key, cached_data in self.capability_cache.items():
            age = current_time - cached_data['timestamp']
            if age < self.cache_ttl:
                valid_entries += 1
            else:
                expired_entries += 1

        return {
            'total_entries': len(self.capability_cache),
            'valid_entries': valid_entries,
            'expired_entries': expired_entries,
            'cache_ttl': self.cache_ttl,
            'hit_rate': getattr(self, '_hit_count', 0) / max(getattr(self, '_total_requests', 1), 1) * 100
        }

    def cleanup_expired_cache(self):
        """清理过期的缓存条目"""
        current_time = time.time()
        expired_keys = []

        for key, cached_data in self.capability_cache.items():
            age = current_time - cached_data['timestamp']
            if age >= self.cache_ttl:
                expired_keys.append(key)

        for key in expired_keys:
            del self.capability_cache[key]

        if expired_keys:
            logger.info(f"清理过期缓存条目: {len(expired_keys)} 个")

    def test_specific_model(self, provider_id: str, model_name: str, api_key: str, base_url: str, test_image_path: str = None) -> Dict[str, Any]:
        """
        测试特定模型的能力（同步版本）

        Args:
            provider_id: Provider ID
            model_name: 模型名称
            api_key: API密钥
            base_url: API基础URL
            test_image_path: 测试图像路径（可选）

        Returns:
            测试结果
        """
        provider_config = {
            'id': provider_id,
            'model_name': model_name,
            'api_key': api_key,
            'base_url': base_url
        }

        # 如果提供了测试图像，添加到配置中
        if test_image_path and os.path.exists(test_image_path):
            provider_config['test_image_path'] = test_image_path
            logger.info(f"使用自定义测试图像: {test_image_path}")

        logger.info(f"开始测试特定模型能力: {provider_id}:{model_name}")

        # 使用同步方式运行异步方法
        import asyncio
        try:
            return asyncio.run(self._test_model_capability(provider_config))
        except Exception as e:
            logger.error(f"测试特定模型能力失败: {e}")
            return {
                'provider_id': provider_id,
                'model_name': model_name,
                'supports_images': False,
                'confidence': 0.0,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


def create_model_capability_detector() -> ModelCapabilityDetector:
    """创建模型能力检测器实例"""
    detector = ModelCapabilityDetector()
    logger.info("模型能力检测器实例创建完成")
    return detector