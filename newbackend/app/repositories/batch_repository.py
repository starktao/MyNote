"""
Batch Repository - Data Access Layer for Batch Tasks
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.database.batch_task import BatchTask
from app.repositories.base_repository import BaseRepository


class BatchRepository(BaseRepository[BatchTask]):
    def get_model_class(self) -> type:
        return BatchTask

    def create_with_total(self, batch_id: str, total: int) -> BatchTask:
        """Create batch task with total count"""
        batch_data = {"id": batch_id, "total": total}
        return self.create(batch_data)

    def find_by_id_with_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Find batch by ID and return status information"""
        batch = self.find_by_id(batch_id)
        if not batch:
            return None

        return {
            "batch_id": batch.id,
            "total": batch.total,
            "finished": batch.finished,
            "failed": batch.failed,
        }

    def increment_finished(self, batch_id: str) -> bool:
        """Increment finished count"""
        batch = self.find_by_id(batch_id)
        if batch:
            batch.finished += 1
            self.session.commit()
            return True
        return False

    def increment_failed(self, batch_id: str) -> bool:
        """Increment failed count"""
        batch = self.find_by_id(batch_id)
        if batch:
            batch.failed += 1
            self.session.commit()
            return True
        return False

    def increment_counters(self, batch_id: str, success: bool) -> bool:
        """Increment appropriate counter based on success"""
        if success:
            return self.increment_finished(batch_id)
        else:
            return self.increment_failed(batch_id)

    def get_progress(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get batch progress information"""
        status = self.find_by_id_with_status(batch_id)
        if not status:
            return None

        total = status["total"]
        finished = status["finished"]
        failed = status["failed"]

        return {
            **status,
            "pending": total - finished - failed,
            "progress": (finished + failed) / total if total > 0 else 0,
            "success_rate": finished / (finished + failed) if (finished + failed) > 0 else 0
        }