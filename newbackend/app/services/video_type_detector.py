"""
视频类型自动检测服务
使用 LLM 根据视频标题判断视频类型
"""

from typing import Optional
from app.repositories.provider_repository import ProviderRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


def detect_video_type(title: str, provider_id: str, model_name: str) -> str:
    """
    使用LLM根据视频标题判断视频类型

    Args:
        title: 视频标题
        provider_id: 用户选择的提供商ID
        model_name: 用户选择的模型名称

    Returns:
        视频类型代码：'tech' | 'dialogue' | 'science' | 'review'
        失败时返回默认值 'science'
    """
    if not title or not title.strip():
        logger.warning("Empty title provided for type detection, using default 'science'")
        return "science"

    try:
        # 加载提供商信息
        with ProviderRepository() as provider_repo:
            provider = provider_repo.find_by_id(provider_id)
            if not provider:
                logger.warning(f"Provider {provider_id} not found, using default 'science'")
                return "science"

            if not provider.api_key:
                logger.warning(f"Provider {provider_id} has no API key, using default 'science'")
                return "science"

        # 构造分类 Prompt
        prompt = f"""你是视频内容分类专家。根据视频标题判断其类型，仅返回一个类型代码。

分类规则：
- tech：技术教程、编程、操作演示、工具使用（如"Python入门"、"Docker部署教程"）
- dialogue：对话访谈、辩论、圆桌讨论、播客（如"对话马斯克"、"圆桌派"）
- science：科普解读、知识讲解、理论分析（如"量子力学科普"、"经济学原理"）
- review：测评对比、选型推荐、产品评测（如"手机测评"、"框架对比"）

视频标题：{title}

仅返回类型代码（tech/dialogue/science/review），无需任何解释。"""

        # 调用 LLM
        from openai import OpenAI
        import httpx

        # 创建客户端，10秒超时
        timeout = httpx.Timeout(10.0, connect=5.0)

        if provider.base_url:
            client = OpenAI(
                api_key=provider.api_key,
                base_url=provider.base_url,
                http_client=httpx.Client(timeout=timeout)
            )
        else:
            client = OpenAI(
                api_key=provider.api_key,
                http_client=httpx.Client(timeout=timeout)
            )

        # 调用模型
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,  # 低温度，更确定性
            max_tokens=10,    # 只需要返回一个单词
        )

        result = response.choices[0].message.content.strip().lower()
        logger.info(f"Video type detection result for '{title}': {result}")

        # 验证返回值
        valid_types = {'tech', 'dialogue', 'science', 'review'}
        if result in valid_types:
            return result

        # 降级：如果LLM返回了其他内容，尝试从中提取
        for valid_type in valid_types:
            if valid_type in result:
                logger.info(f"Extracted type '{valid_type}' from LLM response: {result}")
                return valid_type

        # 最终降级
        logger.warning(f"Invalid type detection result: {result}, using default 'science'")
        return "science"

    except Exception as e:
        logger.warning(f"Video type detection failed: {e}, using default 'science'")
        return "science"
