"""
任务事件系统

支持 SSE (Server-Sent Events) 和 WebSocket 推送。
"""
import asyncio
import json
from datetime import datetime
from typing import Optional, Dict, Any, Set, AsyncGenerator
from dataclasses import dataclass, asdict

from .models import Task, TaskStatus
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TaskEvent:
    """任务事件"""
    event_type: str  # task_created, task_started, task_progress, task_completed, task_failed
    task_id: str
    task_name: str
    status: str
    progress: float
    message: str
    timestamp: str
    data: Optional[Dict[str, Any]] = None
    
    def to_sse(self) -> str:
        """转换为 SSE 格式"""
        event_data = asdict(self)
        return f"event: {self.event_type}\ndata: {json.dumps(event_data, ensure_ascii=False)}\n\n"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class TaskEventEmitter:
    """任务事件发射器
    
    支持:
    - SSE 流式推送
    - 多客户端订阅
    - 按任务ID/项目ID 过滤
    """
    
    _instance: Optional["TaskEventEmitter"] = None
    
    def __init__(self):
        # 订阅者队列
        self._subscribers: Set[asyncio.Queue] = set()
        # 最近事件缓存 (用于新连接时重放)
        self._recent_events: list = []
        self._max_recent = 50
    
    @classmethod
    def get_instance(cls) -> "TaskEventEmitter":
        """获取单例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def subscribe(self) -> AsyncGenerator[TaskEvent, None]:
        """订阅事件流"""
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(queue)
        
        try:
            # 发送最近事件
            for event in self._recent_events[-10:]:
                yield event
            
            # 等待新事件
            while True:
                event = await queue.get()
                yield event
        finally:
            self._subscribers.discard(queue)
    
    async def emit(self, event: TaskEvent) -> None:
        """发送事件"""
        # 添加到缓存
        self._recent_events.append(event)
        if len(self._recent_events) > self._max_recent:
            self._recent_events = self._recent_events[-self._max_recent:]
        
        # 发送给所有订阅者
        for queue in self._subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("事件队列已满，丢弃事件")
    
    async def emit_task_event(
        self,
        task: Task,
        event_type: str,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """发送任务事件"""
        event = TaskEvent(
            event_type=event_type,
            task_id=task.id,
            task_name=task.name,
            status=task.status.value if isinstance(task.status, TaskStatus) else task.status,
            progress=task.progress,
            message=task.message,
            timestamp=datetime.now().isoformat(),
            data=extra_data,
        )
        await self.emit(event)
    
    async def emit_progress(
        self,
        task: Task,
        progress: float,
        message: str = "",
    ) -> None:
        """发送进度更新事件"""
        event = TaskEvent(
            event_type="task_progress",
            task_id=task.id,
            task_name=task.name,
            status=task.status.value if isinstance(task.status, TaskStatus) else task.status,
            progress=progress,
            message=message,
            timestamp=datetime.now().isoformat(),
        )
        await self.emit(event)
    
    def get_subscriber_count(self) -> int:
        """获取订阅者数量"""
        return len(self._subscribers)


def get_event_emitter() -> TaskEventEmitter:
    """获取事件发射器单例"""
    return TaskEventEmitter.get_instance()

