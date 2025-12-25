"""
AI图像识别检测服务
"""

import os
import uuid
import time
import base64
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.database.image_test import ImageTestSession, ImageTestResult
from app.infrastructure.llm.provider import _load_provider
from app.infrastructure.llm.provider import _build_openai_client
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ImageTestService:
    """AI图像识别检测服务"""

    def __init__(self):
        self.test_image_dir = os.path.join(settings.BASE_DIR, "static", "test_images")

        # 确保测试图像目录存在
        os.makedirs(self.test_image_dir, exist_ok=True)

    def create_test_session(self, provider_id: str, model_name: str, db: Session) -> str:
        """创建图像识别测试会话"""
        session_id = str(uuid.uuid4())

        # 创建会话记录
        session = ImageTestSession(
            id=session_id,
            provider_id=provider_id,
            model_name=model_name,
            status="created"
        )

        db.add(session)
        db.commit()

        logger.info(f"[ImageTestService] 创建测试会话: {session_id}, Provider: {provider_id}, Model: {model_name}")
        return session_id

    async def run_vision_test(self, session_id: str, db: Session) -> Dict[str, Any]:
        """运行完整的图像识别测试"""
        try:
            session = db.query(ImageTestSession).filter(ImageTestSession.id == session_id).first()
            if not session:
                raise ValueError(f"测试会话不存在: {session_id}")

            # 更新状态为运行中
            session.status = "running"
            session.start_time = datetime.now()
            db.commit()

            # 准备测试案例
            test_cases = self._prepare_test_cases()
            if not test_cases:
                raise ValueError("没有可用的测试图像")

            session.total_tests = len(test_cases)
            db.commit()

            # 加载AI Provider
            provider = _load_provider(session.provider_id)
            if not provider:
                raise ValueError(f"Provider不存在: {session.provider_id}")

            # 创建OpenAI客户端
            client = _build_openai_client(
                api_key=provider["api_key"],
                base_url=provider.get("base_url")
            )
            if not client:
                raise ValueError(f"无法创建AI客户端: {session.provider_id}")

            results = []
            passed_count = 0

            # 逐一测试每个图像
            for i, test_case in enumerate(test_cases):
                try:
                    logger.info(f"[ImageTestService] 测试案例 {i+1}/{len(test_cases)}: {test_case['name']}")

                    start_time = time.time()
                    result = await self._test_single_image(client, session.model_name, test_case, session_id, db)
                    response_time = int((time.time() - start_time) * 1000)

                    if result["is_correct"]:
                        passed_count += 1

                    results.append({
                        "image_name": test_case["name"],
                        "correct_answer": test_case["correct_answer"],
                        "ai_response": result["ai_response"],
                        "is_correct": result["is_correct"],
                        "response_time_ms": response_time
                    })

                except Exception as e:
                    logger.error(f"[ImageTestService] 测试案例 {test_case['name']} 失败: {e}")

                    # 保存错误结果
                    test_result = ImageTestResult(
                        id=str(uuid.uuid4()),
                        session_id=session_id,
                        image_name=test_case["name"],
                        image_uuid=test_case["uuid"],
                        correct_answer=test_case["correct_answer"],
                        error_message=str(e)
                    )
                    db.add(test_result)

            # 计算通过率
            pass_rate = int((passed_count / len(test_cases)) * 100) if test_cases else 0

            # 更新会话状态
            session.status = "completed"
            session.end_time = datetime.now()
            session.passed_tests = passed_count
            session.failed_tests = len(test_cases) - passed_count
            session.pass_rate = pass_rate
            db.commit()

            logger.info(f"[ImageTestService] 测试完成: 通过率 {pass_rate}% ({passed_count}/{len(test_cases)})")

            return {
                "session_id": session_id,
                "provider_id": session.provider_id,
                "model_name": session.model_name,
                "total_tests": len(test_cases),
                "passed_tests": passed_count,
                "failed_tests": len(test_cases) - passed_count,
                "pass_rate": pass_rate,
                "results": results
            }

        except Exception as e:
            logger.error(f"[ImageTestService] 测试会话失败: {e}")
            # 更新失败状态
            if 'session' in locals():
                session.status = "failed"
                session.end_time = datetime.now()
                db.commit()
            raise

    def _prepare_test_cases(self) -> List[Dict[str, Any]]:
        """准备测试案例"""
        test_cases = [
            {
                "name": "dog",
                "image_path": os.path.join(self.test_image_dir, "dog.jpg"),
                "uuid": str(uuid.uuid4()) + ".jpg",
                "question": "这张图片显示的是什么动物？",
                "options": ["A. 狗", "B. 猫", "C. 汽车", "D. 建筑"],
                "correct_answer": "A"
            },
            {
                "name": "cat",
                "image_path": os.path.join(self.test_image_dir, "cat.jpg"),
                "uuid": str(uuid.uuid4()) + ".jpg",
                "question": "这张图片显示的是什么动物？",
                "options": ["A. 狗", "B. 猫", "C. 汽车", "D. 建筑"],
                "correct_answer": "B"
            },
            {
                "name": "car",
                "image_path": os.path.join(self.test_image_dir, "car.jpg"),
                "uuid": str(uuid.uuid4()) + ".jpg",
                "question": "这张图片显示的是什么物体？",
                "options": ["A. 狗", "B. 猫", "C. 汽车", "D. 建筑"],
                "correct_answer": "C"
            },
            {
                "name": "building",
                "image_path": os.path.join(self.test_image_dir, "building.jpg"),
                "uuid": str(uuid.uuid4()) + ".jpg",
                "question": "这张图片显示的是什么物体？",
                "options": ["A. 狗", "B. 猫", "C. 汽车", "D. 建筑"],
                "correct_answer": "D"
            }
        ]

        # 验证图像文件存在
        valid_cases = []
        for case in test_cases:
            if os.path.exists(case["image_path"]):
                valid_cases.append(case)
            else:
                logger.warning(f"[ImageTestService] 测试图像不存在: {case['image_path']}")

        return valid_cases

    async def _test_single_image(self, client, model_name: str, test_case: Dict[str, Any], session_id: str, db: Session) -> Dict[str, Any]:
        """测试单个图像识别"""
        try:
            # 检查Provider是否支持图像识别
            if not self._supports_vision(model_name):
                logger.warning(f"[ImageTestService] 模型 {model_name} 不支持图像识别，跳过测试")
                # 保存跳过的结果
                test_result = ImageTestResult(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    image_name=test_case["name"],
                    image_uuid=test_case["uuid"],
                    correct_answer=test_case["correct_answer"],
                    ai_response="模型不支持图像识别",
                    is_correct=False
                )
                db.add(test_result)
                return {
                    "ai_response": "模型不支持图像识别",
                    "is_correct": False
                }

            # 读取图像并转换为Base64
            with open(test_case["image_path"], "rb") as image_file:
                image_data = image_file.read()
                image_base64 = base64.b64encode(image_data).decode('utf-8')

            # 根据Provider类型选择不同的调用方式
            if "deepseek" in model_name.lower():
                # DeepSeek 使用特殊格式 - 尝试不同的方法
                messages = self._build_deepseek_vision_prompt(
                    image_base64,
                    test_case["question"],
                    test_case["options"]
                )
            elif "qwen" in model_name.lower():
                # Qwen 使用特殊格式
                messages = self._build_qwen_vision_prompt(
                    image_base64,
                    test_case["question"],
                    test_case["options"]
                )
            else:
                # OpenAI 兼容格式
                messages = self._build_vision_test_prompt(
                    image_base64,
                    test_case["question"],
                    test_case["options"]
                )

            # 调用AI服务
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.1,  # 低温度确保确定性
                max_tokens=100
            )

            ai_response = response.choices[0].message.content.strip()

            # 验证答案
            is_correct = self._verify_answer(ai_response, test_case["correct_answer"])

            logger.info(f"[ImageTestService] 图像测试结果: {test_case['name']}, AI: {ai_response}, 正确: {test_case['correct_answer']}, 准确: {is_correct}")

            # 保存测试结果
            test_result = ImageTestResult(
                id=str(uuid.uuid4()),
                session_id=session_id,
                image_name=test_case["name"],
                image_uuid=test_case["uuid"],
                correct_answer=test_case["correct_answer"],
                ai_response=ai_response,
                is_correct=is_correct
            )

            db.add(test_result)

            return {
                "ai_response": ai_response,
                "is_correct": is_correct
            }

        except Exception as e:
            logger.error(f"[ImageTestService] 单个图像测试失败: {e}")
            # 保存错误结果
            test_result = ImageTestResult(
                id=str(uuid.uuid4()),
                session_id=session_id,
                image_name=test_case["name"],
                image_uuid=test_case["uuid"],
                correct_answer=test_case["correct_answer"],
                ai_response=f"测试失败: {str(e)}",
                is_correct=False
            )
            db.add(test_result)
            return {
                "ai_response": f"测试失败: {str(e)}",
                "is_correct": False
            }

    def _build_vision_test_prompt(self, image_base64: str, question: str, options: List[str]) -> List[Dict[str, Any]]:
        """构建视觉测试提示词"""
        prompt_text = f"""
请仔细观察这张图片，并回答以下问题：

问题：{question}

选项：
{chr(10).join(options)}

要求：
1. 请只回答正确的选项字母（A、B、C或D）
2. 不要添加任何解释或额外文字
3. 确保答案是一个单独的字母

你的答案：
"""

        return [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt_text
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ]

    def _verify_answer(self, ai_response: str, correct_answer: str) -> bool:
        """验证AI答案准确性"""
        # 清理AI响应
        cleaned_response = ai_response.strip().upper()

        # 直接匹配
        if cleaned_response == correct_answer.upper():
            return True

        # 提取字母匹配
        letters = re.findall(r'[A-D]', cleaned_response)
        if letters and letters[0] == correct_answer.upper():
            return True

        return False

    def _build_vision_prompt_alternative(self, image_base64: str, question: str, options: List[str]) -> List[Dict[str, Any]]:
        """构建DeepSeek/Qwen兼容的视觉测试提示词"""
        prompt_text = f"""请仔细观察这张图片，并回答以下问题：

问题：{question}

选项：
{chr(10).join(options)}

要求：
1. 请只回答正确的选项字母（A、B、C或D）
2. 不要添加任何解释或额外文字
3. 确保答案是一个单独的字母

你的答案："""

        # DeepSeek/Qwen 可能使用不同的格式
        # 首先尝试简单的文本格式，如果不支持多模态，会返回错误
        return [
            {
                "role": "user",
                "content": prompt_text
            }
        ]

    def get_test_session(self, session_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """获取测试会话信息"""
        session = db.query(ImageTestSession).filter(ImageTestSession.id == session_id).first()
        if not session:
            return None

        # 获取测试结果
        results = db.query(ImageTestResult).filter(ImageTestResult.session_id == session_id).all()

        return {
            "session_id": session.id,
            "provider_id": session.provider_id,
            "model_name": session.model_name,
            "status": session.status,
            "total_tests": session.total_tests,
            "passed_tests": session.passed_tests,
            "failed_tests": session.failed_tests,
            "pass_rate": session.pass_rate,
            "start_time": session.start_time.isoformat() if session.start_time else None,
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "results": [result.to_dict() for result in results]
        }

    def _supports_vision(self, model_name: str) -> bool:
        """检查模型是否支持图像识别"""
        model_name_lower = model_name.lower()

        # 支持图像识别的模型列表
        vision_models = [
            "gpt-4-vision-preview",
            "gpt-4o",
            "gpt-4o-mini",
            "claude-3",
            "gemini-pro-vision",
            "qwen-vl",
            "qwen-vl-max"
        ]

        # 检查是否在支持列表中
        return any(vision_model in model_name_lower for vision_model in vision_models)

    def _build_deepseek_vision_prompt(self, image_base64: str, question: str, options: List[str]) -> List[Dict[str, Any]]:
        """构建DeepSeek兼容的视觉测试提示词"""
        prompt_text = f"""请仔细观察这张图片，并回答以下问题：

问题：{question}

选项：
{chr(10).join(options)}

要求：
1. 请只回答正确的选项字母（A、B、C或D）
2. 不要添加任何解释或额外文字
3. 确保答案是一个单独的字母

你的答案："""

        # DeepSeek可能不支持多模态，返回简单的文本提示
        return [
            {
                "role": "user",
                "content": prompt_text
            }
        ]

    def _build_qwen_vision_prompt(self, image_base64: str, question: str, options: List[str]) -> List[Dict[str, Any]]:
        """构建Qwen兼容的视觉测试提示词"""
        prompt_text = f"""请仔细观察这张图片，并回答以下问题：

问题：{question}

选项：
{chr(10).join(options)}

要求：
1. 请只回答正确的选项字母（A、B、C或D）
2. 不要添加任何解释或额外文字
3. 确保答案是一个单独的字母

你的答案："""

        # Qwen VL系列支持多模态，使用标准格式
        return [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt_text
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ]