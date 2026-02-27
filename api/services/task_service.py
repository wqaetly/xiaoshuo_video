"""
任务队列服务 - 管理生成任务和日志
"""
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from collections import deque

from src.utils.config import get_config, Config
from src.utils.logger import get_logger

logger = get_logger("api.task_service")


@dataclass
class TaskData:
    """任务数据"""
    id: str
    name: str
    task_type: str  # image, audio, video, compose
    status: str = "pending"  # pending, running, completed, failed, cancelled
    progress: float = 0.0
    message: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    result: Optional[Dict[str, Any]] = None
    project_name: str = ""
    scene_id: str = ""


@dataclass
class LogData:
    """日志数据"""
    timestamp: str
    level: str
    message: str
    module: Optional[str] = None


class TaskService:
    """任务队列服务"""

    def __init__(self, config: Optional[Config] = None, max_logs: int = 1000):
        self.config = config or get_config()
        self.tasks: Dict[str, TaskData] = {}
        self.logs: deque = deque(maxlen=max_logs)
        self.is_processing: bool = False

    def create_task(
        self,
        name: str,
        task_type: str,
        project_name: str = "",
        scene_id: str = "",
    ) -> TaskData:
        """创建任务"""
        task = TaskData(
            id=f"task_{uuid.uuid4().hex[:8]}",
            name=name,
            task_type=task_type,
            project_name=project_name,
            scene_id=scene_id,
        )
        self.tasks[task.id] = task
        logger.info(f"创建任务: {task.name} ({task.id})")
        return task

    def get_task(self, task_id: str) -> Optional[TaskData]:
        """获取任务"""
        return self.tasks.get(task_id)

    def list_tasks(
        self, status: Optional[str] = None, limit: int = 100
    ) -> Dict[str, Any]:
        """列出任务"""
        tasks = list(self.tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        # 按创建时间倒序
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        tasks = tasks[:limit]
        
        # 统计
        all_tasks = list(self.tasks.values())
        return {
            "tasks": [self._task_to_dict(t) for t in tasks],
            "total": len(self.tasks),
            "running": sum(1 for t in all_tasks if t.status == "running"),
            "pending": sum(1 for t in all_tasks if t.status == "pending"),
            "completed": sum(1 for t in all_tasks if t.status == "completed"),
            "failed": sum(1 for t in all_tasks if t.status == "failed"),
        }

    def update_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
    ) -> Optional[TaskData]:
        """更新任务"""
        task = self.tasks.get(task_id)
        if task is None:
            return None
        
        if status is not None:
            task.status = status
        if progress is not None:
            task.progress = progress
        if message is not None:
            task.message = message
        if result is not None:
            task.result = result
        task.updated_at = datetime.now().isoformat()
        
        return task

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self.tasks.get(task_id)
        if task is None:
            return False
        if task.status in ["pending", "running"]:
            task.status = "cancelled"
            task.updated_at = datetime.now().isoformat()
            return True
        return False

    def clear_completed(self) -> int:
        """清除已完成任务"""
        to_remove = [tid for tid, t in self.tasks.items() if t.status in ["completed", "cancelled"]]
        for tid in to_remove:
            del self.tasks[tid]
        return len(to_remove)

    def cancel_all(self) -> int:
        """取消所有待处理任务"""
        count = 0
        for task in self.tasks.values():
            if task.status in ["pending", "running"]:
                task.status = "cancelled"
                count += 1
        return count

    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        tasks = list(self.tasks.values())
        return {
            "total_tasks": len(tasks),
            "running": sum(1 for t in tasks if t.status == "running"),
            "pending": sum(1 for t in tasks if t.status == "pending"),
            "completed": sum(1 for t in tasks if t.status == "completed"),
            "failed": sum(1 for t in tasks if t.status == "failed"),
            "is_processing": self.is_processing,
        }

    def add_log(self, level: str, message: str, module: Optional[str] = None) -> None:
        """添加日志"""
        log = LogData(
            timestamp=datetime.now().isoformat(),
            level=level.upper(),
            message=message,
            module=module,
        )
        self.logs.append(log)

    def get_logs(
        self, level: Optional[str] = None, limit: int = 100
    ) -> Dict[str, Any]:
        """获取日志"""
        logs = list(self.logs)

        if level:
            logs = [l for l in logs if l.level == level.upper()]

        # 倒序，最新的在前
        logs = logs[-limit:][::-1]

        return {
            "logs": [
                {
                    "timestamp": l.timestamp,
                    "level": l.level,
                    "message": l.message,
                    "module": l.module,
                }
                for l in logs
            ],
            "total": len(self.logs),
        }

    def clear_logs(self) -> None:
        """清除日志"""
        self.logs.clear()

    def _task_to_dict(self, task: TaskData) -> Dict[str, Any]:
        """任务转字典"""
        return {
            "id": task.id,
            "name": task.name,
            "task_type": task.task_type,
            "status": task.status,
            "progress": task.progress,
            "message": task.message,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "result": task.result,
        }


# 单例模式
_task_service: Optional[TaskService] = None


def get_task_service() -> TaskService:
    """获取任务服务实例"""
    global _task_service
    if _task_service is None:
        _task_service = TaskService()
    return _task_service

