"""Pipeline状态管理"""
import json
from enum import Enum
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime


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
    errors: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def save(self, path: Path) -> None:
        """保存状态到文件"""
        data = {
            "phase": self.current_phase.value,
            "scene_index": self.current_scene_index,
            "total_scenes": self.total_scenes,
            "completed_scenes": self.completed_scenes,
            "errors": self.errors,
            "created_at": self.created_at,
            "updated_at": datetime.now().isoformat()
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: Path) -> "PipelineState":
        """从文件加载状态"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls(
            current_phase=Phase(data.get("phase", "init")),
            current_scene_index=data.get("scene_index", 0),
            total_scenes=data.get("total_scenes", 0),
            completed_scenes=data.get("completed_scenes", {}),
            errors=data.get("errors", []),
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
        """检查场景任务是否完成"""
        return scene_id in self.completed_scenes.get(task_type, [])

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
            "total_scenes": self.total_scenes,
            "error_count": len(self.errors)
        }
