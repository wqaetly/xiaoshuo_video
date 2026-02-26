"""
生成控制服务 - 封装 Pipeline 控制逻辑
"""
import asyncio
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field

from loguru import logger

from src.pipeline import PipelineController
from src.pipeline.state import Phase, PipelineState
from src.utils.config import get_config, Config


@dataclass
class TaskInfo:
    """任务信息"""
    project_name: str
    phase: str = "full"
    is_running: bool = False
    progress: float = 0.0
    message: str = ""
    current_phase: str = "init"
    errors: list = field(default_factory=list)
    thread: Optional[threading.Thread] = None
    stop_requested: bool = False


class GenerationService:
    """生成控制服务"""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.projects_dir = Path(self.config.paths.projects_dir)
        # 存储运行中的任务
        self.tasks: Dict[str, TaskInfo] = {}
        # WebSocket 广播回调
        self.on_progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None

    def check_services(self) -> Dict[str, Dict[str, Any]]:
        """检查本地服务状态"""
        import httpx

        services = {
            "ollama": {
                "name": "Ollama",
                "url": self.config.local.ollama_url,
                "status": "offline",
            },
            "comfyui": {
                "name": "ComfyUI",
                "url": self.config.local.comfyui_url,
                "status": "offline",
            },
            "cosyvoice": {
                "name": "CosyVoice",
                "url": getattr(self.config.local, "cosyvoice_url", "http://localhost:9880"),
                "status": "offline",
            },
        }

        for key, info in services.items():
            try:
                response = httpx.get(info["url"], timeout=3.0)
                if response.status_code == 200:
                    services[key]["status"] = "online"
            except Exception:
                services[key]["status"] = "offline"

        return services

    def get_progress(self, project_name: str) -> Dict[str, Any]:
        """获取项目生成进度"""
        task = self.tasks.get(project_name)
        if task is None:
            # 尝试从文件加载状态
            state_file = self.projects_dir / project_name / "pipeline_state.json"
            if state_file.exists():
                state = PipelineState.load(state_file)
                return {
                    "phase": state.current_phase.value,
                    "task": "",
                    "progress": 0.0,
                    "message": f"已暂停于 {state.current_phase.value} 阶段",
                    "is_running": False,
                }
            return {
                "phase": "init",
                "task": "",
                "progress": 0.0,
                "message": "",
                "is_running": False,
            }

        return {
            "phase": task.current_phase,
            "task": task.phase,
            "progress": task.progress,
            "message": task.message,
            "is_running": task.is_running,
        }

    def start_generation(
        self,
        project_name: str,
        phase: str = "full",
        resume: bool = True,
    ) -> Dict[str, Any]:
        """启动生成任务"""
        # 检查项目是否存在
        project_path = self.projects_dir / project_name
        if not project_path.exists():
            raise ValueError(f"项目不存在: {project_name}")

        # 检查是否已有运行中任务
        if project_name in self.tasks and self.tasks[project_name].is_running:
            return {
                "success": False,
                "phase": phase,
                "message": "任务已在运行中",
                "errors": [],
            }

        # 创建任务信息
        task = TaskInfo(project_name=project_name, phase=phase, is_running=True)
        self.tasks[project_name] = task

        # 在后台线程运行
        def run_task():
            try:
                controller = PipelineController(project_path, self.config)
                
                # 设置进度回调
                def on_progress(phase_name: str, message: str, progress: float):
                    task.current_phase = phase_name
                    task.message = message
                    task.progress = progress
                    if self.on_progress_callback:
                        self.on_progress_callback(project_name, self.get_progress(project_name))
                
                controller.on_progress = on_progress
                
                # 执行生成
                if phase == "full":
                    controller.run(resume=resume)
                else:
                    controller.run_phase(Phase(phase))
                
                task.message = "生成完成"
                task.progress = 1.0
            except Exception as e:
                logger.error(f"生成任务失败: {e}")
                task.errors.append({"error": str(e)})
                task.message = f"生成失败: {e}"
            finally:
                task.is_running = False

        task.thread = threading.Thread(target=run_task, daemon=True)
        task.thread.start()

        return {
            "success": True,
            "phase": phase,
            "message": f"已启动 {phase} 生成任务",
            "errors": [],
        }

    def stop_generation(self, project_name: str) -> Dict[str, Any]:
        """停止生成任务"""
        task = self.tasks.get(project_name)
        if task is None or not task.is_running:
            return {
                "success": False,
                "phase": "",
                "message": "没有运行中的任务",
                "errors": [],
            }

        task.stop_requested = True
        task.message = "正在停止..."

        # 注意：目前 PipelineController 不支持中断，需要等待当前步骤完成
        # TODO: 在 PipelineController 中添加中断检查点

        return {
            "success": True,
            "phase": task.phase,
            "message": "已请求停止任务",
            "errors": [],
        }

    def is_task_running(self, project_name: str) -> bool:
        """检查任务是否运行中"""
        task = self.tasks.get(project_name)
        return task is not None and task.is_running


# 单例模式
_generation_service: Optional[GenerationService] = None


def get_generation_service() -> GenerationService:
    """获取生成服务实例"""
    global _generation_service
    if _generation_service is None:
        _generation_service = GenerationService()
    return _generation_service

