"""Pipeline状态管理"""
import json
from enum import Enum
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from filelock import FileLock


class Phase(Enum):
    """处理阶段枚举"""
    INIT = "init"
    ANALYZE = "analyze"
    CHARACTER_DESIGN = "character_design"
    GENERATE_IMAGES = "generate_images"
    GENERATE_AUDIO = "generate_audio"
    GENERATE_VIDEO = "generate_video"
    COMPOSE = "compose"
    DONE = "done"
    ERROR = "error"


@dataclass
class PipelineState:
    """Pipeline状态数据"""
    current_phase: Phase = Phase.INIT
    current_scene_index: int = 0
    total_scenes: int = 0
    completed_scenes: Dict[str, List[str]] = field(default_factory=dict)
    # 失效的场景 - 需要重新生成 {task_type: [scene_ids]}
    invalidated_scenes: Dict[str, List[str]] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    base_seed: Optional[int] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def save(self, path: Path, timeout: float = 10.0) -> None:
        """保存状态到文件（带文件锁保护）

        Args:
            path: 状态文件路径
            timeout: 获取锁的超时时间（秒），默认10秒
        """
        data = {
            "phase": self.current_phase.value,
            "scene_index": self.current_scene_index,
            "total_scenes": self.total_scenes,
            "completed_scenes": self.completed_scenes,
            "invalidated_scenes": self.invalidated_scenes,
            "errors": self.errors,
            "base_seed": self.base_seed,
            "created_at": self.created_at,
            "updated_at": datetime.now().isoformat()
        }
        path.parent.mkdir(parents=True, exist_ok=True)

        # 使用文件锁保护写操作
        lock_path = path.with_suffix(".lock")
        lock = FileLock(lock_path, timeout=timeout)
        with lock:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: Path, timeout: float = 10.0) -> "PipelineState":
        """从文件加载状态（带文件锁保护）

        Args:
            path: 状态文件路径
            timeout: 获取锁的超时时间（秒），默认10秒
        """
        lock_path = path.with_suffix(".lock")
        lock = FileLock(lock_path, timeout=timeout)
        with lock:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

        return cls(
            current_phase=Phase(data.get("phase", "init")),
            current_scene_index=data.get("scene_index", 0),
            total_scenes=data.get("total_scenes", 0),
            completed_scenes=data.get("completed_scenes", {}),
            invalidated_scenes=data.get("invalidated_scenes", {}),
            errors=data.get("errors", []),
            base_seed=data.get("base_seed"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat())
        )

    def mark_scene_completed(self, scene_id: str, task_type: str) -> None:
        """标记场景任务完成"""
        if task_type not in self.completed_scenes:
            self.completed_scenes[task_type] = []
        if scene_id not in self.completed_scenes[task_type]:
            self.completed_scenes[task_type].append(scene_id)

    def is_scene_completed(self, scene_id: str, task_type: str) -> bool:
        """检查场景任务是否完成（且未失效）"""
        is_completed = scene_id in self.completed_scenes.get(task_type, [])
        is_invalidated = scene_id in self.invalidated_scenes.get(task_type, [])
        return is_completed and not is_invalidated

    def invalidate_scene(self, scene_id: str, task_types: List[str]) -> None:
        """标记场景资源为失效，需要重新生成

        Args:
            scene_id: 场景ID
            task_types: 需要失效的任务类型列表，如 ["image", "audio", "video"]
        """
        for task_type in task_types:
            if task_type not in self.invalidated_scenes:
                self.invalidated_scenes[task_type] = []
            if scene_id not in self.invalidated_scenes[task_type]:
                self.invalidated_scenes[task_type].append(scene_id)

    def clear_invalidation(self, scene_id: str, task_type: str) -> None:
        """清除场景的失效标记（重新生成后调用）"""
        if task_type in self.invalidated_scenes:
            if scene_id in self.invalidated_scenes[task_type]:
                self.invalidated_scenes[task_type].remove(scene_id)

    def get_invalidated_scenes(self, task_type: str) -> List[str]:
        """获取某类型下所有失效的场景"""
        return self.invalidated_scenes.get(task_type, [])

    def has_invalidated_scenes(self) -> bool:
        """检查是否有需要重新生成的失效场景"""
        return any(len(scenes) > 0 for scenes in self.invalidated_scenes.values())

    def add_error(self, phase: str, scene_id: Optional[str], message: str) -> None:
        """添加错误记录"""
        self.errors.append({
            "phase": phase,
            "scene_id": scene_id,
            "message": message,
            "time": datetime.now().isoformat()
        })

    def get_progress(self) -> Dict[str, Any]:
        """获取进度信息"""
        phase_order = list(Phase)
        current_idx = phase_order.index(self.current_phase)
        total_phases = len(phase_order) - 2  # 排除INIT和ERROR

        return {
            "phase": self.current_phase.value,
            "phase_progress": current_idx / total_phases if total_phases > 0 else 0,
            "scene_progress": self.current_scene_index / self.total_scenes if self.total_scenes > 0 else 0,
            "completed_scenes": sum(len(v) for v in self.completed_scenes.values()),
            "invalidated_count": sum(len(v) for v in self.invalidated_scenes.values()),
            "total_scenes": self.total_scenes,
            "error_count": len(self.errors)
        }
