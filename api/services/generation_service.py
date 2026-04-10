"""
生成控制服务 - 封装 Pipeline 控制逻辑
"""
import asyncio
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field

from src.pipeline import PipelineController
from src.pipeline.state import Phase, PipelineState
from src.utils.config import get_config, Config
from src.utils.logger import get_logger
from src.utils.file_utils import load_json

logger = get_logger("api.generation_service")

# 阶段定义常量
PHASE_DEFINITIONS = [
    {"id": "init", "name": "初始化", "task_type": None},
    {"id": "analyze", "name": "分析", "task_type": None},
    {"id": "character_design", "name": "角色设计", "task_type": "character"},
    {"id": "generate_images", "name": "图像生成", "task_type": "image"},
    {"id": "generate_audio", "name": "音频生成", "task_type": "audio"},
    {"id": "generate_video", "name": "视频生成", "task_type": "video"},
    {"id": "compose", "name": "合成", "task_type": None},
]


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


@dataclass
class MicroTask:
    """微任务信息 - 用于单独的手动触发任务（如重新生成单张图片）

    区别于 TaskInfo（全局流程任务），MicroTask 用于表示独立的小任务，
    每个微任务有自己独立的进度展示，不会影响全局流程的进度条。
    """
    task_id: str                              # 唯一任务ID
    project_name: str                         # 所属项目
    task_type: str                            # 任务类型: image, audio, character, video
    target_ids: List[str] = field(default_factory=list)  # 目标ID列表（场景ID或角色ID）
    status: str = "pending"                   # pending, running, completed, failed
    progress: float = 0.0                     # 进度 0.0-1.0
    message: str = ""                         # 当前状态消息
    created_at: str = ""                      # 创建时间
    started_at: str = ""                      # 开始时间
    completed_at: str = ""                    # 完成时间
    error: str = ""                           # 错误信息
    thread: Optional[threading.Thread] = None  # 执行线程

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 API 响应）"""
        return {
            "task_id": self.task_id,
            "project_name": self.project_name,
            "task_type": self.task_type,
            "target_ids": self.target_ids,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
        }


class GenerationService:
    """生成控制服务"""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.projects_dir = Path(self.config.paths.projects_dir)
        # 存储运行中的全局任务（每个项目最多一个）
        self.tasks: Dict[str, TaskInfo] = {}
        # 存储微任务（task_id -> MicroTask）
        self.micro_tasks: Dict[str, MicroTask] = {}
        # 微任务计数器（用于生成唯一ID）
        self._micro_task_counter = 0
        # WebSocket 广播回调 (全局进度)
        self.on_progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
        # WebSocket 广播回调 (微任务进度)
        self.on_micro_task_callback: Optional[Callable[[str, MicroTask], None]] = None

    async def check_services(self) -> Dict[str, Dict[str, Any]]:
        """检查本地服务状态（并行检查）"""
        import httpx

        ollama_url = self.config.local.ollama_url
        comfyui_url = self.config.local.comfyui_url
        cosyvoice_url = getattr(self.config.local, "cosyvoice_url", "http://localhost:9880")
        ollama_model = self.config.local.ollama_model or "glm4:9b"

        services = {
            "ollama": {"status": "offline", "model": ""},
            "comfyui": {"status": "offline", "queue_size": 0},
            "cosyvoice": {"status": "offline"},
        }

        logger.debug("开始并行检查本地服务状态...")

        async def check_ollama():
            """检查 Ollama 服务"""
            try:
                async with httpx.AsyncClient(timeout=1.0) as client:
                    response = await client.get(f"{ollama_url}/api/tags")
                    if response.status_code == 200:
                        services["ollama"]["status"] = "online"
                        services["ollama"]["model"] = ollama_model
                        logger.debug(f"服务 Ollama 在线, 模型: {ollama_model}")
                    else:
                        logger.debug(f"服务 Ollama 响应异常 (状态码: {response.status_code})")
            except Exception as e:
                logger.debug(f"服务 Ollama 不可用: {e}")

        async def check_comfyui():
            """检查 ComfyUI 服务"""
            try:
                async with httpx.AsyncClient(timeout=1.0) as client:
                    response = await client.get(f"{comfyui_url}/queue")
                    if response.status_code == 200:
                        services["comfyui"]["status"] = "online"
                        try:
                            queue_data = response.json()
                            running = len(queue_data.get("queue_running", []))
                            pending = len(queue_data.get("queue_pending", []))
                            services["comfyui"]["queue_size"] = running + pending
                        except Exception:
                            pass
                        logger.debug(f"服务 ComfyUI 在线, 队列: {services['comfyui']['queue_size']}")
                    else:
                        logger.debug(f"服务 ComfyUI 响应异常 (状态码: {response.status_code})")
            except Exception as e:
                logger.debug(f"服务 ComfyUI 不可用: {e}")

        async def check_cosyvoice():
            """检查 CosyVoice 服务"""
            try:
                async with httpx.AsyncClient(timeout=1.0) as client:
                    response = await client.get(cosyvoice_url)
                    if response.status_code == 200:
                        services["cosyvoice"]["status"] = "online"
                        logger.debug("服务 CosyVoice 在线")
                    else:
                        logger.debug(f"服务 CosyVoice 响应异常 (状态码: {response.status_code})")
            except Exception as e:
                logger.debug(f"服务 CosyVoice 不可用: {e}")

        # 并行执行所有服务检查
        await asyncio.gather(check_ollama(), check_comfyui(), check_cosyvoice())

        logger.debug(f"服务检查完成: {services}")
        return services

    def _get_phase_index(self, phase_value: str) -> int:
        """获取阶段索引"""
        phase_order = ["init", "analyze", "character_design", "generate_images",
                       "generate_audio", "generate_video", "compose", "done", "error"]
        try:
            return phase_order.index(phase_value)
        except ValueError:
            return 0

    def _parse_progress_message(self, message: str) -> Dict[str, Any]:
        """解析进度消息，提取当前处理项和进度

        消息格式示例：
        - "生成 角色A (3/10)"
        - "生成场景 scene_01_003 (5/20)"
        - "处理音频 (8/15)"
        """
        import re
        result = {
            "current_item": "",
            "current_item_index": 0,
            "current_item_total": 0,
        }

        # 匹配 "(x/y)" 格式
        match = re.search(r'\((\d+)/(\d+)\)', message)
        if match:
            result["current_item_index"] = int(match.group(1))
            result["current_item_total"] = int(match.group(2))

        # 尝试提取当前处理项名称
        # 匹配 "生成 XXX (" 或 "处理 XXX ("
        name_match = re.search(r'(?:生成|处理|合成)\s+(.+?)\s*\(', message)
        if name_match:
            result["current_item"] = name_match.group(1).strip()

        return result

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
            # 新增：当前阶段详细进度
            "phase_progress": 0.0,
            "current_item": "",
            "current_item_index": 0,
            "current_item_total": 0,
            # 场景进度
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

            # 解析消息提取详细进度
            parsed = self._parse_progress_message(task.message)
            response["current_item"] = parsed["current_item"]
            response["current_item_index"] = parsed["current_item_index"]
            response["current_item_total"] = parsed["current_item_total"]

            # 计算当前阶段进度
            if parsed["current_item_total"] > 0:
                response["phase_progress"] = parsed["current_item_index"] / parsed["current_item_total"]
            else:
                response["phase_progress"] = task.progress  # 回退到整体进度

        return response

    def _build_phases_detail(
        self,
        project_name: str,
        state: Optional[PipelineState],
        current_phase: str,
        is_running: bool,
        task: Optional[TaskInfo] = None
    ) -> List[Dict[str, Any]]:
        """构建各阶段详细进度"""
        phases_detail = []
        current_phase_index = self._get_phase_index(current_phase)
        project_path = self.projects_dir / project_name

        # 从运行时任务中解析当前正在处理的项目 ID
        current_item_id = ""
        if task and task.message and is_running:
            parsed = self._parse_progress_message(task.message)
            current_item_id = parsed["current_item"]  # e.g. "场景 scene_01_003"

        # 尝试加载场景和角色数据
        scenes = []
        characters = []
        storyboard_file = project_path / "storyboard.json"
        characters_file = project_path / "characters.json"

        if storyboard_file.exists():
            try:
                storyboard = load_json(storyboard_file)
                scenes = storyboard.get("scenes", [])
            except Exception:
                pass

        if characters_file.exists():
            try:
                char_data = load_json(characters_file)
                characters = char_data.get("characters", [])
            except Exception:
                pass

        # 构建错误信息映射: {(phase_id, scene_id): error_message}
        error_messages: Dict[tuple, str] = {}
        if state:
            for err in state.errors:
                key = (err.get("phase", ""), err.get("scene_id", ""))
                if key[1]:  # 只记录有 scene_id 的错误
                    error_messages[key] = err.get("message", "未知错误")

        for idx, phase_def in enumerate(PHASE_DEFINITIONS):
            phase_id = phase_def["id"]
            phase_name = phase_def["name"]
            task_type = phase_def["task_type"]

            # 确定阶段状态
            if idx < current_phase_index:
                status = "completed"
            elif idx == current_phase_index:
                status = "running" if is_running else "pending"
            else:
                status = "pending"

            phase_info = {
                "phase_id": phase_id,
                "phase_name": phase_name,
                "status": status,
                "progress": 1.0 if status == "completed" else 0.0,
                "total_items": 0,
                "completed_items": 0,
                "failed_items": 0,
                "current_item": "",
                "sub_tasks": [],
            }

            # 构建子任务列表
            if task_type and state:
                completed_ids = set(state.completed_scenes.get(task_type, []))
                failed_ids = set()
                for err in state.errors:
                    if err.get("phase") == phase_id and err.get("scene_id"):
                        failed_ids.add(err["scene_id"])

                if task_type == "character":
                    # 角色设计阶段
                    items = characters
                    id_key = "id"
                    name_key = "name"
                else:
                    # 场景相关阶段（image, audio, video）
                    items = scenes
                    id_key = "id"
                    name_key = "id"

                phase_info["total_items"] = len(items)

                for item in items:
                    item_id = item.get(id_key, "")
                    item_name = item.get(name_key, item_id)

                    if item_id in failed_ids:
                        sub_status = "failed"
                        phase_info["failed_items"] += 1
                    elif item_id in completed_ids:
                        sub_status = "completed"
                        phase_info["completed_items"] += 1
                    elif status == "running" and current_item_id and item_id in current_item_id:
                        # 当前正在处理的子任务
                        sub_status = "running"
                        phase_info["current_item"] = item_id
                    else:
                        sub_status = "pending"

                    # 获取错误信息
                    error_msg = error_messages.get((phase_id, item_id))

                    phase_info["sub_tasks"].append({
                        "id": item_id,
                        "name": item_name,
                        "status": sub_status,
                        "progress": 1.0 if sub_status == "completed" else 0.0,
                        "message": "正在处理..." if sub_status == "running" else "",
                        "error": error_msg,
                    })

                # 计算阶段进度
                if phase_info["total_items"] > 0:
                    phase_info["progress"] = phase_info["completed_items"] / phase_info["total_items"]

            phases_detail.append(phase_info)

        return phases_detail

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
                response["phases_detail"] = self._build_phases_detail(
                    project_name, state, state.current_phase.value, False, task=None
                )
                return response
            response = self._build_progress_response(None, None, is_running=False)
            response["phases_detail"] = []
            return response

        response = self._build_progress_response(state, task, is_running=task.is_running)
        response["phases_detail"] = self._build_phases_detail(
            project_name, state, task.current_phase, task.is_running, task=task
        )
        return response

    def start_generation(
        self,
        project_name: str,
        phase: str = "full",
        resume: bool = True,
        start_from: Optional[str] = None,
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
                    # 使用 controller.state 的英文枚举值，避免中文 phase_name 导致 phase_index 匹配失败
                    if controller.state:
                        task.current_phase = controller.state.current_phase.value
                    else:
                        task.current_phase = phase_name
                    task.message = message
                    task.progress = progress
                    if self.on_progress_callback:
                        self.on_progress_callback(project_name, self.get_progress(project_name))

                controller.on_progress = on_progress

                # 执行生成
                if start_from:
                    # 从指定阶段开始，执行后续所有阶段
                    controller.run_from_phase(Phase(start_from))
                elif phase == "full":
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

    def regenerate_invalidated(
        self,
        project_name: str,
        scene_ids: Optional[List[str]] = None,
        resource_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """重新生成失效的场景资源（使用微任务系统）

        当分镜文本被修改后，相关资源会被标记为失效。
        此方法以微任务形式运行，有独立的进度跟踪。

        Args:
            project_name: 项目名称
            scene_ids: 指定的场景ID列表（可选，用于生成微任务描述）
            resource_types: 指定的资源类型列表（可选，用于生成微任务描述）

        Returns:
            包含处理结果和微任务ID的字典
        """
        # 检查项目是否存在
        project_path = self.projects_dir / project_name
        if not project_path.exists():
            raise ValueError(f"项目不存在: {project_name}")

        # 确定任务类型和目标描述
        if resource_types:
            task_type = resource_types[0] if len(resource_types) == 1 else "mixed"
        else:
            task_type = "regenerate"

        target_ids = scene_ids or []

        # 生成描述信息
        if scene_ids and len(scene_ids) == 1:
            task_desc = f"重新生成 {scene_ids[0]}"
        elif scene_ids:
            task_desc = f"重新生成 {len(scene_ids)} 个场景"
        else:
            task_desc = "增量更新"

        # 创建微任务
        micro_task = self.create_micro_task(
            project_name=project_name,
            task_type=task_type,
            target_ids=target_ids,
            message=f"准备{task_desc}..."
        )

        # 在后台线程运行
        def run_micro_task():
            try:
                self.update_micro_task(
                    micro_task.task_id,
                    status="running",
                    message=f"正在{task_desc}..."
                )

                controller = PipelineController(project_path, self.config)

                # 设置进度回调（通过微任务系统）
                def on_progress(phase_name: str, message: str, progress: float):
                    self.update_micro_task(
                        micro_task.task_id,
                        progress=progress,
                        message=message
                    )

                controller.on_progress = on_progress

                # 执行增量更新
                result = controller.run_invalidated_only()

                # 完成
                success = result.get("success", True)
                self.update_micro_task(
                    micro_task.task_id,
                    status="completed" if success else "failed",
                    progress=1.0,
                    message=result.get("message", f"{task_desc}完成"),
                    error="; ".join(result.get("errors", [])) if not success else None
                )

            except Exception as e:
                logger.error(f"微任务执行失败 [{micro_task.task_id}]: {e}")
                self.update_micro_task(
                    micro_task.task_id,
                    status="failed",
                    message=f"{task_desc}失败",
                    error=str(e)
                )

        micro_task.thread = threading.Thread(target=run_micro_task, daemon=True)
        micro_task.thread.start()

        return {
            "success": True,
            "message": f"已创建{task_desc}任务",
            "task_id": micro_task.task_id,
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

    # ==================== 微任务管理 ====================

    def _generate_micro_task_id(self) -> str:
        """生成微任务唯一ID"""
        from datetime import datetime
        self._micro_task_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"micro_{timestamp}_{self._micro_task_counter}"

    def create_micro_task(
        self,
        project_name: str,
        task_type: str,
        target_ids: List[str],
        message: str = ""
    ) -> MicroTask:
        """创建微任务

        Args:
            project_name: 项目名称
            task_type: 任务类型 (image, audio, character, video)
            target_ids: 目标ID列表
            message: 初始消息

        Returns:
            新创建的 MicroTask 实例
        """
        from datetime import datetime

        task_id = self._generate_micro_task_id()
        micro_task = MicroTask(
            task_id=task_id,
            project_name=project_name,
            task_type=task_type,
            target_ids=target_ids,
            status="pending",
            progress=0.0,
            message=message or f"准备{task_type}任务...",
            created_at=datetime.now().isoformat(),
        )
        self.micro_tasks[task_id] = micro_task
        logger.debug(f"创建微任务: {task_id}, 类型={task_type}, 目标={target_ids}")

        # 触发 WebSocket 通知（创建时也发送）
        if self.on_micro_task_callback:
            self.on_micro_task_callback(project_name, micro_task)

        return micro_task

    def update_micro_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        error: Optional[str] = None
    ) -> Optional[MicroTask]:
        """更新微任务状态并触发 WebSocket 通知

        Args:
            task_id: 任务ID
            status: 新状态
            progress: 新进度
            message: 新消息
            error: 错误信息

        Returns:
            更新后的 MicroTask，如果不存在返回 None
        """
        from datetime import datetime

        micro_task = self.micro_tasks.get(task_id)
        if not micro_task:
            logger.warning(f"微任务不存在: {task_id}")
            return None

        if status is not None:
            micro_task.status = status
            if status == "running" and not micro_task.started_at:
                micro_task.started_at = datetime.now().isoformat()
            elif status in ("completed", "failed"):
                micro_task.completed_at = datetime.now().isoformat()

        if progress is not None:
            micro_task.progress = progress

        if message is not None:
            micro_task.message = message

        if error is not None:
            micro_task.error = error

        # 触发 WebSocket 通知
        if self.on_micro_task_callback:
            self.on_micro_task_callback(micro_task.project_name, micro_task)

        return micro_task

    def get_micro_tasks(self, project_name: str) -> List[Dict[str, Any]]:
        """获取项目的所有微任务

        Args:
            project_name: 项目名称

        Returns:
            微任务列表（字典格式）
        """
        return [
            task.to_dict()
            for task in self.micro_tasks.values()
            if task.project_name == project_name
        ]

    def get_active_micro_tasks(self, project_name: str) -> List[Dict[str, Any]]:
        """获取项目的活跃微任务（pending 或 running）

        Args:
            project_name: 项目名称

        Returns:
            活跃微任务列表
        """
        return [
            task.to_dict()
            for task in self.micro_tasks.values()
            if task.project_name == project_name and task.status in ("pending", "running")
        ]

    def cleanup_micro_tasks(self, project_name: str, max_age_hours: int = 24) -> int:
        """清理过期的已完成微任务

        Args:
            project_name: 项目名称
            max_age_hours: 最大保留时间（小时）

        Returns:
            清理的任务数量
        """
        from datetime import datetime, timedelta

        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        to_remove = []

        for task_id, task in self.micro_tasks.items():
            if task.project_name != project_name:
                continue
            if task.status in ("completed", "failed") and task.completed_at:
                try:
                    completed_time = datetime.fromisoformat(task.completed_at)
                    if completed_time < cutoff:
                        to_remove.append(task_id)
                except ValueError:
                    pass

        for task_id in to_remove:
            del self.micro_tasks[task_id]

        if to_remove:
            logger.debug(f"清理了 {len(to_remove)} 个过期微任务")

        return len(to_remove)


# 单例模式
_generation_service: Optional[GenerationService] = None


def get_generation_service() -> GenerationService:
    """获取生成服务实例"""
    global _generation_service
    if _generation_service is None:
        _generation_service = GenerationService()
    return _generation_service

