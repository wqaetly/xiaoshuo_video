"""
任务持久化存储

将任务持久化到 JSON 文件，支持断点续传和服务重启恢复。
"""
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from filelock import FileLock

from .models import Task, TaskStatus
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TaskStore:
    """任务持久化存储
    
    使用 JSON 文件存储任务数据，支持:
    - 单任务读写
    - 批量操作
    - 文件锁防止并发冲突
    - 自动备份
    """
    
    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        auto_save: bool = True,
    ):
        """初始化存储
        
        Args:
            storage_dir: 存储目录，默认 data/tasks
            auto_save: 是否自动保存
        """
        self.storage_dir = storage_dir or Path("data/tasks")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.tasks_file = self.storage_dir / "tasks.json"
        self.lock_file = self.storage_dir / "tasks.lock"
        self.auto_save = auto_save
        
        # 内存缓存
        self._cache: Dict[str, Task] = {}
        self._dirty = False
        
        # 加载现有任务
        self._load()
    
    def _load(self) -> None:
        """从文件加载任务"""
        if not self.tasks_file.exists():
            logger.info("任务存储文件不存在，创建新存储")
            self._cache = {}
            return
        
        try:
            with FileLock(str(self.lock_file)):
                with open(self.tasks_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                self._cache = {
                    task_id: Task.from_dict(task_data)
                    for task_id, task_data in data.get("tasks", {}).items()
                }
                logger.info(f"已加载 {len(self._cache)} 个任务")
        except json.JSONDecodeError as e:
            logger.error(f"任务文件损坏: {e}")
            self._backup_corrupted()
            self._cache = {}
        except Exception as e:
            logger.error(f"加载任务失败: {e}")
            self._cache = {}
    
    def _save(self) -> None:
        """保存任务到文件"""
        try:
            with FileLock(str(self.lock_file)):
                data = {
                    "version": "1.0",
                    "updated_at": datetime.now().isoformat(),
                    "tasks": {
                        task_id: task.to_dict()
                        for task_id, task in self._cache.items()
                    }
                }
                
                # 写入临时文件再重命名，保证原子性
                temp_file = self.tasks_file.with_suffix(".tmp")
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                temp_file.replace(self.tasks_file)
                
                self._dirty = False
        except Exception as e:
            logger.error(f"保存任务失败: {e}")
    
    def _backup_corrupted(self) -> None:
        """备份损坏的文件"""
        if self.tasks_file.exists():
            backup = self.tasks_file.with_suffix(
                f".corrupted.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            self.tasks_file.rename(backup)
            logger.warning(f"已备份损坏文件: {backup}")
    
    def add(self, task: Task) -> Task:
        """添加任务"""
        self._cache[task.id] = task
        self._dirty = True
        if self.auto_save:
            self._save()
        return task
    
    def get(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self._cache.get(task_id)
    
    def update(self, task: Task) -> Task:
        """更新任务"""
        task.updated_at = datetime.now().isoformat()
        self._cache[task.id] = task
        self._dirty = True
        if self.auto_save:
            self._save()
        return task
    
    def delete(self, task_id: str) -> bool:
        """删除任务"""
        if task_id in self._cache:
            del self._cache[task_id]
            self._dirty = True
            if self.auto_save:
                self._save()
            return True
        return False
    
    def list_by_status(self, status: TaskStatus) -> List[Task]:
        """按状态列出任务"""
        return [t for t in self._cache.values() if t.status == status]
    
    def list_pending(self) -> List[Task]:
        """获取待处理任务（按优先级排序）"""
        pending = [
            t for t in self._cache.values()
            if t.status in [TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.RETRYING]
        ]
        return sorted(pending, key=lambda t: (-t.priority.value, t.created_at))
    
    def list_all(self) -> List[Task]:
        """获取所有任务"""
        return list(self._cache.values())
    
    def count(self) -> Dict[str, int]:
        """统计任务数量"""
        counts = {status.value: 0 for status in TaskStatus}
        for task in self._cache.values():
            counts[task.status.value] += 1
        counts["total"] = len(self._cache)
        return counts
    
    def flush(self) -> None:
        """强制保存"""
        if self._dirty:
            self._save()

