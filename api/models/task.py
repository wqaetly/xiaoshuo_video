"""
任务队列数据模型
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class Task(BaseModel):
    """任务信息"""
    id: str
    name: str
    task_type: str  # image, audio, video, compose
    status: str  # pending, running, completed, failed, cancelled
    progress: float = 0.0
    message: str = ""
    created_at: str
    updated_at: str
    result: Optional[Dict[str, Any]] = None


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: List[Task]
    total: int
    running: int = 0
    pending: int = 0
    completed: int = 0
    failed: int = 0


class QueueStatus(BaseModel):
    """队列状态"""
    total_tasks: int = 0
    running: int = 0
    pending: int = 0
    completed: int = 0
    failed: int = 0
    is_processing: bool = False


class BatchOperationRequest(BaseModel):
    """批量操作请求"""
    scene_ids: List[str]
    regenerate_image: bool = False
    regenerate_audio: bool = False
    regenerate_video: bool = False


class BatchOperationResponse(BaseModel):
    """批量操作响应"""
    success: bool
    message: str
    affected_count: int = 0
    task_ids: List[str] = Field(default_factory=list)


class LogEntry(BaseModel):
    """日志条目"""
    timestamp: str
    level: str  # DEBUG, INFO, WARNING, ERROR
    message: str
    module: Optional[str] = None


class LogsResponse(BaseModel):
    """日志响应"""
    logs: List[LogEntry]
    total: int

