"""
任务数据模型
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"         # 等待执行
    QUEUED = "queued"          # 已入队
    RUNNING = "running"        # 执行中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 失败
    CANCELLED = "cancelled"    # 已取消
    RETRYING = "retrying"      # 重试中


class TaskPriority(int, Enum):
    """任务优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


class TaskType(str, Enum):
    """任务类型"""
    IMAGE_GENERATE = "image_generate"
    VIDEO_GENERATE = "video_generate"
    AUDIO_GENERATE = "audio_generate"
    STORYBOARD = "storyboard"
    VIDEO_COMPOSE = "video_compose"
    FULL_PIPELINE = "full_pipeline"


# 状态转换规则
ALLOWED_TRANSITIONS: Dict[TaskStatus, List[TaskStatus]] = {
    TaskStatus.PENDING: [TaskStatus.QUEUED, TaskStatus.CANCELLED],
    TaskStatus.QUEUED: [TaskStatus.RUNNING, TaskStatus.CANCELLED],
    TaskStatus.RUNNING: [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED],
    TaskStatus.FAILED: [TaskStatus.RETRYING, TaskStatus.CANCELLED],
    TaskStatus.RETRYING: [TaskStatus.QUEUED, TaskStatus.CANCELLED],
    TaskStatus.COMPLETED: [],  # 终态
    TaskStatus.CANCELLED: [],  # 终态
}


@dataclass
class TaskResult:
    """任务结果"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_code: Optional[str] = None


@dataclass
class Task:
    """任务实体"""
    id: str
    name: str
    task_type: str
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    progress: float = 0.0
    message: str = ""
    
    # 关联信息
    project_id: Optional[str] = None
    scene_id: Optional[str] = None
    
    # 时间戳
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # 重试配置
    max_retries: int = 3
    retry_count: int = 0
    retry_delay: float = 1.0  # 初始重试延迟（秒）
    
    # 输入输出
    params: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        name: str,
        task_type: str,
        params: Optional[Dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        project_id: Optional[str] = None,
        scene_id: Optional[str] = None,
        max_retries: int = 3,
    ) -> "Task":
        """创建新任务"""
        return cls(
            id=f"task_{uuid.uuid4().hex[:12]}",
            name=name,
            task_type=task_type,
            params=params or {},
            priority=priority,
            project_id=project_id,
            scene_id=scene_id,
            max_retries=max_retries,
        )
    
    def can_transition_to(self, new_status: TaskStatus) -> bool:
        """检查是否可以转换到目标状态"""
        return new_status in ALLOWED_TRANSITIONS.get(self.status, [])
    
    def transition_to(self, new_status: TaskStatus) -> bool:
        """执行状态转换"""
        if not self.can_transition_to(new_status):
            return False
        
        self.status = new_status
        self.updated_at = datetime.now().isoformat()
        
        if new_status == TaskStatus.RUNNING:
            self.started_at = datetime.now().isoformat()
        elif new_status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            self.completed_at = datetime.now().isoformat()
        
        return True
    
    def can_retry(self) -> bool:
        """检查是否可以重试"""
        return self.status == TaskStatus.FAILED and self.retry_count < self.max_retries

    def complete(self, output: Optional[Dict[str, Any]] = None) -> bool:
        """将任务标记为完成

        Args:
            output: 任务输出结果

        Returns:
            是否成功转换状态
        """
        success = self.transition_to(TaskStatus.COMPLETED)
        if success:
            self.result = output
            self.progress = 1.0
            self.message = "任务完成"
        return success

    def fail(self, error_msg: str, error_code: Optional[str] = None) -> bool:
        """将任务标记为失败

        Args:
            error_msg: 错误消息
            error_code: 错误代码

        Returns:
            是否成功转换状态
        """
        success = self.transition_to(TaskStatus.FAILED)
        if success:
            self.error = error_msg
            self.message = f"任务失败: {error_msg}"
            if error_code:
                self.metadata["error_code"] = error_code
        return success

    def update_progress(self, progress: float, message: Optional[str] = None) -> None:
        """更新任务进度

        Args:
            progress: 进度值 (0.0 ~ 1.0)
            message: 进度消息
        """
        self.progress = max(0.0, min(1.0, progress))
        if message:
            self.message = message
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["status"] = self.status.value
        data["priority"] = self.priority.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """从字典创建"""
        data["status"] = TaskStatus(data["status"])
        data["priority"] = TaskPriority(data["priority"])
        return cls(**data)

