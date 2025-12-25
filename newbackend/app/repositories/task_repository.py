"""
Task Repository - Data Access Layer for Video Tasks
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.database.video_task import VideoTask
from app.repositories.base_repository import BaseRepository


class TaskRepository(BaseRepository[VideoTask]):
    def get_model_class(self) -> type:
        return VideoTask

    def update_status(self, task_id: str, status: str, message: str = "", **changes: Any) -> Optional[VideoTask]:
        """Update task status and message"""
        task = self.find_by_id(task_id)
        if not task:
            return None

        task.status = status
        task.message = message

        for key, value in changes.items():
            if hasattr(task, key):
                setattr(task, key, value)

        self.session.commit()
        return task

    def find_by_video_id_and_platform(self, video_id: str, platform: str) -> Optional[VideoTask]:
        """Find task by video ID and platform"""
        return (
            self.session.query(VideoTask)
            .filter(VideoTask.video_id == video_id, VideoTask.platform == platform)
            .first()
        )

    def find_pending_tasks(self) -> List[VideoTask]:
        """Find all pending tasks"""
        return (
            self.session.query(VideoTask)
            .filter(VideoTask.status == "PENDING")
            .all()
        )

    def find_running_tasks(self) -> List[VideoTask]:
        """Find all running tasks"""
        return (
            self.session.query(VideoTask)
            .filter(VideoTask.status.in_(["RUNNING", "TRANSCRIBING", "GENERATING"]))
            .all()
        )

    def find_by_batch_id(self, batch_id: str) -> List[VideoTask]:
        """Find tasks by batch ID"""
        return (
            self.session.query(VideoTask)
            .filter(VideoTask.batch_id == batch_id)
            .all()
        )

    def find_by_provider_and_model(self, provider_id: str, model_name: str) -> List[VideoTask]:
        """Find tasks by provider and model"""
        return (
            self.session.query(VideoTask)
            .filter(
                and_(
                    VideoTask.provider_id == provider_id,
                    VideoTask.model_name == model_name
                )
            )
            .all()
        )

    def update_result_paths(self, task_id: str, **paths: str) -> Optional[VideoTask]:
        """Update result file paths"""
        task = self.find_by_id(task_id)
        if not task:
            return None

        for path_name, path_value in paths.items():
            if hasattr(task, path_name):
                setattr(task, path_name, path_value)

        self.session.commit()
        return task

    def find_completed_tasks(self) -> List[VideoTask]:
        """Find all completed tasks"""
        return (
            self.session.query(VideoTask)
            .filter(VideoTask.status == "SUCCESS")
            .all()
        )

    def find_failed_tasks(self) -> List[VideoTask]:
        """Find all failed tasks"""
        return (
            self.session.query(VideoTask)
            .filter(VideoTask.status == "FAILED")
            .all()
        )

    def list_history(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> tuple[int, List[VideoTask]]:
        """
        分页查询任务历史记录

        Args:
            page: 页码，从1开始
            page_size: 每页数量
            filters: 过滤条件，支持 status、provider_id、model_name、platform

        Returns:
            (总数, 任务列表) 元组
        """
        query = self.session.query(VideoTask)

        # 应用过滤条件
        if filters:
            if status := filters.get("status"):
                query = query.filter(VideoTask.status == status)
            if provider_id := filters.get("provider_id"):
                query = query.filter(VideoTask.provider_id == provider_id)
            if model_name := filters.get("model_name"):
                query = query.filter(VideoTask.model_name == model_name)
            if platform := filters.get("platform"):
                query = query.filter(VideoTask.platform == platform)

        # 获取总数
        total = query.count()

        # 分页查询，按创建时间倒序
        tasks = (
            query.order_by(VideoTask.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return total, tasks