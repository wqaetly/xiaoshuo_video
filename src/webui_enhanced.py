"""WebUI增强模块 - 实时日志、任务队列、批量操作、WebSocket支持"""
import asyncio
import queue
import threading
import time
import json
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, Any, List, Optional, Generator, Set
from .utils.logger import get_logger

logger = get_logger(__name__)


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: datetime
    level: LogLevel
    module: str
    message: str
    
    def format(self) -> str:
        ts = self.timestamp.strftime("%H:%M:%S")
        return f"[{ts}] [{self.level.value}] {self.module}: {self.message}"


class RealtimeLogHandler:
    """实时日志处理器 - 支持WebUI流式显示"""
    
    def __init__(self, max_entries: int = 500):
        self.max_entries = max_entries
        self._logs: deque = deque(maxlen=max_entries)
        self._subscribers: List[queue.Queue] = []
        self._lock = threading.Lock()
    
    def add_log(self, level: LogLevel, module: str, message: str) -> None:
        """添加日志"""
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            module=module,
            message=message
        )
        
        with self._lock:
            self._logs.append(entry)
            for q in self._subscribers:
                try:
                    q.put_nowait(entry)
                except queue.Full:
                    pass
    
    def info(self, module: str, message: str) -> None:
        self.add_log(LogLevel.INFO, module, message)
    
    def warning(self, module: str, message: str) -> None:
        self.add_log(LogLevel.WARNING, module, message)
    
    def error(self, module: str, message: str) -> None:
        self.add_log(LogLevel.ERROR, module, message)
    
    def debug(self, module: str, message: str) -> None:
        self.add_log(LogLevel.DEBUG, module, message)
    
    def subscribe(self) -> queue.Queue:
        """订阅日志流"""
        q = queue.Queue(maxsize=100)
        with self._lock:
            self._subscribers.append(q)
        return q
    
    def unsubscribe(self, q: queue.Queue) -> None:
        """取消订阅"""
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)
    
    def get_recent(self, count: int = 50) -> List[str]:
        """获取最近的日志"""
        with self._lock:
            entries = list(self._logs)[-count:]
        return [e.format() for e in entries]
    
    def get_logs_generator(self, timeout: float = 0.5) -> Generator[str, None, None]:
        """生成器方式获取日志流"""
        q = self.subscribe()
        try:
            while True:
                try:
                    entry = q.get(timeout=timeout)
                    yield entry.format()
                except queue.Empty:
                    yield ""
        finally:
            self.unsubscribe(q)
    
    def clear(self) -> None:
        """清空日志"""
        with self._lock:
            self._logs.clear()


class WebSocketLogBroadcaster:
    """WebSocket日志广播器 - 支持实时推送日志到客户端"""
    
    def __init__(self, log_handler: RealtimeLogHandler):
        self.log_handler = log_handler
        self._clients: Set[asyncio.Queue] = set()
        self._lock = threading.Lock()
        self._running = False
        self._broadcast_task: Optional[asyncio.Task] = None
    
    def add_client(self) -> asyncio.Queue:
        """添加WebSocket客户端"""
        client_queue = asyncio.Queue(maxsize=100)
        with self._lock:
            self._clients.add(client_queue)
        logger.debug(f"WebSocket客户端已连接, 当前连接数: {len(self._clients)}")
        return client_queue
    
    def remove_client(self, client_queue: asyncio.Queue) -> None:
        """移除WebSocket客户端"""
        with self._lock:
            self._clients.discard(client_queue)
        logger.debug(f"WebSocket客户端已断开, 当前连接数: {len(self._clients)}")
    
    async def broadcast(self, message: Dict[str, Any]) -> None:
        """广播消息到所有客户端"""
        msg_json = json.dumps(message, ensure_ascii=False, default=str)
        dead_clients = []
        
        with self._lock:
            clients = list(self._clients)
        
        for client_queue in clients:
            try:
                client_queue.put_nowait(msg_json)
            except asyncio.QueueFull:
                dead_clients.append(client_queue)
        
        # 清理死连接
        for dead in dead_clients:
            self.remove_client(dead)
    
    async def start_broadcasting(self) -> None:
        """启动日志广播循环"""
        self._running = True
        log_queue = self.log_handler.subscribe()
        
        try:
            while self._running:
                try:
                    # 非阻塞获取日志
                    entry = log_queue.get_nowait()
                    await self.broadcast({
                        "type": "log",
                        "data": entry.format(),
                        "timestamp": datetime.now().isoformat()
                    })
                except queue.Empty:
                    await asyncio.sleep(0.1)
        finally:
            self.log_handler.unsubscribe(log_queue)
    
    def stop(self) -> None:
        """停止广播"""
        self._running = False
    
    @property
    def client_count(self) -> int:
        """获取当前连接的客户端数量"""
        with self._lock:
            return len(self._clients)
    
    async def send_to_client(self, client_queue: asyncio.Queue, timeout: float = 30.0) -> Optional[str]:
        """从客户端队列获取消息(用于WebSocket handler)"""
        try:
            return await asyncio.wait_for(client_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None


class TaskProgressBroadcaster:
    """任务进度广播器"""
    
    def __init__(self, ws_broadcaster: WebSocketLogBroadcaster):
        self.ws_broadcaster = ws_broadcaster
    
    async def on_task_progress(self, task_id: str, progress: float, message: str) -> None:
        """任务进度更新回调"""
        await self.ws_broadcaster.broadcast({
            "type": "task_progress",
            "task_id": task_id,
            "progress": progress,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    async def on_task_complete(self, task_id: str, success: bool, message: str) -> None:
        """任务完成回调"""
        await self.ws_broadcaster.broadcast({
            "type": "task_complete",
            "task_id": task_id,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class UITask:
    """UI任务定义"""
    task_id: str
    name: str
    task_type: str
    params: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    message: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None


class TaskQueue:
    """任务队列管理器"""
    
    def __init__(self, max_concurrent: int = 1):
        self.max_concurrent = max_concurrent
        self._tasks: Dict[str, UITask] = {}
        self._pending: deque = deque()
        self._running: Dict[str, threading.Thread] = {}
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._task_handlers: Dict[str, Callable] = {}
        self._on_progress: Optional[Callable[[str, float, str], None]] = None
        self._on_complete: Optional[Callable[[str, bool, str], None]] = None
        self._worker_thread: Optional[threading.Thread] = None
    
    def register_handler(self, task_type: str, handler: Callable) -> None:
        """注册任务处理器"""
        self._task_handlers[task_type] = handler
    
    def set_callbacks(
        self,
        on_progress: Optional[Callable[[str, float, str], None]] = None,
        on_complete: Optional[Callable[[str, bool, str], None]] = None
    ) -> None:
        """设置回调函数"""
        self._on_progress = on_progress
        self._on_complete = on_complete
    
    def add_task(
        self,
        task_id: str,
        name: str,
        task_type: str,
        **params
    ) -> UITask:
        """添加任务到队列"""
        task = UITask(
            task_id=task_id,
            name=name,
            task_type=task_type,
            params=params
        )
        
        with self._lock:
            self._tasks[task_id] = task
            self._pending.append(task_id)
        
        logger.info(f"任务已添加: {task_id} ({name})")
        return task
    
    def add_batch(self, tasks: List[Dict[str, Any]]) -> List[UITask]:
        """批量添加任务"""
        created = []
        for t in tasks:
            task = self.add_task(
                task_id=t["task_id"],
                name=t["name"],
                task_type=t["task_type"],
                **t.get("params", {})
            )
            created.append(task)
        return created
    
    def start(self) -> None:
        """启动任务队列处理"""
        if self._worker_thread and self._worker_thread.is_alive():
            return
        
        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        logger.info("任务队列已启动")
    
    def stop(self) -> None:
        """停止任务队列"""
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        logger.info("任务队列已停止")
    
    def _worker_loop(self) -> None:
        """工作循环"""
        while not self._stop_event.is_set():
            with self._lock:
                if self._pending and len(self._running) < self.max_concurrent:
                    task_id = self._pending.popleft()
                    self._start_task(task_id)
            time.sleep(0.1)
    
    def _start_task(self, task_id: str) -> None:
        """启动单个任务"""
        task = self._tasks.get(task_id)
        if not task:
            return
        
        handler = self._task_handlers.get(task.task_type)
        if not handler:
            task.status = TaskStatus.FAILED
            task.error = f"未知任务类型: {task.task_type}"
            return
        
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        thread = threading.Thread(
            target=self._execute_task,
            args=(task, handler),
            daemon=True
        )
        self._running[task_id] = thread
        thread.start()
    
    def _execute_task(self, task: UITask, handler: Callable) -> None:
        """执行任务"""
        try:
            def progress_callback(progress: float, message: str = ""):
                task.progress = progress
                task.message = message
                if self._on_progress:
                    self._on_progress(task.task_id, progress, message)
            
            result = handler(task.params, progress_callback)
            
            task.status = TaskStatus.COMPLETED
            task.progress = 1.0
            task.finished_at = datetime.now()
            
            if self._on_complete:
                self._on_complete(task.task_id, True, "完成")
                
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.finished_at = datetime.now()
            logger.error(f"任务失败 {task.task_id}: {e}")
            
            if self._on_complete:
                self._on_complete(task.task_id, False, str(e))
        
        finally:
            with self._lock:
                if task.task_id in self._running:
                    del self._running[task.task_id]
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            
            if task.status == TaskStatus.PENDING:
                if task_id in self._pending:
                    self._pending.remove(task_id)
                task.status = TaskStatus.CANCELLED
                return True
            
            return False
    
    def get_task(self, task_id: str) -> Optional[UITask]:
        """获取任务"""
        return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> List[UITask]:
        """获取所有任务"""
        return list(self._tasks.values())
    
    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        with self._lock:
            return {
                "pending": len(self._pending),
                "running": len(self._running),
                "total": len(self._tasks),
                "completed": sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED),
                "failed": sum(1 for t in self._tasks.values() if t.status == TaskStatus.FAILED),
            }
    
    def clear_completed(self) -> int:
        """清除已完成的任务"""
        removed = 0
        with self._lock:
            to_remove = [
                tid for tid, t in self._tasks.items()
                if t.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
            ]
            for tid in to_remove:
                del self._tasks[tid]
                removed += 1
        return removed


class BatchOperations:
    """批量操作管理器"""
    
    def __init__(self, task_queue: TaskQueue, log_handler: RealtimeLogHandler):
        self.task_queue = task_queue
        self.log = log_handler
    
    def regenerate_scenes(
        self,
        scene_ids: List[str],
        regenerate_image: bool = True,
        regenerate_audio: bool = True,
        regenerate_video: bool = False
    ) -> List[str]:
        """批量重新生成场景"""
        task_ids = []
        
        for scene_id in scene_ids:
            if regenerate_image:
                task_id = f"regen_image_{scene_id}_{int(time.time())}"
                self.task_queue.add_task(
                    task_id=task_id,
                    name=f"重新生成图像: {scene_id}",
                    task_type="regenerate_image",
                    scene_id=scene_id
                )
                task_ids.append(task_id)
            
            if regenerate_audio:
                task_id = f"regen_audio_{scene_id}_{int(time.time())}"
                self.task_queue.add_task(
                    task_id=task_id,
                    name=f"重新生成音频: {scene_id}",
                    task_type="regenerate_audio",
                    scene_id=scene_id
                )
                task_ids.append(task_id)
            
            if regenerate_video:
                task_id = f"regen_video_{scene_id}_{int(time.time())}"
                self.task_queue.add_task(
                    task_id=task_id,
                    name=f"重新生成视频: {scene_id}",
                    task_type="regenerate_video",
                    scene_id=scene_id
                )
                task_ids.append(task_id)
        
        self.log.info("BatchOps", f"已添加 {len(task_ids)} 个重新生成任务")
        return task_ids
    
    def delete_scenes(self, scene_ids: List[str], storyboard_path) -> int:
        """批量删除场景"""
        from .utils.file_utils import load_json, save_json
        
        storyboard = load_json(storyboard_path)
        scenes = storyboard.get("scenes", [])
        
        original_count = len(scenes)
        scenes = [s for s in scenes if s.get("id") not in scene_ids]
        
        storyboard["scenes"] = scenes
        storyboard["total_scenes"] = len(scenes)
        save_json(storyboard_path, storyboard)
        
        deleted = original_count - len(scenes)
        self.log.info("BatchOps", f"已删除 {deleted} 个场景")
        return deleted
    
    def update_scene_status(
        self,
        scene_ids: List[str],
        status_type: str,
        new_status: str,
        storyboard_path
    ) -> int:
        """批量更新场景状态"""
        from .utils.file_utils import load_json, save_json
        
        storyboard = load_json(storyboard_path)
        scenes = storyboard.get("scenes", [])
        
        updated = 0
        for scene in scenes:
            if scene.get("id") in scene_ids:
                if "generation_status" not in scene:
                    scene["generation_status"] = {}
                scene["generation_status"][status_type] = new_status
                updated += 1
        
        save_json(storyboard_path, storyboard)
        self.log.info("BatchOps", f"已更新 {updated} 个场景的 {status_type} 状态为 {new_status}")
        return updated
    
    def export_scenes_data(self, scene_ids: List[str], storyboard_path, output_path) -> bool:
        """导出选中场景数据"""
        from .utils.file_utils import load_json, save_json
        
        storyboard = load_json(storyboard_path)
        scenes = storyboard.get("scenes", [])
        
        selected_scenes = [s for s in scenes if s.get("id") in scene_ids]
        
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "scene_count": len(selected_scenes),
            "scenes": selected_scenes
        }
        
        save_json(output_path, export_data)
        self.log.info("BatchOps", f"已导出 {len(selected_scenes)} 个场景到 {output_path}")
        return True


_log_handler: Optional[RealtimeLogHandler] = None
_task_queue: Optional[TaskQueue] = None
_ws_broadcaster: Optional[WebSocketLogBroadcaster] = None


def get_log_handler() -> RealtimeLogHandler:
    """获取全局日志处理器"""
    global _log_handler
    if _log_handler is None:
        _log_handler = RealtimeLogHandler()
    return _log_handler


def get_task_queue() -> TaskQueue:
    """获取全局任务队列"""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue(max_concurrent=2)
    return _task_queue


def get_ws_broadcaster() -> WebSocketLogBroadcaster:
    """获取全局WebSocket日志广播器"""
    global _ws_broadcaster
    if _ws_broadcaster is None:
        _ws_broadcaster = WebSocketLogBroadcaster(get_log_handler())
    return _ws_broadcaster


def create_websocket_handler():
    """创建WebSocket处理函数(用于FastAPI/Starlette集成)
    
    使用示例:
    ```python
    from fastapi import FastAPI, WebSocket
    from starlette.websockets import WebSocketDisconnect
    
    app = FastAPI()
    
    @app.websocket("/ws/logs")
    async def websocket_logs(websocket: WebSocket):
        await websocket.accept()
        broadcaster = get_ws_broadcaster()
        client_queue = broadcaster.add_client()
        
        try:
            while True:
                message = await broadcaster.send_to_client(client_queue, timeout=30.0)
                if message:
                    await websocket.send_text(message)
                else:
                    # 发送心跳
                    await websocket.send_text('{"type": "ping"}')
        except WebSocketDisconnect:
            pass
        finally:
            broadcaster.remove_client(client_queue)
    ```
    """
    return get_ws_broadcaster()
