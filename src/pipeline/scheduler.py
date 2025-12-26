"""并行任务调度器"""
import asyncio
import concurrent.futures
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, List, Dict, Any, Optional, TypeVar, Generic
from queue import PriorityQueue
import threading
import time
from ..utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class TaskPriority(Enum):
    """任务优先级"""
    HIGH = 1
    NORMAL = 2
    LOW = 3


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(order=True)
class Task:
    """任务定义"""
    priority: int
    task_id: str = field(compare=False)
    func: Callable = field(compare=False)
    args: tuple = field(default_factory=tuple, compare=False)
    kwargs: dict = field(default_factory=dict, compare=False)
    status: TaskStatus = field(default=TaskStatus.PENDING, compare=False)
    result: Any = field(default=None, compare=False)
    error: Optional[Exception] = field(default=None, compare=False)
    created_at: float = field(default_factory=time.time, compare=False)
    started_at: Optional[float] = field(default=None, compare=False)
    finished_at: Optional[float] = field(default=None, compare=False)


class ParallelTaskScheduler:
    """并行任务调度器 - 支持优先级队列和并发控制"""
    
    def __init__(
        self,
        max_workers: int = 3,
        on_task_complete: Optional[Callable[[Task], None]] = None,
        on_task_error: Optional[Callable[[Task, Exception], None]] = None,
    ):
        self.max_workers = max_workers
        self.on_task_complete = on_task_complete
        self.on_task_error = on_task_error
        
        self._tasks: Dict[str, Task] = {}
        self._queue: PriorityQueue = PriorityQueue()
        self._executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
        self._lock = threading.Lock()
        self._running = False
        self._futures: Dict[str, concurrent.futures.Future] = {}
    
    def add_task(
        self,
        task_id: str,
        func: Callable,
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        **kwargs
    ) -> Task:
        """添加任务到队列"""
        task = Task(
            priority=priority.value,
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs
        )
        
        with self._lock:
            self._tasks[task_id] = task
            self._queue.put(task)
        
        logger.debug(f"任务已添加: {task_id} (优先级: {priority.name})")
        return task
    
    def add_batch(
        self,
        tasks: List[Dict[str, Any]],
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> List[Task]:
        """批量添加任务"""
        created_tasks = []
        for task_def in tasks:
            task = self.add_task(
                task_id=task_def["task_id"],
                func=task_def["func"],
                *task_def.get("args", ()),
                priority=task_def.get("priority", priority),
                **task_def.get("kwargs", {})
            )
            created_tasks.append(task)
        return created_tasks
    
    def start(self) -> None:
        """启动调度器"""
        if self._running:
            return
            
        self._running = True
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
        
        worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        worker_thread.start()
        
        logger.info(f"并行调度器已启动 (workers={self.max_workers})")
    
    def stop(self, wait: bool = True) -> None:
        """停止调度器"""
        self._running = False
        
        if self._executor:
            self._executor.shutdown(wait=wait)
            self._executor = None
        
        logger.info("并行调度器已停止")
    
    def _worker_loop(self) -> None:
        """工作循环"""
        while self._running:
            try:
                if not self._queue.empty() and len(self._futures) < self.max_workers:
                    task = self._queue.get_nowait()
                    self._submit_task(task)
                else:
                    time.sleep(0.1)
            except Exception as e:
                logger.error(f"调度器工作循环错误: {e}")
    
    def _submit_task(self, task: Task) -> None:
        """提交任务到执行器"""
        if not self._executor:
            return
            
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        
        future = self._executor.submit(self._execute_task, task)
        self._futures[task.task_id] = future
        
        def on_done(f):
            del self._futures[task.task_id]
        
        future.add_done_callback(on_done)
    
    def _execute_task(self, task: Task) -> None:
        """执行单个任务"""
        try:
            result = task.func(*task.args, **task.kwargs)
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.finished_at = time.time()
            
            logger.debug(f"任务完成: {task.task_id} (耗时: {task.finished_at - task.started_at:.2f}s)")
            
            if self.on_task_complete:
                self.on_task_complete(task)
                
        except Exception as e:
            task.error = e
            task.status = TaskStatus.FAILED
            task.finished_at = time.time()
            
            logger.error(f"任务失败: {task.task_id} - {e}")
            
            if self.on_task_error:
                self.on_task_error(task, e)
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self._tasks.get(task_id)
    
    def get_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        with self._lock:
            return {
                "running": self._running,
                "total_tasks": len(self._tasks),
                "queued": self._queue.qsize(),
                "executing": len(self._futures),
                "completed": sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED),
                "failed": sum(1 for t in self._tasks.values() if t.status == TaskStatus.FAILED),
            }
    
    def wait_all(self, timeout: Optional[float] = None) -> bool:
        """等待所有任务完成"""
        start = time.time()
        
        while True:
            status = self.get_status()
            pending = status["queued"] + status["executing"]
            
            if pending == 0:
                return True
                
            if timeout and (time.time() - start) > timeout:
                return False
                
            time.sleep(0.5)
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self._tasks.get(task_id)
        if not task:
            return False
            
        if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            task.status = TaskStatus.CANCELLED
            
            if task_id in self._futures:
                self._futures[task_id].cancel()
            
            return True
        return False


class AsyncParallelScheduler:
    """异步并行任务调度器"""
    
    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self._semaphore: Optional[asyncio.Semaphore] = None
    
    async def run_batch(
        self,
        tasks: List[Dict[str, Any]],
        on_progress: Optional[Callable[[str, str, float], None]] = None
    ) -> List[Any]:
        """批量运行异步任务"""
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        
        total = len(tasks)
        completed = [0]
        results = []
        
        async def run_task(task_def: Dict[str, Any], index: int):
            async with self._semaphore:
                task_id = task_def.get("task_id", f"task_{index}")
                func = task_def["func"]
                args = task_def.get("args", ())
                kwargs = task_def.get("kwargs", {})
                
                try:
                    if asyncio.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        loop = asyncio.get_event_loop()
                        result = await loop.run_in_executor(None, lambda: func(*args, **kwargs))
                    
                    completed[0] += 1
                    if on_progress:
                        on_progress(task_id, "completed", completed[0] / total)
                    
                    return {"task_id": task_id, "result": result, "error": None}
                    
                except Exception as e:
                    completed[0] += 1
                    logger.error(f"异步任务失败: {task_id} - {e}")
                    
                    if on_progress:
                        on_progress(task_id, "failed", completed[0] / total)
                    
                    return {"task_id": task_id, "result": None, "error": e}
        
        tasks_coros = [run_task(t, i) for i, t in enumerate(tasks)]
        results = await asyncio.gather(*tasks_coros)
        
        return results


def run_parallel_sync(
    tasks: List[Dict[str, Any]],
    max_workers: int = 3,
    on_progress: Optional[Callable[[str, float], None]] = None
) -> List[Dict[str, Any]]:
    """同步方式运行并行任务 (便捷函数)"""
    results = []
    completed = [0]
    total = len(tasks)
    lock = threading.Lock()
    
    def execute_task(task_def: Dict[str, Any]) -> Dict[str, Any]:
        task_id = task_def.get("task_id", "unknown")
        func = task_def["func"]
        args = task_def.get("args", ())
        kwargs = task_def.get("kwargs", {})
        
        try:
            result = func(*args, **kwargs)
            
            with lock:
                completed[0] += 1
                if on_progress:
                    on_progress(task_id, completed[0] / total)
            
            return {"task_id": task_id, "result": result, "error": None}
            
        except Exception as e:
            with lock:
                completed[0] += 1
                if on_progress:
                    on_progress(task_id, completed[0] / total)
            
            logger.error(f"任务失败: {task_id} - {e}")
            return {"task_id": task_id, "result": None, "error": e}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(execute_task, t) for t in tasks]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    return results
