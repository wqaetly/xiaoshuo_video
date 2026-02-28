"""
增强型任务队列系统

借鉴 waoowaoo 的 BullMQ 设计，实现:
- 任务持久化存储 (JSON 文件)
- 完整的状态机
- 可配置重试机制
- 进度追踪和 SSE 推送
"""

from .models import Task, TaskStatus, TaskPriority, TaskType
from .store import TaskStore
from .queue import TaskQueue
from .manager import TaskManager, get_task_manager
from .events import TaskEvent, TaskEventEmitter, get_event_emitter

__all__ = [
    "Task",
    "TaskStatus",
    "TaskPriority",
    "TaskType",
    "TaskStore",
    "TaskQueue",
    "TaskManager",
    "get_task_manager",
    "TaskEvent",
    "TaskEventEmitter",
    "get_event_emitter",
]

