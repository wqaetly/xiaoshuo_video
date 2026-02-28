"""
任务管理器

整合任务存储和队列，提供统一的任务管理接口。
"""
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable, Awaitable

from .models import Task, TaskStatus, TaskPriority, TaskType
from .store import TaskStore
from .queue import TaskQueue, TaskHandler
from src.utils.logger import get_logger
from src.utils.config import get_config

logger = get_logger(__name__)


class TaskManager:
    """任务管理器
    
    提供统一的任务管理接口:
    - 创建/查询/取消任务
    - 注册处理器
    - 启动/停止队列
    - 监听任务事件
    """
    
    _instance: Optional["TaskManager"] = None
    
    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        max_concurrent: int = 2,
    ):
        """初始化管理器"""
        config = get_config()
        
        # 初始化存储
        storage_path = storage_dir or Path(config.data_dir) / "tasks"
        self.store = TaskStore(storage_dir=storage_path)
        
        # 初始化队列
        self.queue = TaskQueue(
            store=self.store,
            max_concurrent=max_concurrent,
        )
        
        # 事件监听器
        self._listeners: Dict[str, List[Callable]] = {
            "progress": [],
            "complete": [],
            "error": [],
        }
        
        # 设置队列回调
        self.queue.set_callbacks(
            on_progress=self._emit_progress,
            on_complete=self._emit_complete,
            on_error=self._emit_error,
        )
    
    @classmethod
    def get_instance(cls) -> "TaskManager":
        """获取单例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def create_task(
        self,
        name: str,
        task_type: str,
        params: Optional[Dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        project_id: Optional[str] = None,
        scene_id: Optional[str] = None,
        auto_enqueue: bool = True,
    ) -> Task:
        """创建任务"""
        task = Task.create(
            name=name,
            task_type=task_type,
            params=params,
            priority=priority,
            project_id=project_id,
            scene_id=scene_id,
        )
        
        self.store.add(task)
        logger.info(f"创建任务: {task.name} ({task.id})")
        
        if auto_enqueue:
            await self.queue.enqueue(task)
        
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.store.get(task_id)
    
    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        project_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Task]:
        """列出任务"""
        tasks = self.store.list_all()
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        if project_id:
            tasks = [t for t in tasks if t.project_id == project_id]
        
        # 按更新时间排序
        tasks.sort(key=lambda t: t.updated_at, reverse=True)
        return tasks[:limit]
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        return self.queue.cancel(task_id)
    
    def register_handler(self, task_type: str, handler: TaskHandler) -> None:
        """注册任务处理器"""
        self.queue.register_handler(task_type, handler)
    
    async def start(self) -> None:
        """启动任务管理器"""
        await self.queue.start()
        logger.info("任务管理器已启动")
    
    async def stop(self) -> None:
        """停止任务管理器"""
        await self.queue.stop()
        logger.info("任务管理器已停止")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.queue.get_stats()
    
    def on(self, event: str, callback: Callable) -> None:
        """监听事件"""
        if event in self._listeners:
            self._listeners[event].append(callback)
    
    def _emit_progress(self, task: Task) -> None:
        for cb in self._listeners["progress"]:
            cb(task)
    
    def _emit_complete(self, task: Task) -> None:
        for cb in self._listeners["complete"]:
            cb(task)
    
    def _emit_error(self, task: Task, error: Exception) -> None:
        for cb in self._listeners["error"]:
            cb(task, error)


def get_task_manager() -> TaskManager:
    """获取任务管理器单例"""
    return TaskManager.get_instance()

