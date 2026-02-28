"""
任务队列

实现带优先级的任务队列，支持并发控制和任务调度。
"""
import asyncio
from typing import Optional, Callable, Awaitable, List, Dict, Any
from datetime import datetime
import heapq

from .models import Task, TaskStatus, TaskPriority
from .store import TaskStore
from src.utils.logger import get_logger

logger = get_logger(__name__)


# 任务处理器类型
TaskHandler = Callable[[Task], Awaitable[Dict[str, Any]]]


class TaskQueue:
    """任务队列
    
    特性:
    - 优先级队列
    - 并发控制
    - 自动重试
    - 进度回调
    """
    
    def __init__(
        self,
        store: TaskStore,
        max_concurrent: int = 2,
        default_retry_delay: float = 1.0,
        max_retry_delay: float = 60.0,
    ):
        """初始化队列
        
        Args:
            store: 任务存储
            max_concurrent: 最大并发数
            default_retry_delay: 默认重试延迟（秒）
            max_retry_delay: 最大重试延迟（秒）
        """
        self.store = store
        self.max_concurrent = max_concurrent
        self.default_retry_delay = default_retry_delay
        self.max_retry_delay = max_retry_delay
        
        # 运行状态
        self._running = False
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._handlers: Dict[str, TaskHandler] = {}
        
        # 事件回调
        self._on_progress: Optional[Callable[[Task], None]] = None
        self._on_complete: Optional[Callable[[Task], None]] = None
        self._on_error: Optional[Callable[[Task, Exception], None]] = None
    
    def register_handler(self, task_type: str, handler: TaskHandler) -> None:
        """注册任务处理器"""
        self._handlers[task_type] = handler
        logger.info(f"注册任务处理器: {task_type}")
    
    def set_callbacks(
        self,
        on_progress: Optional[Callable[[Task], None]] = None,
        on_complete: Optional[Callable[[Task], None]] = None,
        on_error: Optional[Callable[[Task, Exception], None]] = None,
    ) -> None:
        """设置回调函数"""
        self._on_progress = on_progress
        self._on_complete = on_complete
        self._on_error = on_error
    
    async def enqueue(self, task: Task) -> Task:
        """将任务加入队列"""
        task.status = TaskStatus.QUEUED
        task.updated_at = datetime.now().isoformat()
        self.store.update(task)
        logger.info(f"任务入队: {task.name} ({task.id})")
        return task
    
    async def start(self) -> None:
        """启动队列处理"""
        if self._running:
            return
        
        self._running = True
        logger.info("任务队列启动")
        
        # 恢复未完成的任务
        await self._recover_tasks()
        
        # 启动处理循环
        asyncio.create_task(self._process_loop())
    
    async def stop(self) -> None:
        """停止队列处理"""
        self._running = False
        
        # 等待活动任务完成
        if self._active_tasks:
            logger.info(f"等待 {len(self._active_tasks)} 个任务完成...")
            await asyncio.gather(*self._active_tasks.values(), return_exceptions=True)
        
        self.store.flush()
        logger.info("任务队列已停止")
    
    async def _recover_tasks(self) -> None:
        """恢复未完成的任务"""
        # 将 RUNNING 状态的任务重置为 QUEUED
        for task in self.store.list_by_status(TaskStatus.RUNNING):
            task.status = TaskStatus.QUEUED
            self.store.update(task)
            logger.info(f"恢复任务: {task.name} ({task.id})")
    
    async def _process_loop(self) -> None:
        """任务处理循环"""
        while self._running:
            # 检查是否有空闲槽位
            if len(self._active_tasks) >= self.max_concurrent:
                await asyncio.sleep(0.1)
                continue
            
            # 获取下一个待处理任务
            pending = self.store.list_pending()
            if not pending:
                await asyncio.sleep(0.5)
                continue
            
            # 选择最高优先级任务
            task = pending[0]
            if task.id in self._active_tasks:
                await asyncio.sleep(0.1)
                continue
            
            # 启动任务
            self._active_tasks[task.id] = asyncio.create_task(
                self._process_task(task)
            )
    
    async def _process_task(self, task: Task) -> None:
        """处理单个任务"""
        handler = self._handlers.get(task.task_type)
        if not handler:
            logger.error(f"未找到任务处理器: {task.task_type}")
            task.status = TaskStatus.FAILED
            task.error = f"未知任务类型: {task.task_type}"
            self.store.update(task)
            return
        
        # 更新状态为运行中
        task.transition_to(TaskStatus.RUNNING)
        self.store.update(task)
        
        try:
            logger.info(f"开始处理任务: {task.name} ({task.id})")
            result = await handler(task)
            
            # 任务成功
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.progress = 100.0
            task.completed_at = datetime.now().isoformat()
            self.store.update(task)
            
            logger.info(f"任务完成: {task.name} ({task.id})")
            if self._on_complete:
                self._on_complete(task)
                
        except Exception as e:
            await self._handle_task_error(task, e)
        finally:
            self._active_tasks.pop(task.id, None)

    async def _handle_task_error(self, task: Task, error: Exception) -> None:
        """处理任务错误"""
        logger.error(f"任务失败: {task.name} ({task.id}): {error}")

        task.error = str(error)
        task.status = TaskStatus.FAILED
        self.store.update(task)

        if self._on_error:
            self._on_error(task, error)

        # 检查是否可以重试
        if task.can_retry():
            await self._schedule_retry(task)

    async def _schedule_retry(self, task: Task) -> None:
        """安排任务重试"""
        task.retry_count += 1

        # 指数退避
        delay = min(
            task.retry_delay * (2 ** (task.retry_count - 1)),
            self.max_retry_delay
        )

        logger.info(
            f"任务 {task.name} 将在 {delay:.1f}s 后重试 "
            f"(第 {task.retry_count}/{task.max_retries} 次)"
        )

        task.status = TaskStatus.RETRYING
        task.message = f"等待重试 ({task.retry_count}/{task.max_retries})"
        self.store.update(task)

        # 延迟后重新入队
        await asyncio.sleep(delay)

        if self._running and task.status == TaskStatus.RETRYING:
            task.status = TaskStatus.QUEUED
            task.message = ""
            self.store.update(task)

    def update_progress(self, task_id: str, progress: float, message: str = "") -> None:
        """更新任务进度"""
        task = self.store.get(task_id)
        if task and task.status == TaskStatus.RUNNING:
            task.progress = progress
            task.message = message
            self.store.update(task)

            if self._on_progress:
                self._on_progress(task)

    def cancel(self, task_id: str) -> bool:
        """取消任务"""
        task = self.store.get(task_id)
        if not task:
            return False

        if task.status in [TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.RETRYING]:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now().isoformat()
            self.store.update(task)
            logger.info(f"任务已取消: {task.name} ({task.id})")
            return True

        return False

    def get_stats(self) -> Dict[str, Any]:
        """获取队列统计"""
        counts = self.store.count()
        return {
            **counts,
            "running": len(self._active_tasks),
            "is_running": self._running,
            "max_concurrent": self.max_concurrent,
        }

