"""
Task Service - Business Logic for Task Management
集成完整的截图功能，支持智能截图生成和AI选择
"""

import json
import os
import uuid
import asyncio
import logging
from typing import Optional, Dict, Any
from app.repositories.task_repository import TaskRepository
from app.infrastructure.llm.provider import generate_markdown_via_llm

# Import required services
from app.services.download_service import DownloadService
from app.services.screenshot_service import ScreenshotService
from app.models.dto.screenshot_dto import ScreenshotProcessResult

# P1.4新增：导入SSE事件管理器
from app.infrastructure.tasks.events import emit_transcribe_progress
from app.infrastructure.transcribe.transcriber_manager import transcriber_manager

logger = logging.getLogger(__name__)

class TaskService:
    """Task management service with integrated screenshot functionality"""

    def __init__(self):
        """Initialize task service - 移除长连接持有，使用按需连接模式"""
        self.service_name = "TaskService"
        # 移除 self.task_repo = TaskRepository() - 避免长连接持有
        self.download_service = DownloadService()
        self.screenshot_service = ScreenshotService()
        logger.info(f"[{self.service_name}] 任务服务初始化完成，使用按需连接模式")

    def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new task"""
        try:
            # Generate task ID if not provided
            task_id = task_data.get("task_id") or uuid.uuid4().hex

            logger.info(f"[{self.service_name}] 创建任务: {task_id}")
            logger.info(f"[{self.service_name}] 任务数据: {task_data}")

            # Handle empty provider_id by using default from configured models
            provider_id = task_data.get("provider_id")
            model_name = task_data.get("model_name")
            screenshot_enabled = task_data.get("screenshot", False)

            if not provider_id and model_name:
                # Try to find a configured model with this model_name
                from app.repositories.model_repository import ModelRepository
                model_repo = ModelRepository()
                configured_models = model_repo.find_by_condition({"name": model_name, "enabled": True})
                if configured_models:
                    configured_model = configured_models[0]
                    provider_id = configured_model.provider_id
                    logger.info(f"[{self.service_name}] 找到配置的模型，使用provider_id: {provider_id}")
                else:
                    logger.warning(f"[{self.service_name}] 未找到 {model_name} 的配置模型，provider_id保持为空")

            if not provider_id:
                logger.warning(f"[{self.service_name}] provider_id为空，AI生成可能会失败")

            # Create VideoTask object
            from app.models.database.video_task import VideoTask
            task_obj = VideoTask(
                id=task_id,
                batch_id=task_data.get("batch_id"),
                video_id=task_data.get("video_id", ""),
                platform=task_data.get("platform", "generic"),
                source_url=task_data.get("video_url"),
                status="PENDING",
                quality=task_data.get("quality", "fast"),
                model_name=model_name,
                provider_id=provider_id or "",  # Ensure it's not None
                style=task_data.get("style"),
                video_type=task_data.get("video_type", "auto"),
                note_style=task_data.get("note_style", "detailed"),
                options=json.dumps({
                    "format": task_data.get("format", []),
                    "extras": task_data.get("extras"),
                    "screenshot": screenshot_enabled,
                    "screenshot_mode": task_data.get("screenshot_mode", "smart"),
                    "screenshot_window": task_data.get("screenshot_window", 2.0),
                    "screenshot_candidates": task_data.get("screenshot_candidates", 5),
                    "export_raw_transcript": task_data.get("export_raw_transcript", False),
                    "link": task_data.get("link", False),  # 保存原视频链接开关
                    "screenshot_density": task_data.get("screenshot_density", "medium")  # 保存截图密度
                }, ensure_ascii=False)
            )

            logger.info(f"[{self.service_name}] 创建任务对象: {task_obj}")

            # Create task in database - 使用按需连接模式
            with TaskRepository() as task_repo:
                task = task_repo.create(task_obj)
            logger.info(f"[{self.service_name}] 任务已创建到数据库: {task}")

            return {
                "task_id": task_id,
                "status": "PENDING",
                "message": "任务创建成功",
                "video_type": task_data.get("video_type", "auto"),
                "note_style": task_data.get("note_style", "detailed"),
                "screenshot_enabled": screenshot_enabled
            }
        except Exception as e:
            logger.error(f"[{self.service_name}] 创建任务失败: {str(e)}")
            import traceback
            logger.error(f"[{self.service_name}] 完整错误堆栈: {traceback.format_exc()}")
            raise Exception(f"创建任务失败: {str(e)}")

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status from database"""
        try:
            with TaskRepository() as task_repo:
                task = task_repo.find_by_id(task_id)
            if not task:
                return None

            return {
                "task_id": task.id,
                "status": task.status,
                "message": task.message or "",
                "video_id": task.video_id,
                "platform": task.platform,
                "quality": task.quality,
                "model_name": task.model_name,
                "provider_id": task.provider_id,
                "style": task.style,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
                "audio_path": task.audio_path,
                "result_path": task.result_path,
                "transcript_path": task.transcript_path
            }
        except Exception as e:
            raise Exception(f"Failed to get task status: {str(e)}")

    def update_task_status(self, task_id: str, status: str, message: str = "", **kwargs) -> bool:
        """Update task status"""
        try:
            with TaskRepository() as task_repo:
                task = task_repo.update_status(task_id, status, message, **kwargs)

            # Send SSE event if registry is available
            try:
                from app.controllers.note_controller import task_registry
                if task_registry:
                    task_registry.publish(task_id, {
                        "task_id": task_id,
                        "status": status,
                        "message": message,
                        "timestamp": __import__("time").time()
                    })
                    print(f"[SSE] Published status update: {task_id} -> {status}")
            except Exception as sse_error:
                print(f"[WARNING] Failed to publish SSE event: {sse_error}")

            return task is not None
        except Exception as e:
            raise Exception(f"Failed to update task status: {str(e)}")

    async def execute_task(self, task_id: str, task_data: Dict[str, Any]) -> bool:
        """Execute the complete task workflow"""
        screenshot_result = None  # 初始化变量在try块外部

        try:
            print(f"[TASK] Starting task execution: {task_id}")
            print(f"[INFO] Task data: {task_data}")

            # Step 1: Download video/audio (with video if screenshots needed)
            screenshot_enabled = task_data.get("screenshot", False)
            download_message = "Downloading audio" + (" and video for screenshots" if screenshot_enabled else "")
            self.update_task_status(task_id, "DOWNLOADING", f"{download_message}...")

            print(f"[DOWNLOAD] Starting download - Screenshot enabled: {screenshot_enabled}")
            print(f"[DOWNLOAD] Video URL: {task_data['video_url']}")

            try:
                logger.info(f"[{self.service_name}] 开始下载，截图功能: {screenshot_enabled}")
                print(f"[DOWNLOAD] Calling download service with need_video={screenshot_enabled}")

                # 使用 asyncio.to_thread 将同步下载操作放到线程池
                download_result = await asyncio.to_thread(
                    self.download_service.download,
                    video_url=task_data["video_url"],
                    quality=task_data.get("quality", "fast"),
                    need_video=screenshot_enabled
                )

                audio_path = download_result["audio_path"]
                video_path = download_result.get("video_path", "")
                video_info = download_result["video_info"]

                print(f"[DOWNLOAD] Download completed successfully")
                print(f"[DOWNLOAD] Audio path: {audio_path}")
                print(f"[DOWNLOAD] Video path: {video_path}")
                print(f"[DOWNLOAD] Download type: {video_info.get('download_type', 'unknown')}")

                logger.info(f"[{self.service_name}] 下载完成: {video_info['title']}")
                logger.info(f"[{self.service_name}] 音频文件: {audio_path}")
                if video_path:
                    logger.info(f"[{self.service_name}] 视频文件: {video_path}")

            except Exception as e:
                logger.error(f"[{self.service_name}] 下载失败: {str(e)}")
                self.update_task_status(task_id, "FAILED", f"下载失败: {str(e)}")
                raise Exception(f"下载失败: {str(e)}")

            # Update database with download result
            self.update_task_status(
                task_id,
                "DOWNLOADED",
                "Audio downloaded successfully",
                audio_path=audio_path,
                video_id=video_info.get("video_id", "")
            )

            # 如果视频类型是 auto，在下载后进行类型检测
            if task_data.get("video_type") == "auto":
                try:
                    logger.info(f"[{self.service_name}] 检测到 video_type='auto'，开始自动识别视频类型")
                    from app.services.video_type_detector import detect_video_type

                    # 使用视频标题进行检测
                    title = video_info.get("title", task_data.get("video_url", ""))
                    detected_type = await asyncio.to_thread(
                        detect_video_type,
                        title=title,
                        provider_id=task_data.get("provider_id", ""),
                        model_name=task_data.get("model_name", "")
                    )

                    # 更新任务数据和数据库
                    task_data["video_type"] = detected_type
                    with TaskRepository() as task_repo:
                        task_repo.update(task_id, {"video_type": detected_type})

                    logger.info(f"[{self.service_name}] 视频类型识别完成: {detected_type}")

                    # 通过 SSE 通知前端
                    try:
                        from app.controllers.note_controller import task_registry
                        from app.infrastructure.llm.note_prompts import VIDEO_TYPE_LABELS
                        if task_registry:
                            type_label = VIDEO_TYPE_LABELS.get(detected_type, detected_type)
                            task_registry.publish(task_id, {
                                "task_id": task_id,
                                "status": "DOWNLOADED",
                                "video_type": detected_type,
                                "message": f"已识别为{type_label}类型",
                                "timestamp": __import__("time").time()
                            })
                    except Exception as sse_error:
                        logger.warning(f"[{self.service_name}] SSE 事件发送失败: {sse_error}")

                except Exception as e:
                    logger.warning(f"[{self.service_name}] 视频类型自动识别失败: {e}，使用默认类型 'science'")
                    task_data["video_type"] = "science"
                    with TaskRepository() as task_repo:
                        task_repo.update(task_id, {"video_type": "science"})

            # Update task_data with the correct provider_id (important for AI generation)
            provider_id = task_data.get("provider_id")
            if not provider_id:
                # Re-check for configured model
                from app.repositories.model_repository import ModelRepository
                model_repo = ModelRepository()
                configured_models = model_repo.find_by_condition({"name": task_data["model_name"], "enabled": True})
                if configured_models:
                    provider_id = configured_models[0].provider_id
                    task_data["provider_id"] = provider_id
                    print(f"[DEBUG] Updated task_data provider_id: {provider_id}")

            # Step 2: Transcribe audio - P1.4新增：集成SSE进度反馈
            self.update_task_status(task_id, "TRANSCRIBING", "Transcribing audio...")
            try:
                # P1.4新增：发送转写开始事件
                await emit_transcribe_progress(task_id, {
                    "status": "started",
                    "progress": 0,
                    "message": "开始转写音频",
                    "timestamp": asyncio.get_event_loop().time()
                })

                # 使用转写器管理器获取优化后的转写器
                transcriber = transcriber_manager.get_transcriber(
                    transcriber_type="whisper",
                    model_size="base",  # 可以从task_data获取
                    device="auto"
                )

                # P1.4新增：设置SSE进度回调
                transcriber.set_progress_callback(emit_transcribe_progress)

                # 使用带进度反馈的转写方法
                transcript_result = await transcriber.transcribe_with_progress(audio_path, task_id)

                # 转换结果格式以保持兼容性
                transcription_result = {
                    "full_text": transcript_result.full_text,
                    "segments": [
                        {
                            "start": seg.start,
                            "end": seg.end,
                            "text": seg.text
                        }
                        for seg in transcript_result.segments
                    ],
                    "language": transcript_result.language
                }

                print(f"[TRANSCRIBE] Transcription completed: {len(transcription_result['full_text'])} characters")

                # P1.4新增：发送转写完成事件
                await emit_transcribe_progress(task_id, {
                    "status": "completed",
                    "progress": 100,
                    "message": f"转写完成，共{len(transcription_result['full_text'])}字符",
                    "result": {
                        "text_length": len(transcription_result['full_text']),
                        "language": transcription_result['language'],
                        "segments": len(transcription_result['segments'])
                    },
                    "timestamp": asyncio.get_event_loop().time()
                })

            except Exception as e:
                print(f"[ERROR] Transcription failed: {str(e)}")

                # P1.4新增：发送转写失败事件
                await emit_transcribe_progress(task_id, {
                    "status": "error",
                    "progress": 0,
                    "message": f"转写失败: {str(e)}",
                    "timestamp": asyncio.get_event_loop().time()
                })

                self.update_task_status(task_id, "FAILED", f"Transcription failed: {str(e)}")
                return False

            # Step 3: Generate AI summary with screenshot markers
            # 新流程：让 GPT 在生成笔记时同时输出截图时间点标记
            self.update_task_status(task_id, "GENERATING", "Generating AI summary with screenshot markers...")
            try:
                # 构建 format 列表，如果截图功能启用，确保包含 "screenshot"
                formats = list(task_data.get("format", []))  # 复制列表避免修改原始数据
                if screenshot_enabled and "screenshot" not in formats:
                    formats.append("screenshot")
                    logger.info(f"[{self.service_name}] 截图功能已启用，自动添加 'screenshot' 到 format 列表")

                # 从 options 中读取截图密度
                screenshot_density = "medium"  # 默认值
                try:
                    with TaskRepository() as task_repo:
                        task = task_repo.find_by_id(task_id)
                    if task and task.options:
                        options = json.loads(task.options)
                        screenshot_density = options.get("screenshot_density", "medium")
                        logger.info(f"[{self.service_name}] 截图密度: {screenshot_density}")
                except Exception as e:
                    logger.warning(f"[{self.service_name}] 读取截图密度失败，使用默认值: {e}")

                print(f"[AI] Starting AI summary generation (with screenshot markers)")
                print(f"[AI] Provider ID: {task_data['provider_id']}")
                print(f"[AI] Model: {task_data['model_name']}")
                print(f"[AI] Video Type: {task_data.get('video_type', 'science')}")
                print(f"[AI] Note Style: {task_data.get('note_style', 'detailed')}")
                print(f"[AI] Format: {formats}")
                print(f"[AI] Screenshot enabled: {screenshot_enabled}")
                print(f"[AI] Screenshot density: {screenshot_density}")
                print(f"[AI] Input text length: {len(transcription_result['full_text'])} characters")

                logger.info(f"[{self.service_name}] 开始生成笔记（含截图时间点标记）")

                # 传入真实的 Whisper segments 和新的类型/风格参数
                markdown_result = await asyncio.to_thread(
                    generate_markdown_via_llm,
                    task_data["provider_id"],
                    task_data["model_name"],
                    transcription_result["full_text"],
                    task_data.get("video_type", "science"),  # 视频类型
                    task_data.get("note_style", "detailed"),  # 笔记风格
                    formats,  # 使用更新后的 formats 列表
                    task_data.get("extras"),
                    transcription_result["segments"],  # 传入真实的 Whisper segments
                    screenshot_density  # 传递截图密度
                )

                print(f"[AI] AI generation completed")
                print(f"[AI] Generated markdown length: {len(markdown_result)} characters")
                logger.info(f"[{self.service_name}] 笔记生成完成，长度: {len(markdown_result)} 字符")

                # 附加原视频链接（如果启用）
                try:
                    # 从 options 中读取 link 参数
                    with TaskRepository() as task_repo:
                        task = task_repo.find_by_id(task_id)
                    if task and task.options:
                        options = json.loads(task.options)
                        link_enabled = options.get("link", False)

                        if link_enabled:
                            # 构造原视频链接前缀（使用HTML格式，支持新标签页打开）
                            video_title = video_info.get("title", "点击查看")
                            video_url = task_data.get("video_url", "")

                            link_prefix = f'<a href="{video_url}" target="_blank" rel="noopener noreferrer"><strong>📺 原视频：{video_title}</strong></a>\n\n---\n\n'
                            markdown_result = link_prefix + markdown_result

                            print(f"[LINK] Added video link prefix to markdown")
                            logger.info(f"[{self.service_name}] 已添加原视频链接到笔记开头")
                except Exception as link_error:
                    # 链接插入失败不影响主流程
                    logger.warning(f"[{self.service_name}] 插入原视频链接失败: {link_error}")
                    print(f"[WARNING] Failed to add video link: {link_error}")

            except Exception as e:
                print(f"[ERROR] AI generation failed: {e}")
                logger.error(f"[{self.service_name}] 笔记生成失败: {e}")
                self.update_task_status(task_id, "FAILED", f"AI generation failed: {str(e)}")
                return False

            # Step 4: Process screenshots based on markdown markers (if enabled)
            # 新流程：从 Markdown 中提取截图标记，调用现有截图处理管线
            screenshot_result = None
            print(f"[SCREENSHOT_CHECK] Starting screenshot evaluation")
            print(f"[SCREENSHOT_CHECK] screenshot_enabled: {screenshot_enabled}")
            print(f"[SCREENSHOT_CHECK] video_path exists: {bool(video_path)}")

            try:
                if screenshot_enabled and video_path:
                    print(f"[SCREENSHOT] Both conditions met, starting screenshot processing from markdown markers")
                    self.update_task_status(task_id, "SCREENSHOT", "Processing screenshots from markdown markers...")
                    logger.info(f"[{self.service_name}] 开始基于 Markdown 标记处理截图，视频文件: {video_path}")

                    # 调用新的截图处理接口
                    markdown_result, screenshot_result = await self.screenshot_service.process_screenshots_from_markdown(
                        markdown=markdown_result,
                        video_path=video_path,
                        transcript_segments=transcription_result["segments"],
                        task_id=task_id,
                        screenshot_window=float(task_data.get("screenshot_window", 2.0)),
                        screenshot_candidates=int(task_data.get("screenshot_candidates", 5)),
                        provider_id=task_data.get("provider_id", ""),
                        model_name=task_data.get("model_name", "")
                    )

                    print(f"[SCREENSHOT] Screenshot processing completed")
                    print(f"[SCREENSHOT] Successful screenshots: {screenshot_result.successful_screenshots}")

                    # 使用 asyncio.to_thread 保存截图处理结果
                    await asyncio.to_thread(
                        self.screenshot_service.save_process_result,
                        screenshot_result
                    )

                    logger.info(f"[{self.service_name}] 截图处理完成: {screenshot_result.successful_screenshots} 张截图")
                    logger.info(f"[{self.service_name}] 视频类型: {screenshot_result.video_type}")

                else:
                    print(f"[SCREENSHOT] Skipping screenshot processing")
                    print(f"[SCREENSHOT] Reason: screenshot_enabled={screenshot_enabled}, video_path exists={bool(video_path)}")
                    logger.info(f"[{self.service_name}] 跳过截图处理: 截图功能={screenshot_enabled}, 视频文件存在={bool(video_path)}")
                    screenshot_result = ScreenshotProcessResult(
                        task_id=task_id,
                        video_type="未识别",
                        total_timepoints=0,
                        successful_screenshots=0,
                        selected_screenshots=[],
                        processing_time=0.0
                    )

            except Exception as e:
                logger.error(f"[{self.service_name}] 截图处理失败: {str(e)}")
                # 截图失败不终止流程，使用空结果继续
                print(f"[SCREENSHOT] Screenshot processing failed, continuing with empty result: {e}")
                screenshot_result = ScreenshotProcessResult(
                    task_id=task_id,
                    video_type="未识别",
                    total_timepoints=0,
                    successful_screenshots=0,
                    selected_screenshots=[],
                    processing_time=0.0
                )

            # Step 5: Save result with screenshots
            # 处理截图结果，转换为可用格式
            screenshot_data = []
            if screenshot_result and screenshot_result.selected_screenshots:
                for sr in screenshot_result.selected_screenshots:
                    screenshot_data.append({
                        "timepoint": sr.timepoint,
                        "selected": sr.selected,
                        "reasons": sr.reasons,
                        "representativeness": sr.content_representativeness
                    })

            result_data = {
                "markdown": markdown_result,
                "transcript": transcription_result,
                "audio_meta": {
                    "title": video_info.get("title", "Unknown"),
                    "duration": video_info.get("duration", 0),
                    "platform": task_data.get("platform", "generic"),
                    "video_id": video_info.get("video_id", ""),
                    "file_path": audio_path
                },
                "screenshots": screenshot_data,
                "screenshot_analysis": {
                    "video_type": screenshot_result.video_type if screenshot_result else "none",
                    "total_timepoints": screenshot_result.total_timepoints if screenshot_result else 0,
                    "successful_screenshots": screenshot_result.successful_screenshots if screenshot_result else 0,
                    "processing_time": screenshot_result.processing_time if screenshot_result else 0.0
                },
                "extras": task_data.get("extras", "")  # 保存用户备注，方便前端展示
            }

            logger.info(f"[{self.service_name}] 结果数据构建完成，包含 {len(screenshot_data)} 个截图")

            # Save result to file (for compatibility with original implementation)
            # 使用 asyncio.to_thread 处理文件 I/O 操作
            os.makedirs("output", exist_ok=True)
            result_path = f"output/{task_id}.json"

            def save_result_file():
                with open(result_path, "w", encoding="utf-8") as f:
                    json.dump(result_data, f, ensure_ascii=False, indent=2)

            await asyncio.to_thread(save_result_file)

            # Update database with result path
            self.update_task_status(
                task_id,
                "SUCCESS",
                "Task completed successfully",
                result_path=result_path
            )

            # 任务完成后的清理工作
            try:
                logger.info(f"[{self.service_name}] 开始任务完成后的清理工作")

                # 清理截图临时文件，保留最终截图
                if screenshot_result:
                    await self.screenshot_service.cleanup_on_task_complete(task_id, keep_screenshots=True)

                # 如果启用了截图且下载了视频，清理临时视频文件
                if screenshot_enabled and video_path and os.path.exists(video_path):
                    try:
                        await asyncio.to_thread(os.remove, video_path)
                        logger.info(f"[{self.service_name}] 已清理临时视频文件: {video_path}")
                    except Exception as cleanup_error:
                        logger.warning(f"[{self.service_name}] 清理视频文件失败: {cleanup_error}")

            except Exception as cleanup_error:
                logger.warning(f"[{self.service_name}] 任务完成清理失败: {cleanup_error}")

            logger.info(f"[{self.service_name}] 任务执行完成: {task_id}")
            return True

        except Exception as e:
            logger.error(f"[{self.service_name}] 任务执行失败: {task_id}, 错误: {str(e)}")
            import traceback
            logger.error(f"[{self.service_name}] 错误堆栈: {traceback.format_exc()}")

            # 任务失败时也要清理临时文件
            try:
                if screenshot_result:
                    await self.screenshot_service.cleanup_on_task_complete(task_id, keep_screenshots=False)
                if screenshot_enabled and video_path and os.path.exists(video_path):
                    await asyncio.to_thread(os.remove, video_path)
            except Exception as cleanup_error:
                logger.warning(f"[{self.service_name}] 任务失败清理失败: {cleanup_error}")

            self.update_task_status(task_id, "FAILED", f"任务执行失败: {str(e)}")
            raise Exception(f"任务执行失败: {str(e)}")