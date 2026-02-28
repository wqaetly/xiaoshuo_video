"""
阶段处理器基类

提供阶段处理的通用接口和上下文管理。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from ..state import PipelineState, Phase
from ...utils.config import Config
from ...utils.logger import get_logger
from ...utils.file_utils import load_json, save_json

if TYPE_CHECKING:
    from ..controller import PipelineController

logger = get_logger(__name__)


@dataclass
class PhaseContext:
    """阶段执行上下文
    
    封装阶段执行所需的共享资源和状态。
    """
    project_path: Path
    config: Config
    state: PipelineState
    
    # 回调函数
    on_progress: Optional[Callable[[str, str, float], None]] = None
    on_error: Optional[Callable[[str, str], None]] = None
    
    # 控制选项
    skip_failed_scenes: bool = True
    failure_threshold: float = 0.5
    
    # 中断检查函数
    check_stop: Optional[Callable[[], bool]] = None
    
    # 额外数据
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def report_progress(self, phase: str, message: str, progress: float) -> None:
        """报告进度"""
        if self.on_progress:
            self.on_progress(phase, message, progress)
    
    def report_error(self, phase: str, error: str) -> None:
        """报告错误"""
        if self.on_error:
            self.on_error(phase, error)
        logger.error(f"[{phase}] {error}")
    
    def should_stop(self) -> bool:
        """检查是否应该停止"""
        if self.check_stop:
            return self.check_stop()
        return False
    
    def load_storyboard(self) -> Dict[str, Any]:
        """加载分镜数据"""
        return load_json(self.project_path / "storyboard.json")
    
    def load_characters(self) -> Dict[str, Any]:
        """加载角色数据"""
        return load_json(self.project_path / "characters.json")
    
    def save_storyboard(self, data: Dict[str, Any]) -> None:
        """保存分镜数据"""
        save_json(self.project_path / "storyboard.json", data)


class BasePhaseHandler(ABC):
    """阶段处理器基类
    
    每个阶段处理器负责执行特定阶段的逻辑。
    """
    
    # 子类必须定义的阶段标识
    phase: Phase = None
    phase_name: str = "未知阶段"
    
    def __init__(self, controller: "PipelineController"):
        """初始化处理器
        
        Args:
            controller: Pipeline 控制器实例，用于访问模块和配置
        """
        self.controller = controller
    
    @property
    def context(self) -> PhaseContext:
        """获取执行上下文"""
        return PhaseContext(
            project_path=self.controller.project_path,
            config=self.controller.config,
            state=self.controller.state,
            on_progress=self.controller.on_progress,
            on_error=self.controller.on_error,
            skip_failed_scenes=self.controller.skip_failed_scenes,
            failure_threshold=self.controller.failure_threshold,
            check_stop=lambda: self.controller._stop_requested,
        )
    
    def report_progress(self, message: str, progress: float) -> None:
        """报告阶段进度"""
        self.context.report_progress(self.phase_name, message, progress)
    
    @abstractmethod
    def execute(self) -> None:
        """执行阶段逻辑
        
        子类必须实现此方法。
        """
        pass
    
    def validate(self) -> bool:
        """验证阶段前置条件
        
        Returns:
            True 如果满足前置条件，False 否则
        """
        return True
    
    def cleanup(self) -> None:
        """阶段完成后的清理工作"""
        pass

