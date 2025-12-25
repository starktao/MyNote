"""
多模态AI处理器
基于comprehensive_test2.py验证的代码
支持多图片同时分析的选择器
"""

import os
import re
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from openai import OpenAI

from app.config.settings import settings
from app.services.utils.image_encoder import ImageEncoder

logger = logging.getLogger(__name__)


class MultimodalAIProcessor:
    """多模态AI处理器，基于comprehensive_test2.py成功实现"""

    def __init__(self, api_key: str, base_url: str, model_name: str):
        """
        初始化多模态AI处理器

        Args:
            api_key: API密钥
            base_url: API基础URL
            model_name: 模型名称
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.image_encoder = ImageEncoder()
        self.client = OpenAI(api_key=api_key, base_url=base_url)

        logger.info(f"多模态AI处理器初始化完成: {model_name} ({base_url})")

    async def select_best_image(self, image_paths: List[str], context: str = "") -> Dict[str, Any]:
        """
        使用多模态AI选择最佳图像

        Args:
            image_paths: 图像路径列表
            context: 上下文信息

        Returns:
            选择结果
        """
        start_time = time.time()

        try:
            logger.info(f"开始多模态AI选择最佳图像，图片数量: {len(image_paths)}")
            logger.info(f"使用模型: {self.model_name}")

            if not image_paths:
                error_msg = "没有提供图像路径"
                logger.warning(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'model': self.model_name,
                    'method': 'multimodal_ai'
                }

            # 验证图像文件存在
            valid_images = []
            for img_path in image_paths:
                if os.path.exists(img_path):
                    valid_images.append(img_path)
                else:
                    logger.warning(f"图像文件不存在，跳过: {img_path}")

            if not valid_images:
                error_msg = "所有图像文件都不存在"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'model': self.model_name,
                    'method': 'multimodal_ai'
                }

            logger.info(f"有效图像数量: {len(valid_images)}/{len(image_paths)}")

            # 构建提示词
            prompt = self._build_selection_prompt(len(valid_images), context)

            # 构建多图片消息
            messages = self._build_multimodal_messages(valid_images, prompt)

            # 调用API
            logger.info(f"发送多模态AI请求到 {self.model_name}")
            api_start_time = time.time()

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=1000,
                temperature=0.1,
                timeout=settings.MULTIMODAL_TIMEOUT
            )

            api_time = time.time() - api_start_time
            response_text = response.choices[0].message.content

            logger.info(f"多模态AI响应完成，API耗时: {api_time:.2f}秒")
            logger.info(f"响应长度: {len(response_text)} 字符")

            # 解析选择结果
            selection_result = self._parse_selected_image(response_text, valid_images)

            processing_time = time.time() - start_time

            if selection_result:
                image_number = selection_result['selected_image']
                select_reason = selection_result.get('select_reason', '无理由')
                response_format = selection_result.get('format', 'unknown')

                # 转换为0索引
                image_index = image_number - 1
                if 0 <= image_index < len(valid_images):
                    selected_image = valid_images[image_index]

                    logger.info(f"多模态AI选择成功: 图片{image_number} -> {os.path.basename(selected_image)}")
                    logger.info(f"选择理由: {select_reason}")
                    logger.info(f"响应格式: {response_format}")

                    return {
                        'success': True,
                        'selected_image': selected_image,
                        'selected_image_number': image_number,
                        'select_reason': select_reason,
                        'response_format': response_format,
                        'raw_response': response_text,
                        'processing_time': processing_time,
                        'api_time': api_time,
                        'model': self.model_name,
                        'method': 'multimodal_ai',
                        'image_count': len(valid_images),
                        'response_length': len(response_text)
                    }
                else:
                    logger.error(f"图片编号 {image_number} 超出范围 (1-{len(valid_images)})")
                    return {
                        'success': False,
                        'error': f'图片编号 {image_number} 超出范围',
                        'raw_response': response_text,
                        'processing_time': processing_time,
                        'api_time': api_time,
                        'model': self.model_name,
                        'method': 'multimodal_ai'
                    }
            else:
                logger.warning(f"无法从AI响应中解析选择的图像")
                logger.debug(f"AI响应内容: {response_text[:200]}...")
                return {
                    'success': False,
                    'error': '无法解析AI选择结果',
                    'raw_response': response_text,
                    'processing_time': processing_time,
                    'api_time': api_time,
                    'model': self.model_name,
                    'method': 'multimodal_ai'
                }

        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"多模态AI选择失败: {str(e)}"
            logger.error(error_msg, exc_info=True)

            return {
                'success': False,
                'error': error_msg,
                'processing_time': processing_time,
                'model': self.model_name,
                'method': 'multimodal_ai'
            }

    def _build_selection_prompt(self, image_count: int, context: str = "") -> Dict[str, Any]:
        """
        构建图片选择提示词

        Args:
            image_count: 图片数量
            context: 上下文信息

        Returns:
            提示词字典
        """
        # 获取图像文件名用于提示
        image_names = [f"图片{i+1}" for i in range(image_count)]

        base_prompt = f"""我给你展示{image_count}张截图，请选择信息量最多的一张。

选择标准：
1. 文字信息的丰富程度 - 文本越多通常信息量越大
2. 内容的完整性和清晰度 - 图像清晰可读
3. 图像的复杂度和信息密度 - 包含更多细节和元素
4. 对理解内容的价值 - 能帮助理解主要信息的图像

{image_count}张图片依次为：{', '.join(image_names)}

请仔细分析每一张图像，然后用JSON格式回答，包含两个字段：
1. select_pic: 你选择的图片编号（数字）
2. select_reason: 选择这张图片的简短理由（1-2句话）

例如：{{"select_pic": 3, "select_reason": "第3张图片文字最丰富，内容最完整"}}"""

        if context:
            base_prompt += f"\n\n上下文信息：\n{context}"

        base_prompt += f"""

重要：请严格按照JSON格式回答，不要包含其他文字。"""

        return {
            'text': base_prompt,
            'expected_keywords': ['图片', '选择', '最佳', '信息量'],
            'max_tokens': 100,
            'temperature': 0.1
        }

    def _build_multimodal_messages(self, image_paths: List[str], prompt_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        构建多图片消息格式

        Args:
            image_paths: 图像路径列表
            prompt_dict: 提示词字典

        Returns:
            消息列表
        """
        content = [{"type": "text", "text": prompt_dict['text']}]

        # 添加图像到消息中
        for i, image_path in enumerate(image_paths):
            try:
                base64_image = self.image_encoder.encode_image_to_base64(image_path)
                if base64_image:
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": base64_image}
                    })
                    logger.debug(f"成功编码图像 {i+1}/{len(image_paths)}: {os.path.basename(image_path)}")
                else:
                    logger.warning(f"跳过无法编码的图像: {image_path}")
            except Exception as e:
                logger.error(f"编码图像失败 {image_path}: {e}")

        return [{"role": "user", "content": content}]

    def _parse_selected_image(self, response_text: str, image_paths: List[str]) -> Optional[Dict[str, Any]]:
        """
        从AI响应中解析选择的图片和理由

        Args:
            response_text: AI响应文本
            image_paths: 图像路径列表

        Returns:
            解析结果字典，包含selected_image和select_reason，解析失败返回None
        """
        logger.debug(f"解析AI响应选择结果: {response_text[:200]}...")

        try:
            # 首先尝试解析JSON格式
            json_result = self._parse_json_response(response_text)
            if json_result:
                return json_result

            # 如果JSON解析失败，尝试传统格式解析（向后兼容）
            return self._parse_legacy_response(response_text, image_paths)

        except Exception as e:
            logger.error(f"解析AI响应失败: {e}")
            return None

    def _parse_json_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """解析JSON格式的响应"""
        import json

        try:
            # 清理响应文本，移除可能的markdown代码块标记
            cleaned_text = response_text.strip()

            # 移除```json 和 ``` 标记
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()

            # 尝试解析JSON
            data = json.loads(cleaned_text)

            # 验证JSON格式
            if 'select_pic' in data:
                image_number = int(data['select_pic'])
                select_reason = str(data.get('select_reason', '未提供选择理由'))

                logger.info(f"JSON解析成功: 选择图片{image_number}, 理由: {select_reason[:50]}...")

                return {
                    'selected_image': image_number,  # 返回图片编号
                    'select_reason': select_reason,
                    'format': 'json'
                }
            else:
                logger.warning(f"JSON格式缺少select_pic字段: {data}")
                return None

        except json.JSONDecodeError as e:
            logger.debug(f"JSON解析失败: {e}")
            return None
        except Exception as e:
            logger.debug(f"JSON处理异常: {e}")
            return None

    def _parse_legacy_response(self, response_text: str, image_paths: List[str]) -> Optional[Dict[str, Any]]:
        """解析传统格式的响应（向后兼容）"""
        # 清理响应文本
        cleaned_text = response_text.strip().lower()

        # 优先匹配图片编号格式（图片1, 图片2, etc.）
        number_patterns = [
            r'图片(\d+)',
            r'第?(\d+)张',
            r'picture\s*(\d+)',
            r'image\s*(\d+)',
            r'(\d+)',
        ]

        # 尝试匹配图片编号
        for pattern in number_patterns:
            try:
                match = re.search(pattern, cleaned_text)
                if match:
                    image_number = int(match.group(1))

                    # 检查索引是否有效
                    if 1 <= image_number <= len(image_paths):
                        logger.info(f"传统格式解析成功: 选择图片{image_number}")

                        return {
                            'selected_image': image_number,  # 返回图片编号
                            'select_reason': "基于传统格式解析的选择",
                            'format': 'legacy'
                        }
                    else:
                        logger.warning(f"图片编号 {image_number} 超出范围 (1-{len(image_paths)})")

            except Exception as e:
                logger.debug(f"编号匹配失败 '{pattern}': {e}")
                continue

        logger.warning("传统格式解析也失败")
        return None

    def _match_filename(self, selected_text: str, image_paths: List[str]) -> Optional[str]:
        """
        精确匹配文件名

        Args:
            selected_text: 选择的文本
            image_paths: 图像路径列表

        Returns:
            匹配的图片路径
        """
        # 提取图像文件名列表
        image_filenames = [os.path.basename(path) for path in image_paths]
        image_basenames = [os.path.splitext(name)[0] for name in image_filenames]

        # 清理选择文本
        clean_selected = selected_text.strip().lower()

        logger.debug(f"精确匹配: '{clean_selected}' vs {image_filenames}")

        # 1. 完全匹配
        for i, filename in enumerate(image_filenames):
            if clean_selected == filename.lower():
                logger.info(f"完全匹配成功: {filename}")
                return image_paths[i]

        # 2. 基名匹配（去掉扩展名）
        for i, basename in enumerate(image_basenames):
            if clean_selected == basename.lower():
                logger.info(f" basename匹配成功: {basename}")
                return image_paths[i]

        # 3. 包含匹配
        for i, filename in enumerate(image_filenames):
            if clean_selected in filename.lower() or filename.lower() in clean_selected:
                logger.info(f"包含匹配成功: {filename}")
                return image_paths[i]

        # 4. 基名包含匹配
        for i, basename in enumerate(image_basenames):
            if clean_selected in basename.lower() or basename.lower() in clean_selected:
                logger.info(f"basename包含匹配成功: {basename}")
                return image_paths[i]

        logger.debug(f"精确匹配失败: '{selected_text}'")
        return None

    def _fuzzy_match_filename(self, response_text: str, image_paths: List[str]) -> Optional[str]:
        """
        模糊匹配文件名

        Args:
            response_text: 响应文本
            image_paths: 图像路径列表

        Returns:
            匹配的图片路径
        """
        image_filenames = [os.path.basename(path) for path in image_paths]
        image_basenames = [os.path.splitext(name)[0] for name in image_filenames]

        # 分割响应文本为单词
        response_words = re.findall(r'\w+', response_text.lower())

        logger.debug(f"模糊匹配，响应单词: {response_words}")
        logger.debug(f"候选文件名: {image_filenames}")

        # 为每个图像计算匹配分数
        scores = []
        for i, filename in enumerate(image_filenames):
            score = 0
            filename_lower = filename.lower()

            # 完整文件名匹配
            for word in response_words:
                if word in filename_lower:
                    score += len(word)  # 长词权重更高
                    logger.debug(f"文件名 '{filename}' 匹配单词 '{word}', 分数: {score}")

            # 基名匹配
            basename = image_basenames[i].lower()
            for word in response_words:
                if word in basename:
                    score += len(word) * 0.8  # 基名匹配权重稍低
                    logger.debug(f"basename '{basename}' 匹配单词 '{word}', 分数: {score}")

            scores.append((score, i, filename))

        # 返回分数最高的
        if scores:
            scores.sort(reverse=True)
            best_score, best_index, best_filename = scores[0]

            if best_score > 0:
                logger.info(f"模糊匹配最佳结果: {best_filename} (分数: {best_score})")
                return image_paths[best_index]

        logger.debug("模糊匹配失败")
        return None

    async def batch_select_images(self, image_groups: List[List[str]], contexts: List[str] = None) -> List[Dict[str, Any]]:
        """
        批量选择多组图像

        Args:
            image_groups: 图像组列表
            contexts: 上下文信息列表（可选）

        Returns:
            选择结果列表
        """
        logger.info(f"开始批量多模态AI选择，组数: {len(image_groups)}")

        results = []
        start_time = time.time()

        for i, image_group in enumerate(image_groups):
            context = contexts[i] if contexts and i < len(contexts) else ""
            group_name = f"group_{i+1}"

            logger.info(f"处理第 {i+1}/{len(image_groups)} 组: {len(image_group)} 张图片")

            try:
                result = await self.select_best_image(image_group, context)
                result['group_name'] = group_name
                result['group_index'] = i
                results.append(result)

                if result['success']:
                    logger.info(f"第 {i+1} 组选择成功: {os.path.basename(result['selected_image'])}")
                else:
                    logger.warning(f"第 {i+1} 组选择失败: {result.get('error', '未知错误')}")

            except Exception as e:
                logger.error(f"第 {i+1} 组处理异常: {e}")
                results.append({
                    'group_name': group_name,
                    'group_index': i,
                    'success': False,
                    'error': str(e),
                    'model': self.model_name,
                    'method': 'multimodal_ai'
                })

        total_time = time.time() - start_time
        successful_count = sum(1 for r in results if r.get('success', False))

        logger.info(f"批量选择完成: {successful_count}/{len(image_groups)} 组成功")
        logger.info(f"总耗时: {total_time:.2f}秒")

        return results

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            'model_name': self.model_name,
            'api_base_url': self.base_url,
            'api_configured': bool(self.api_key and self.base_url),
            'capabilities': [
                'multi_image_analysis',
                'image_content_understanding',
                'intelligent_selection',
                'context_aware_selection'
            ]
        }

    def validate_configuration(self) -> Dict[str, Any]:
        """验证配置是否完整"""
        issues = []

        if not self.api_key:
            issues.append("缺少API密钥")

        if not self.base_url:
            issues.append("缺少API基础URL")

        if not self.model_name:
            issues.append("缺少模型名称")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'model': self.model_name
        }

    async def select_best_screenshots_batch(
        self,
        timepoint_groups: Dict[str, List[str]],  # {timepoint_timestamp: [image_paths]}
        timepoint_contexts: Dict[str, str],      # {timepoint_timestamp: context}
        global_context: str = ""
    ) -> Dict[str, Any]:
        """
        批量选择多个时间点的最佳截图 - 单次API调用

        Args:
            timepoint_groups: 时间点分组字典，格式为 {"时间戳": [图片路径列表]}
            timepoint_contexts: 时间点上下文信息字典，格式为 {"时间戳": "上下文描述"}
            global_context: 全局上下文信息

        Returns:
            Dict[str, Any]: 批量选择结果
        """
        start_time = time.time()

        try:
            logger.info(f"开始批量多模态AI选择最佳截图，时间点数量: {len(timepoint_groups)}")
            logger.info(f"使用模型: {self.model_name}")

            if not timepoint_groups:
                error_msg = "没有提供时间点分组"
                logger.warning(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'model': self.model_name,
                    'method': 'multimodal_ai_batch'
                }

            # 准备所有图片路径和验证
            all_image_paths = []
            timepoint_image_ranges = {}  # 记录每个时间点在全局图片列表中的范围

            current_start_index = 0
            for timepoint_timestamp, image_paths in timepoint_groups.items():
                # 验证图片文件存在
                valid_images = []
                for img_path in image_paths:
                    if os.path.exists(img_path):
                        valid_images.append(img_path)
                    else:
                        logger.warning(f"图像文件不存在，跳过: {img_path}")

                if not valid_images:
                    logger.warning(f"时间点 {timepoint_timestamp} 没有有效的图片文件")
                    continue

                timepoint_image_ranges[timepoint_timestamp] = {
                    'start': current_start_index,
                    'end': current_start_index + len(valid_images) - 1,
                    'images': valid_images
                }

                all_image_paths.extend(valid_images)
                current_start_index += len(valid_images)

            if not all_image_paths:
                error_msg = "所有时间点都没有有效的图片文件"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'model': self.model_name,
                    'method': 'multimodal_ai_batch'
                }

            logger.info(f"有效图片总数: {len(all_image_paths)}，时间点数: {len(timepoint_image_ranges)}")

            # 构建批量选择提示词
            prompt = self._build_batch_selection_prompt(timepoint_groups, timepoint_contexts, global_context, timepoint_image_ranges)

            # 构建多图片消息
            messages = self._build_multimodal_messages(all_image_paths, {'text': prompt})

            # 调用API
            logger.info(f"发送批量多模态AI请求到 {self.model_name}")
            api_start_time = time.time()

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=2000,  # 增加token限制以处理批量结果
                temperature=0.1,
                timeout=settings.MULTIMODAL_TIMEOUT
            )

            api_time = time.time() - api_start_time
            response_text = response.choices[0].message.content

            logger.info(f"批量多模态AI响应完成，API耗时: {api_time:.2f}秒")
            logger.info(f"响应长度: {len(response_text)} 字符")

            # 解析批量选择结果
            batch_selection_result = self._parse_batch_selection_result(response_text, timepoint_image_ranges)

            processing_time = time.time() - start_time

            if batch_selection_result['success']:
                logger.info(f"批量多模态AI选择成功，处理了 {len(timepoint_image_ranges)} 个时间点")
                logger.info(f"成功选择: {len(batch_selection_result['selections'])}/{len(timepoint_image_ranges)} 个时间点")

                return {
                    'success': True,
                    'selections': batch_selection_result['selections'],
                    'raw_response': response_text,
                    'processing_time': processing_time,
                    'api_time': api_time,
                    'model': self.model_name,
                    'method': 'multimodal_ai_batch',
                    'timepoint_count': len(timepoint_image_ranges),
                    'total_image_count': len(all_image_paths),
                    'response_length': len(response_text)
                }
            else:
                logger.error(f"批量选择解析失败: {batch_selection_result.get('error', '未知错误')}")
                return {
                    'success': False,
                    'error': batch_selection_result.get('error', '解析批量选择结果失败'),
                    'raw_response': response_text,
                    'processing_time': processing_time,
                    'api_time': api_time,
                    'model': self.model_name,
                    'method': 'multimodal_ai_batch'
                }

        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"批量多模态AI选择失败: {str(e)}"
            logger.error(error_msg, exc_info=True)

            return {
                'success': False,
                'error': error_msg,
                'processing_time': processing_time,
                'model': self.model_name,
                'method': 'multimodal_ai_batch'
            }

    def _build_batch_selection_prompt(
        self,
        timepoint_groups: Dict[str, List[str]],
        timepoint_contexts: Dict[str, str],
        global_context: str,
        timepoint_image_ranges: Dict[str, Dict]
    ) -> str:
        """
        构建批量选择的智能提示词
        """
        # 构建时间点分组信息
        timepoint_info = []
        for i, (timepoint_timestamp, range_info) in enumerate(timepoint_image_ranges.items()):
            image_count = len(range_info['images'])
            global_start = range_info['start'] + 1  # 转换为1基索引
            global_end = range_info['end'] + 1

            context_info = timepoint_contexts.get(timepoint_timestamp, "无特殊上下文")
            timepoint_info.append(f"时间点{i+1}({timepoint_timestamp}): 图片{global_start}-{global_end} ({image_count}张)，上下文: {context_info}")

        base_prompt = f"""我需要你从多个时间点中为每个时间点选择一张最佳截图。

时间点分组信息：
{chr(10).join(timepoint_info)}

选择标准：
1. 文字信息丰富程度 - 文本越多通常信息量越大
2. 内容完整性和清晰度 - 图像清晰可读
3. 图像复杂度和信息密度 - 包含更多细节和元素
4. 对理解该时间点内容的价值 - 能帮助理解该时刻主要信息的图像

请为每个时间点选择一张最佳截图，返回JSON格式，包含selections数组：
{{
  "selections": [
    {{"timepoint": "1:30", "selected_image": 3, "reason": "包含完整的关键公式推导和详细说明"}},
    {{"timepoint": "2:15", "selected_image": 8, "reason": "展示了清晰的界面操作步骤和结果"}},
    ...
  ]
}}

重要说明：
- selected_image是**全局图片索引**（1开始），不是每组的索引
- reason字段请说明选择该图片的具体理由
- 确保每个时间点都有且仅有一张被选中的图片"""

        if global_context:
            base_prompt += f"\n\n全局上下文：{global_context}"

        base_prompt += f"""

重要：请严格按照JSON格式回答，不要包含其他文字。确保每个指定的时间点都有对应的选择结果。"""

        return base_prompt

    def _parse_batch_selection_result(self, response_text: str, timepoint_image_ranges: Dict[str, Dict]) -> Dict[str, Any]:
        """
        从AI响应中解析批量选择结果
        """
        logger.debug(f"解析批量AI选择结果: {response_text[:300]}...")

        try:
            # 首先尝试解析JSON格式
            json_result = self._parse_batch_json_response(response_text, timepoint_image_ranges)
            if json_result:
                return json_result

            # 如果JSON解析失败，尝试传统格式解析
            return self._parse_batch_legacy_response(response_text, timepoint_image_ranges)

        except Exception as e:
            logger.error(f"解析批量AI响应失败: {e}")
            return {
                'success': False,
                'error': f"解析失败: {str(e)}"
            }

    def _parse_batch_json_response(self, response_text: str, timepoint_image_ranges: Dict[str, Dict]) -> Optional[Dict[str, Any]]:
        """解析JSON格式的批量响应"""
        import json

        try:
            # 清理响应文本，移除可能的markdown代码块标记
            cleaned_text = response_text.strip()

            # 移除```json 和 ``` 标记
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()

            # 尝试解析JSON
            data = json.loads(cleaned_text)

            if 'selections' not in data:
                logger.warning(f"JSON格式缺少selections字段: {data}")
                return None

            selections = data['selections']
            if not isinstance(selections, list):
                logger.warning(f"selections字段不是数组格式: {type(selections)}")
                return None

            # 验证和转换选择结果
            validated_selections = []
            for selection in selections:
                if not isinstance(selection, dict):
                    continue

                timepoint = selection.get('timepoint')
                selected_image = selection.get('selected_image')
                reason = selection.get('reason', '批量选择结果')

                if not timepoint or not selected_image:
                    continue

                # 验证时间点是否有效
                if timepoint not in timepoint_image_ranges:
                    logger.warning(f"未知的时间点: {timepoint}")
                    continue

                # 转换并验证图片索引
                try:
                    image_index = int(selected_image)
                    if image_index < 1:
                        logger.warning(f"图片索引无效: {image_index}，时间点: {timepoint}")
                        continue

                    # 验证图片索引是否在有效范围内
                    range_info = timepoint_image_ranges[timepoint]
                    global_start = range_info['start'] + 1  # 转换为1基索引
                    global_end = range_info['end'] + 1

                    if not (global_start <= image_index <= global_end):
                        logger.warning(f"图片索引 {image_index} 超出时间点 {timepoint} 的范围 [{global_start}, {global_end}]")
                        continue

                    # 转换为组内索引
                    group_index = image_index - global_start
                    selected_image_path = range_info['images'][group_index]

                    validated_selections.append({
                        'timepoint': timepoint,
                        'selected_image': selected_image_path,
                        'selected_image_index': group_index,  # 0基的组内索引
                        'global_image_index': image_index,   # 1基的全局索引
                        'reason': reason,
                        'format': 'json'
                    })

                except (ValueError, IndexError) as e:
                    logger.warning(f"图片索引转换失败: {selected_image}, 时间点: {timepoint}, 错误: {e}")
                    continue

            # 检查是否覆盖了所有时间点
            covered_timepoints = {s['timepoint'] for s in validated_selections}
            missing_timepoints = set(timepoint_image_ranges.keys()) - covered_timepoints

            if missing_timepoints:
                logger.warning(f"部分时间点未选择图片: {missing_timepoints}")
                # 为缺失的时间点创建默认选择（选择第一张图片）
                for missing_timepoint in missing_timepoints:
                    range_info = timepoint_image_ranges[missing_timepoint]
                    if range_info['images']:
                        validated_selections.append({
                            'timepoint': missing_timepoint,
                            'selected_image': range_info['images'][0],
                            'selected_image_index': 0,
                            'global_image_index': range_info['start'] + 1,
                            'reason': '解析失败，默认选择第一张图片',
                            'format': 'json_fallback'
                        })

            logger.info(f"JSON解析成功: {len(validated_selections)} 个时间点选择结果")
            return {
                'success': True,
                'selections': validated_selections,
                'format': 'json'
            }

        except json.JSONDecodeError as e:
            logger.debug(f"JSON解析失败: {e}")
            return None
        except Exception as e:
            logger.debug(f"JSON处理异常: {e}")
            return None

    def _parse_batch_legacy_response(self, response_text: str, timepoint_image_ranges: Dict[str, Dict]) -> Optional[Dict[str, Any]]:
        """解析传统格式的批量响应（向后兼容）"""
        logger.warning("使用传统格式解析批量响应，建议使用JSON格式")

        # 简化的传统解析，主要处理一些常见的响应格式
        # 这里可以根据实际需要进行扩展
        try:
            # 尝试提取时间点和图片对应关系
            selections = []
            timepoint_list = list(timepoint_image_ranges.keys())

            # 如果没有明确的选择，为每个时间点选择第一张图片
            for i, timepoint in enumerate(timepoint_list):
                range_info = timepoint_image_ranges[timepoint]
                if range_info['images']:
                    selections.append({
                        'timepoint': timepoint,
                        'selected_image': range_info['images'][0],
                        'selected_image_index': 0,
                        'global_image_index': range_info['start'] + 1,
                        'reason': '传统格式解析，默认选择第一张图片',
                        'format': 'legacy'
                    })

            return {
                'success': True,
                'selections': selections,
                'format': 'legacy'
            }

        except Exception as e:
            logger.error(f"传统格式解析也失败: {e}")
            return None


def create_multimodal_processor(provider_config: Dict[str, Any]) -> MultimodalAIProcessor:
    """
    创建多模态AI处理器实例

    Args:
        provider_config: Provider配置

    Returns:
        MultimodalAIProcessor实例
    """
    api_key = provider_config.get('api_key')
    base_url = provider_config.get('base_url')
    model_name = provider_config.get('model_name', 'gpt-4o')

    if not all([api_key, base_url]):
        raise ValueError("Provider配置缺少必要信息: api_key, base_url")

    processor = MultimodalAIProcessor(api_key, base_url, model_name)
    logger.info(f"多模态AI处理器实例创建完成: {model_name}")
    return processor