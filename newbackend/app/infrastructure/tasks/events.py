"""
Task Event Management for SSE
P1.2新增：支持转写进度事件管理
"""

from typing import Dict, Any, Optional, Callable, List
import asyncio
import json


class TaskRegistry:
    """Registry for managing SSE task events"""

    def __init__(self):
        self._task_connections: Dict[str, Any] = {}
        self._task_data: Dict[str, Dict[str, Any]] = {}
        self._listeners: Dict[str, List[asyncio.Queue]] = {}
        # P1.2新增：转写进度监听器
        self._transcribe_listeners: Dict[str, List[Callable]] = {}

    def register_task(self, task_id: str) -> None:
        """Register a new task"""
        self._task_data[task_id] = {
            "status": "pending",
            "progress": 0,
            "message": "Task created",
            "result": None,
            "error": None
        }
        print(f"[TASK_REGISTRY] Registered task: {task_id}")

    def update_task(self, task_id: str, data: Dict[str, Any]) -> None:
        """Update task status/data"""
        if task_id in self._task_data:
            self._task_data[task_id].update(data)
            print(f"[TASK_REGISTRY] Updated task {task_id}: {data}")

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task data"""
        return self._task_data.get(task_id)

    def remove_task(self, task_id: str) -> None:
        """Remove task from registry"""
        if task_id in self._task_data:
            del self._task_data[task_id]
        if task_id in self._task_connections:
            del self._task_connections[task_id]
        print(f"[TASK_REGISTRY] Removed task: {task_id}")

    async def send_task_update(self, task_id: str, event_type: str = "update") -> None:
        """Send SSE update to connected clients"""
        if task_id in self._task_connections:
            data = self._task_data.get(task_id, {})
            await self._task_connections[task_id].put({
                "event": event_type,
                "data": json.dumps(data)
            })

    def create_task_queue(self, task_id: str) -> asyncio.Queue:
        """Create a queue for task SSE events"""
        queue = asyncio.Queue()
        self._task_connections[task_id] = queue
        return queue

    def get_task_queue(self, task_id: str) -> Optional[asyncio.Queue]:
        """Get task event queue"""
        return self._task_connections.get(task_id)

    def subscribe(self, task_id: str) -> asyncio.Queue:
        """Subscribe to task events"""
        queue = asyncio.Queue()
        self._listeners.setdefault(task_id, []).append(queue)
        return queue

    def unsubscribe(self, task_id: str, queue: asyncio.Queue) -> None:
        """Unsubscribe from task events"""
        if task_id in self._listeners:
            try:
                self._listeners[task_id].remove(queue)
            except ValueError:
                pass

    def publish(self, task_id: str, data: Dict[str, Any]) -> None:
        """Publish event to all subscribers with logging and error handling"""
        if task_id in self._listeners:
            subscriber_count = len(self._listeners[task_id])
            print(f"[TASK_REGISTRY] 发布事件到 {subscriber_count} 个订阅者 (任务 {task_id}): {data}")

            failed_queues = []
            for queue in self._listeners[task_id]:
                try:
                    queue.put_nowait(data)
                except asyncio.QueueFull:
                    failed_queues.append(queue)
                    print(f"[TASK_REGISTRY] 队列已满，跳过事件发布 (任务 {task_id})")

            # 清理失败的队列连接
            if failed_queues:
                self._listeners[task_id] = [q for q in self._listeners[task_id] if q not in failed_queues]
                print(f"[TASK_REGISTRY] 清理了 {len(failed_queues)} 个失败的队列连接")

    # P1.2新增：转写进度事件管理方法
    async def emit_transcribe_progress(self, task_id: str, progress_data: Dict[str, Any]) -> None:
        """发送转写进度事件"""
        try:
            # 使用现有的发布机制发送转写进度
            event_data = {
                "event_type": "transcribe_progress",
                "task_id": task_id,
                "timestamp": progress_data.get("timestamp", asyncio.get_event_loop().time()),
                "data": progress_data
            }

            # 发布到常规监听器
            self.publish(f"transcribe_progress:{task_id}", event_data)

            # 同时发布到任务专用频道
            self.publish(task_id, event_data)

            print(f"[TASK_REGISTRY] 发送转写进度事件 (任务 {task_id}): {progress_data.get('status', 'unknown')} - {progress_data.get('progress', 0)}%")

        except Exception as e:
            print(f"[TASK_REGISTRY] 发送转写进度事件失败 (任务 {task_id}): {e}")

    def register_transcribe_progress_listener(self, task_id: str, callback: Callable) -> None:
        """注册转写进度监听器"""
        if task_id not in self._transcribe_listeners:
            self._transcribe_listeners[task_id] = []
        self._transcribe_listeners[task_id].append(callback)
        print(f"[TASK_REGISTRY] 注册转写进度监听器 (任务 {task_id})")

    def unregister_transcribe_progress_listener(self, task_id: str, callback: Callable) -> None:
        """取消注册转写进度监听器"""
        if task_id in self._transcribe_listeners:
            try:
                self._transcribe_listeners[task_id].remove(callback)
                print(f"[TASK_REGISTRY] 取消注册转写进度监听器 (任务 {task_id})")
            except ValueError:
                pass

    async def notify_transcribe_listeners(self, task_id: str, progress_data: Dict[str, Any]) -> None:
        """通知所有转写进度监听器"""
        if task_id in self._transcribe_listeners:
            listener_count = len(self._transcribe_listeners[task_id])
            print(f"[TASK_REGISTRY] 通知 {listener_count} 个转写进度监听器 (任务 {task_id})")

            failed_callbacks = []
            for callback in self._transcribe_listeners[task_id]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(task_id, progress_data)
                    else:
                        callback(task_id, progress_data)
                except Exception as e:
                    failed_callbacks.append(callback)
                    print(f"[TASK_REGISTRY] 转写进度回调失败 (任务 {task_id}): {e}")

            # 清理失败的回调
            if failed_callbacks:
                self._transcribe_listeners[task_id] = [
                    cb for cb in self._transcribe_listeners[task_id]
                    if cb not in failed_callbacks
                ]
                print(f"[TASK_REGISTRY] 清理了 {len(failed_callbacks)} 个失败的转写进度回调")

    def subscribe_to_transcribe_progress(self, task_id: str) -> asyncio.Queue:
        """订阅转写进度事件"""
        return self.subscribe(f"transcribe_progress:{task_id}")

    def unsubscribe_from_transcribe_progress(self, task_id: str, queue: asyncio.Queue) -> None:
        """取消订阅转写进度事件"""
        self.unsubscribe(f"transcribe_progress:{task_id}", queue)


# Global task registry instance
task_registry = TaskRegistry()

# P1.2新增：全局转写进度事件发射器
async def emit_transcribe_progress(task_id: str, progress_data: Dict[str, Any]) -> None:
    """全局转写进度事件发射器函数"""
    await task_registry.emit_transcribe_progress(task_id, progress_data)