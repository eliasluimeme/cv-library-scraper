"""
Task manager for handling background operations.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from api.models.schemas import TaskResult


class TaskManager:
    """Simple task manager for background operations."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.tasks: Dict[str, TaskResult] = {}
        self.active_tasks: Dict[str, asyncio.Task] = {}
    
    def create_task(self, task_func, *args, **kwargs) -> str:
        """Create and track a background task."""
        task_id = str(uuid.uuid4())
        
        task_result = TaskResult(
            task_id=task_id,
            status="pending",
            created_at=datetime.utcnow()
        )
        
        self.tasks[task_id] = task_result
        
        # Create asyncio task
        async_task = asyncio.create_task(self._run_task(task_id, task_func, *args, **kwargs))
        self.active_tasks[task_id] = async_task
        
        return task_id
    
    async def _run_task(self, task_id: str, task_func, *args, **kwargs):
        """Run a task and update its status."""
        task_result = self.tasks[task_id]
        
        try:
            task_result.status = "running"
            task_result.started_at = datetime.utcnow()
            
            # Run the task function
            if asyncio.iscoroutinefunction(task_func):
                result = await task_func(*args, **kwargs)
            else:
                result = task_func(*args, **kwargs)
            
            # Update result
            task_result.status = "completed"
            task_result.result = result
            task_result.completed_at = datetime.utcnow()
            
            if task_result.started_at:
                duration = (task_result.completed_at - task_result.started_at).total_seconds()
                task_result.duration = duration
            
        except Exception as e:
            task_result.status = "failed"
            task_result.error = str(e)
            task_result.completed_at = datetime.utcnow()
            self.logger.error(f"Task {task_id} failed: {e}")
        
        finally:
            # Remove from active tasks
            self.active_tasks.pop(task_id, None)
    
    def get_task(self, task_id: str) -> Optional[TaskResult]:
        """Get task status and result."""
        return self.tasks.get(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        task = self.active_tasks.get(task_id)
        if task and not task.done():
            task.cancel()
            
            task_result = self.tasks.get(task_id)
            if task_result:
                task_result.status = "cancelled"
                task_result.completed_at = datetime.utcnow()
            
            return True
        
        return False
    
    async def cleanup(self):
        """Clean up all tasks."""
        for task_id, task in self.active_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self.active_tasks.clear()
        self.logger.info("TaskManager cleanup completed") 