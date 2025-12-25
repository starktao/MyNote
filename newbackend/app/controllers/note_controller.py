"""
Note Controller - Note Generation Endpoints
"""

import os
import json
import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel
from fastapi.responses import StreamingResponse, FileResponse
import asyncio

from app.utils.response import R
from app.services.task_service import TaskService
from app.repositories.task_repository import TaskRepository
from app.config.settings import settings
from app.infrastructure.tasks.events import TaskRegistry, emit_transcribe_progress

router = APIRouter(tags=["Notes"])

# Force reload to clear cache

# Initialize task registry for SSE
task_registry = None  # Will be initialized when needed


class VideoRequest(BaseModel):
    model_config = {"protected_namespaces": ()}  # 允许 model_ 开头的字段名

    video_url: str
    platform: str = "generic"
    quality: str = "fast"
    screenshot: Optional[bool] = False
    link: Optional[bool] = False
    model_name: str
    provider_id: str
    task_id: Optional[str] = None
    format: Optional[List[str]] = []
    style: Optional[str] = "concise"
    video_type: Optional[str] = "auto"  # 视频类型：auto/tech/dialogue/science/review
    note_style: Optional[str] = "detailed"  # 笔记风格：concise/detailed/teaching/xiaohongshu
    extras: Optional[str] = None
    screenshot_mode: Optional[str] = "smart"
    screenshot_window: Optional[float] = 1.2
    screenshot_candidates: Optional[int] = 5
    export_raw_transcript: Optional[bool] = False
    screenshot_density: Optional[str] = "medium"  # 截图密度：low/medium/high


class BatchRequest(BaseModel):
    items: List[VideoRequest]
    max_concurrency: Optional[int] = None


@router.get("/notes")
async def get_notes():
    """Get all notes (placeholder)"""
    return R.success({"message": "Notes endpoint - coming soon"})


@router.get("/tasks/history")
async def get_task_history(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    provider_id: Optional[str] = None,
    model_name: Optional[str] = None,
    platform: Optional[str] = None
):
    """
    获取任务历史记录（分页）

    Args:
        page: 页码，默认1
        page_size: 每页数量，默认20，最大100
        status: 按状态过滤（可选）
        provider_id: 按提供商过滤（可选）
        model_name: 按模型名称过滤（可选）
        platform: 按平台过滤（可选）

    Returns:
        {
            "items": [...],
            "total": 总数,
            "page": 当前页,
            "page_size": 每页数量,
            "has_more": 是否有更多
        }
    """
    # 参数验证
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)

    # 构建过滤条件
    filters = {}
    if status:
        filters["status"] = status
    if provider_id:
        filters["provider_id"] = provider_id
    if model_name:
        filters["model_name"] = model_name
    if platform:
        filters["platform"] = platform

    try:
        with TaskRepository() as repo:
            total, tasks = repo.list_history(page, page_size, filters)

        # 转换为历史记录格式
        items = [task.to_history_dict() for task in tasks]

        return R.success({
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": page * page_size < total
        })

    except Exception as e:
        print(f"[ERROR] Failed to fetch task history: {str(e)}")
        return R.error(f"Failed to fetch task history: {str(e)}", 500)


@router.post("/generate_note")
async def generate_note(data: VideoRequest, background: BackgroundTasks):
    """Generate note from video URL"""
    print(f"[API] Generate note request received:")
    print(f"   - Video URL: {data.video_url}")
    print(f"   - Platform: {data.platform}")
    print(f"   - Model: {data.model_name}")
    print(f"   - Provider: {data.provider_id}")

    # Validate video_url
    if not data.video_url or not data.video_url.strip():
        return R.error("video_url cannot be empty", 400)

    # Create task
    task_service = TaskService()
    try:
        task_result = task_service.create_task(data.model_dump())
        task_id = task_result["task_id"]

        print(f"[API] Task created: {task_id}")
        print(f"[DEBUG] Full task result: {task_result}")

        # Add background task for execution
        background.add_task(execute_single_task, task_id, data.model_dump())

        response_data = {
            "task_id": task_id,
            "status": task_result["status"],
            "message": task_result["message"],
            "video_type": task_result.get("video_type", "auto"),
            "note_style": task_result.get("note_style", "detailed")
        }
        print(f"[DEBUG] Response to be sent: {response_data}")

        response = R.success(response_data)
        print(f"[DEBUG] Full response object: {response}")
        return response

    except Exception as e:
        print(f"[ERROR] Failed to create task: {str(e)}")
        return R.error(f"Failed to create task: {str(e)}", 500)


@router.post("/generate_notes")
async def generate_notes(batch: BatchRequest, background: BackgroundTasks):
    """Generate notes from multiple video URLs"""
    print(f"[API] Batch generate request received:")
    print(f"   - Items: {len(batch.items)}")
    print(f"   - Max concurrency: {batch.max_concurrency or settings.MAX_CONCURRENCY}")

    # Validate batch
    if not batch.items:
        return R.error("Batch items cannot be empty", 400)

    # Validate each item's video_url
    for i, item in enumerate(batch.items):
        if not item.video_url or not item.video_url.strip():
            return R.error(f"Item {i+1} video_url cannot be empty", 400)

    # Create batch task
    batch_id = uuid.uuid4().hex
    print(f"[API] Batch created: {batch_id}")

    # Prepare items with task IDs
    items = []
    task_ids = []
    for i, item in enumerate(batch.items):
        task_service = TaskService()
        task_result = task_service.create_task({
            **item.model_dump(),
            "batch_id": batch_id
        })

        task_id = task_result["task_id"]
        task_ids.append(task_id)
        items.append({
            **item.model_dump(),
            "task_id": task_id,
            "batch_id": batch_id
        })

        print(f"   - Task {i+1}: {task_id}")

    # Add background task for batch execution
    max_concurrency = batch.max_concurrency or settings.MAX_CONCURRENCY
    background.add_task(execute_batch, batch_id, items, max_concurrency)

    return R.success({
        "batch_id": batch_id,
        "task_ids": task_ids
    })


@router.get("/task_status/{task_id}")
async def task_status(task_id: str):
    """Get task status - lightweight implementation using direct repository access"""
    try:
        # 直接使用 Repository，避免不必要的服务初始化
        with TaskRepository() as task_repo:
            task = task_repo.find_by_id(task_id)

        if not task:
            return R.success({
                "status": "PENDING",
                "message": "Task not found",
                "task_id": task_id
            })

        # 直接构建响应数据，与 TaskService.get_task_status 保持相同的结构
        task_data = {
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

        # Check if task is successful and has result file
        if task_data["status"] == "SUCCESS" and task_data.get("result_path"):
            result_path = task_data["result_path"]
            if os.path.exists(result_path):
                with open(result_path, "r", encoding="utf-8") as f:
                    result = json.load(f)
                return R.success({
                    "status": "SUCCESS",
                    "result": result,
                    "task_id": task_id
                })

        return R.success(task_data)

    except Exception as e:
        print(f"[ERROR] Failed to get task status: {str(e)}")
        return R.error(f"Failed to get task status: {str(e)}", 500)


@router.get("/batch_status/{batch_id}")
def batch_status(batch_id: str):
    """Get batch status (placeholder)"""
    return R.success({
        "batch_id": batch_id,
        "total": 0,
        "finished": 0,
        "failed": 0
    })


@router.get("/task_events/{task_id}")
async def task_events(task_id: str):
    """
    Server-Sent Events for live task status updates.
    Frontend can consume with EventSource(`${baseURL}/task_events/${taskId}`)
    """
    global task_registry
    if task_registry is None:
        task_registry = TaskRegistry()

    async def event_gen():
        queue = task_registry.subscribe(task_id)
        try:
            while True:
                try:
                    # Wait for next event with timeout
                    data = await asyncio.wait_for(queue.get(), timeout=25.0)
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive to keep connection alive
                    yield ": keepalive\n\n"
        finally:
            task_registry.unsubscribe(task_id, queue)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
            "X-Accel-Buffering": "no",  # 禁用Nginx缓冲
        }
    )


@router.get("/download_raw_transcript/{task_id}")
async def download_raw_transcript(task_id: str):
    """Download raw transcript file"""
    try:
        # First check task status to get transcript path
        task_service = TaskService()
        task_data = task_service.get_task_status(task_id)

        if not task_data or not task_data.get("transcript_path"):
            return R.error("Transcript file not found or not exported", 404)

        transcript_path = task_data["transcript_path"]
        if not os.path.exists(transcript_path):
            return R.error("Transcript file not found", 404)

        return FileResponse(
            path=transcript_path,
            filename=f"transcript_{task_id}.txt",
            media_type="text/plain; charset=utf-8"
        )

    except Exception as e:
        print(f"[ERROR] Failed to download transcript: {str(e)}")
        return R.error(f"Failed to download transcript: {str(e)}", 500)


@router.get("/image_proxy")
async def image_proxy(request: Request, url: str):
    """Proxy image requests with proper headers"""
    from app.infrastructure.services.http_client import HttpClient

    headers = {
        "Referer": "https://www.bilibili.com/",
        "User-Agent": request.headers.get("User-Agent", ""),
    }

    try:
        async with HttpClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                return R.error("Failed to fetch image", response.status_code)

            content_type = response.headers.get("content-type", "image/jpeg")
            return StreamingResponse(
                response.aiter_bytes(),
                media_type=content_type
            )

    except Exception as e:
        print(f"[ERROR] Failed to proxy image: {str(e)}")
        return R.error(f"Failed to proxy image: {str(e)}", 500)


# Background task execution functions - 异步实现版本
async def _execute_single_task_async(task_id: str, task_data: Dict[str, Any]) -> bool:
    """Execute a single task in background - 异步实现（内部使用）"""
    try:
        task_service = TaskService()
        success = await task_service.execute_task(task_id, task_data)
        return success
    except Exception as e:
        print(f"[ERROR] Background task failed: {task_id}, Error: {str(e)}")
        import traceback
        print(f"[ERROR] Stack trace: {traceback.format_exc()}")
        # 确保任务状态被更新为失败
        try:
            task_service = TaskService()
            task_service.update_task_status(task_id, "FAILED", f"任务执行异常: {str(e)}")
        except Exception as update_error:
            print(f"[ERROR] Failed to update task status: {update_error}")
        return False


def execute_single_task(task_id: str, task_data: Dict[str, Any]) -> bool:
    """同步入口：在独立线程中运行异步任务"""
    try:
        print(f"[TASK] Starting task in background thread: {task_id}")
        result = asyncio.run(_execute_single_task_async(task_id, task_data))
        print(f"[TASK] Background task completed: {task_id}, Success: {result}")
        return result
    except Exception as e:
        print(f"[ERROR] Failed to run task in background thread: {task_id}, Error: {str(e)}")
        import traceback
        print(f"[ERROR] Stack trace: {traceback.format_exc()}")
        return False


async def _execute_batch_async(batch_id: str, items: List[Dict[str, Any]], max_concurrency: int) -> None:
    """Execute batch tasks with concurrency control - 异步实现（内部使用）"""
    semaphore = asyncio.Semaphore(max_concurrency)

    async def execute_item(item: Dict[str, Any], index: int):
        async with semaphore:
            task_id = item["task_id"]
            print(f"[BATCH] Executing task {index+1}/{len(items)}: {task_id}")
            success = await _execute_single_task_async(task_id, item)

            if success:
                print(f"[SUCCESS] Task {index+1} completed: {task_id}")
            else:
                print(f"[ERROR] Task {index+1} failed: {task_id}")

    # Execute all items concurrently
    await asyncio.gather(*[
        execute_item(item, i)
        for i, item in enumerate(items)
    ])

    print(f"[BATCH] Batch execution completed: {batch_id}")


def execute_batch(batch_id: str, items: List[Dict[str, Any]], max_concurrency: int) -> None:
    """同步入口：在独立线程中运行批量异步任务"""
    try:
        print(f"[BATCH] Starting batch in background thread: {batch_id}")
        asyncio.run(_execute_batch_async(batch_id, items, max_concurrency))
        print(f"[BATCH] Background batch completed: {batch_id}")
    except Exception as e:
        print(f"[ERROR] Failed to run batch in background thread: {batch_id}, Error: {str(e)}")
        import traceback
        print(f"[ERROR] Stack trace: {traceback.format_exc()}")


# P1.3新增：转写进度SSE端点
@router.get("/transcribe/progress/{task_id}")
async def transcribe_progress(task_id: str):
    """
    转写进度Server-Sent Events端点 - P1.3新增
    前端可以使用EventSource(`${baseURL}/transcribe/progress/${task_id}`)来监听转写进度
    """
    global task_registry
    if task_registry is None:
        task_registry = TaskRegistry()

    async def event_generator():
        """生成转写进度事件"""
        # 订阅转写进度事件
        queue = task_registry.subscribe_to_transcribe_progress(task_id)

        try:
            while True:
                try:
                    # 等待转写进度事件，25秒超时
                    data = await asyncio.wait_for(queue.get(), timeout=25.0)

                    # 格式化为SSE格式
                    event_data = {
                        "type": "transcribe_progress",
                        "task_id": task_id,
                        "data": data
                    }

                    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

                except asyncio.TimeoutError:
                    # 发送保活信号，保持连接
                    yield ": keepalive\n\n"

        except Exception as e:
            # 发生错误时发送错误事件
            error_data = {
                "type": "transcribe_progress",
                "task_id": task_id,
                "data": {
                    "status": "error",
                    "message": f"连接错误: {str(e)}",
                    "timestamp": asyncio.get_event_loop().time()
                }
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

        finally:
            # 清理订阅
            task_registry.unsubscribe_from_transcribe_progress(task_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "X-Accel-Buffering": "no",  # 禁用Nginx缓冲
            "X-Content-Type-Options": "nosniff",
        }
    )


# P1.3新增：转写进度测试端点
@router.post("/transcribe/test_progress/{task_id}")
async def test_transcribe_progress(task_id: str):
    """
    测试转写进度事件的端点 - P1.3新增
    用于模拟转写进度，便于前端测试
    """
    global task_registry

    async def simulate_progress():
        """模拟转写进度"""
        progress_steps = [
            {"status": "started", "progress": 0, "message": "开始转写"},
            {"status": "loading_model", "progress": 5, "message": "正在加载模型"},
            {"status": "model_loaded", "progress": 10, "message": "模型加载完成"},
            {"status": "transcribing", "progress": 20, "message": "开始处理音频"},
            {"status": "transcribing", "progress": 50, "message": "已处理一半内容"},
            {"status": "transcribing", "progress": 80, "message": "即将完成"},
            {"status": "completed", "progress": 100, "message": "转写完成", "result": {"text": "测试转写完成", "language": "zh"}}
        ]

        for i, step in enumerate(progress_steps):
            await asyncio.sleep(2)  # 每2秒发送一次进度

            step_data = {
                "timestamp": asyncio.get_event_loop().time(),
                **step
            }

            # 发送进度事件
            await emit_transcribe_progress(task_id, step_data)

            print(f"[TEST] 发送转写进度 {task_id}: {step}")

    # 在后台运行进度模拟
    asyncio.create_task(simulate_progress())

    return R.success({
        "message": "开始模拟转写进度",
        "task_id": task_id,
        "sse_endpoint": f"/transcribe/progress/{task_id}"
    })


