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
    controller: Optional[PipelineController] = None  # 控制器引用，用于中断任务


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

    def _get_phase_index(self, phase_value: str) -> int:
        """获取阶段索引"""
        phase_order = ["init", "analyze", "character_design", "generate_images",
                       "generate_audio", "generate_video", "compose", "done", "error"]
        try:
            return phase_order.index(phase_value)
        except ValueError:
            return 0

    def _build_progress_response(
        self,
        state: Optional[PipelineState],
        task: Optional[TaskInfo],
        is_running: bool
    ) -> Dict[str, Any]:
        """构建进度响应"""
        # 基础响应
        response = {
            "phase": "init",
            "phase_index": 0,
            "total_phases": 7,
            "task": "",
            "progress": 0.0,
            "message": "",
            "is_running": is_running,
            "current_scene_index": 0,
            "total_scenes": 0,
            "completed_tasks": {
                "character": 0,
                "image": 0,
                "audio": 0,
                "video": 0,
            },
            "failed_scenes": [],
            "error_count": 0,
        }

        # 从 PipelineState 获取详细信息
        if state:
            phase_value = state.current_phase.value
            response["phase"] = phase_value
            response["phase_index"] = self._get_phase_index(phase_value)
            response["current_scene_index"] = state.current_scene_index
            response["total_scenes"] = state.total_scenes

            # 统计各类型完成数
            completed = state.completed_scenes
            response["completed_tasks"] = {
                "character": len(completed.get("character", [])),
                "image": len(completed.get("image", [])),
                "audio": len(completed.get("audio", [])),
                "video": len(completed.get("video", [])),
            }

            # 错误信息
            response["error_count"] = len(state.errors)
            response["failed_scenes"] = [
                {
                    "scene_id": err.get("scene_id", "unknown"),
                    "phase": err.get("phase", "unknown"),
                    "message": err.get("message", "未知错误"),
                    "time": err.get("time", ""),
                }
                for err in state.errors
                if err.get("scene_id")  # 只包含有场景ID的错误
            ]

        # 从运行时任务获取信息
        if task:
            response["phase"] = task.current_phase
            response["phase_index"] = self._get_phase_index(task.current_phase)
            response["task"] = task.phase
            response["progress"] = task.progress
            response["message"] = task.message

        return response

    def get_progress(self, project_name: str) -> Dict[str, Any]:
        """获取项目生成进度"""
        task = self.tasks.get(project_name)
        state = None

        # 尝试加载状态文件
        state_file = self.projects_dir / project_name / "pipeline_state.json"
        if state_file.exists():
            try:
                state = PipelineState.load(state_file)
            except Exception as e:
                logger.warning(f"加载状态文件失败: {e}")

        if task is None:
            if state:
                response = self._build_progress_response(state, None, is_running=False)
                response["message"] = f"已暂停于 {state.current_phase.value} 阶段"
                return response
            return self._build_progress_response(None, None, is_running=False)

        return self._build_progress_response(state, task, is_running=task.is_running)

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
                # 保存控制器引用，以便可以从外部请求停止
                task.controller = controller

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

                # 检查是否是用户主动停止
                if controller.is_stop_requested():
                    task.message = "任务已停止"
                else:
                    task.message = "生成完成"
                    task.progress = 1.0
            except Exception as e:
                logger.error(f"生成任务失败: {e}")
                task.errors.append({"error": str(e)})
                task.message = f"生成失败: {e}"
            finally:
                task.is_running = False
                task.controller = None  # 清理控制器引用

        task.thread = threading.Thread(target=run_task, daemon=True)
        task.thread.start()

        return {
            "success": True,
            "phase": phase,
            "message": f"已启动 {phase} 生成任务",
            "errors": [],
        }

    def stop_generation(self, project_name: str) -> Dict[str, Any]:
        """停止生成任务

        向正在运行的 PipelineController 发送停止请求。
        控制器会在下一个检查点（通常是当前场景完成后）优雅停止。
        """
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

        # 调用控制器的停止请求方法
        if task.controller is not None:
            task.controller.request_stop()
            logger.info(f"已向项目 {project_name} 的控制器发送停止请求")
        else:
            logger.warning(f"项目 {project_name} 的控制器引用不可用，无法发送停止信号")

        return {
            "success": True,
            "phase": task.phase,
            "message": "已请求停止任务，将在当前场景完成后停止",
            "errors": [],
        }

    def is_task_running(self, project_name: str) -> bool:
        """检查任务是否运行中"""
        task = self.tasks.get(project_name)
        return task is not None and task.is_running

    def regenerate_invalidated(self, project_name: str) -> Dict[str, Any]:
        """重新生成失效的场景资源

        当分镜文本被修改后，相关资源会被标记为失效。
        此方法仅重新生成这些失效的资源。

        Returns:
            包含处理结果的字典
        """
        # 检查项目是否存在
        project_path = self.projects_dir / project_name
        if not project_path.exists():
            raise ValueError(f"项目不存在: {project_name}")

        # 检查是否已有运行中任务
        if project_name in self.tasks and self.tasks[project_name].is_running:
            return {
                "success": False,
                "message": "任务已在运行中，请等待完成",
                "regenerated": {},
                "errors": [],
            }

        # 创建任务信息
        task = TaskInfo(project_name=project_name, phase="regenerate", is_running=True)
        self.tasks[project_name] = task

        result_data = {
            "success": True,
            "message": "",
            "regenerated": {},
            "errors": [],
        }

        # 在后台线程运行
        def run_task():
            nonlocal result_data
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

                # 执行增量更新
                result = controller.run_invalidated_only()
                result_data.update(result)

                task.message = result.get("message", "增量更新完成")
                task.progress = 1.0
            except Exception as e:
                logger.error(f"增量更新任务失败: {e}")
                task.errors.append({"error": str(e)})
                task.message = f"增量更新失败: {e}"
                result_data["success"] = False
                result_data["errors"].append(str(e))
            finally:
                task.is_running = False

        task.thread = threading.Thread(target=run_task, daemon=True)
        task.thread.start()

        return {
            "success": True,
            "message": "已启动增量更新任务",
            "regenerated": {},
            "errors": [],
        }

    def get_invalidation_status(self, project_name: str) -> Dict[str, Any]:
        """获取项目的失效状态

        Returns:
            包含失效场景信息的字典
        """
        project_path = self.projects_dir / project_name
        state_file = project_path / "pipeline_state.json"

        if not state_file.exists():
            return {
                "has_invalidated": False,
                "invalidated_counts": {"image": 0, "audio": 0, "video": 0},
                "invalidated_scenes": {},
            }

        try:
            state = PipelineState.load(state_file)
            return {
                "has_invalidated": state.has_invalidated_scenes(),
                "invalidated_counts": {
                    "image": len(state.get_invalidated_scenes("image")),
                    "audio": len(state.get_invalidated_scenes("audio")),
                    "video": len(state.get_invalidated_scenes("video")),
                },
                "invalidated_scenes": {
                    "image": state.get_invalidated_scenes("image"),
                    "audio": state.get_invalidated_scenes("audio"),
                    "video": state.get_invalidated_scenes("video"),
                },
            }
        except Exception as e:
            logger.warning(f"加载状态文件失败: {e}")
            return {
                "has_invalidated": False,
                "invalidated_counts": {"image": 0, "audio": 0, "video": 0},
                "invalidated_scenes": {},
            }


# 单例模式
_generation_service: Optional[GenerationService] = None


def get_generation_service() -> GenerationService:
    """获取生成服务实例"""
    global _generation_service
    if _generation_service is None:
        _generation_service = GenerationService()
    return _generation_service

