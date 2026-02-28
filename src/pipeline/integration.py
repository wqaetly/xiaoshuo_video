"""
Pipeline 集成层

将新的生成器工厂和任务管理系统与现有 PipelineController 集成。
提供向后兼容的包装器和任务追踪功能。
"""
from pathlib import Path
from typing import Optional, Dict, Any, Callable, Awaitable
import asyncio

from ..generators.factory import (
    create_image_generator,
    create_video_generator,
    create_audio_generator,
    normalize_provider,
)
from ..generators.base import (
    ImageGenerator,
    VideoGenerator,
    AudioGenerator,
    ImageGenerateParams,
    VideoGenerateParams,
    AudioGenerateParams,
    GenerateOptions,
    GenerateResult,
)
from ..utils.logger import get_logger
from ..utils.config import get_config

logger = get_logger(__name__)


class GeneratorBridge:
    """生成器桥接层

    提供统一接口，允许 PipelineController 使用新的生成器抽象，
    同时保持与现有代码的兼容性。
    """

    def __init__(self, config: Optional[Any] = None):
        """初始化桥接层

        Args:
            config: 配置对象，默认从全局获取
        """
        self.config = config or get_config()
        self._image_gen: Optional[ImageGenerator] = None
        self._video_gen: Optional[VideoGenerator] = None
        self._audio_gen: Optional[AudioGenerator] = None

    @property
    def image_generator(self) -> ImageGenerator:
        """获取图像生成器（懒加载）"""
        if self._image_gen is None:
            self._image_gen = create_image_generator(
                provider="comfyui",
                base_url=self.config.local.comfyui_url,
            )
            logger.info(f"[Bridge] 创建图像生成器: comfyui")
        return self._image_gen

    @property
    def video_generator(self) -> Optional[VideoGenerator]:
        """获取视频生成器（懒加载）"""
        if self._video_gen is None:
            provider = getattr(self.config.video, 'provider', 'api')

            if provider == "local":
                # 本地 Wan 视频生成
                self._video_gen = create_video_generator(
                    provider="wan",
                    comfyui_base_url=self.config.local.comfyui_url,
                )
            elif self.config.api.video_api_key:
                # 远端 API
                api_provider = self.config.api.video_provider
                self._video_gen = create_video_generator(
                    provider=api_provider,
                    api_key=self.config.api.video_api_key,
                )
            else:
                logger.warning("[Bridge] 视频生成器未配置 API Key")
                return None

            logger.info(f"[Bridge] 创建视频生成器: {provider}")
        return self._video_gen

    @property
    def audio_generator(self) -> AudioGenerator:
        """获取语音生成器（懒加载）"""
        if self._audio_gen is None:
            self._audio_gen = create_audio_generator(
                provider="cosyvoice",
                base_url=self.config.local.cosyvoice_url,
            )
            logger.info(f"[Bridge] 创建语音生成器: cosyvoice")
        return self._audio_gen

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        aspect_ratio: str = "16:9",
        style: Optional[str] = None,
        **kwargs: Any
    ) -> GenerateResult:
        """生成图像

        Args:
            prompt: 正向提示词
            negative_prompt: 负向提示词
            aspect_ratio: 宽高比
            style: 风格预设
            **kwargs: 额外参数

        Returns:
            GenerateResult 结果对象
        """
        params = ImageGenerateParams(
            prompt=prompt,
            negative_prompt=negative_prompt,
            options=GenerateOptions(
                aspect_ratio=aspect_ratio,
                style=style,
                extra=kwargs,
            )
        )
        return await self.image_generator.generate(params)

    async def generate_video(
        self,
        image_url: str,
        motion_prompt: Optional[str] = None,
        duration: float = 5.0,
        **kwargs: Any
    ) -> GenerateResult:
        """生成视频

        Args:
            image_url: 起始图片路径或URL
            motion_prompt: 运动提示词
            duration: 时长（秒）
            **kwargs: 额外参数

        Returns:
            GenerateResult 结果对象
        """
        if self.video_generator is None:
            return GenerateResult(
                success=False,
                error="视频生成器未配置",
                error_code="VIDEO_GENERATOR_NOT_CONFIGURED"
            )

        params = VideoGenerateParams(
            image_url=image_url,
            prompt=motion_prompt,
            options=GenerateOptions(
                duration=duration,
                extra=kwargs,
            )
        )
        return await self.video_generator.generate(params)

    async def generate_audio(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: float = 1.0,
        **kwargs: Any
    ) -> GenerateResult:
        """生成语音

        Args:
            text: 待合成文本
            voice: 音色
            rate: 语速倍率
            **kwargs: 额外参数

        Returns:
            GenerateResult 结果对象
        """
        params = AudioGenerateParams(
            text=text,
            voice=voice,
            rate=rate,
            speaker=kwargs.pop("speaker", None),
            emotion=kwargs.pop("emotion", None),
            options=GenerateOptions(extra=kwargs) if kwargs else None,
        )
        return await self.audio_generator.generate(params)

    def check_health(self) -> Dict[str, bool]:
        """检查所有生成器的健康状态"""
        return {
            "image": self.image_generator.check_health() if self._image_gen else False,
            "video": self.video_generator.check_health() if self._video_gen else False,
            "audio": self.audio_generator.check_health() if self._audio_gen else False,
        }



class TaskTrackedPipeline:
    """任务追踪包装器

    将 Pipeline 操作包装为可追踪的任务，集成 TaskManager。
    支持批量任务创建和进度追踪。
    """

    def __init__(
        self,
        bridge: Optional[GeneratorBridge] = None,
        project_id: Optional[str] = None,
        on_task_progress: Optional[Callable[[str, str, float, str], Awaitable[None]]] = None,
        on_task_complete: Optional[Callable[[str, str, Dict[str, Any]], Awaitable[None]]] = None,
        on_task_error: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
    ):
        """初始化

        Args:
            bridge: 生成器桥接层实例
            project_id: 项目ID，用于任务关联
            on_task_progress: 进度回调 (task_id, scene_id, progress, message)
            on_task_complete: 完成回调 (task_id, scene_id, output)
            on_task_error: 错误回调 (task_id, scene_id, error)
        """
        self.bridge = bridge or GeneratorBridge()
        self.project_id = project_id
        self._task_manager = None

        # 回调函数
        self.on_task_progress = on_task_progress
        self.on_task_complete = on_task_complete
        self.on_task_error = on_task_error

        # 批量任务追踪
        self._batch_tasks: Dict[str, List[str]] = {}  # batch_id -> [task_ids]

    @property
    def task_manager(self):
        """获取任务管理器（延迟导入）"""
        if self._task_manager is None:
            from api.services.task_queue.manager import get_task_manager
            self._task_manager = get_task_manager()
        return self._task_manager

    async def _notify_progress(self, task_id: str, scene_id: str, progress: float, message: str) -> None:
        """通知进度更新"""
        if self.on_task_progress:
            try:
                await self.on_task_progress(task_id, scene_id, progress, message)
            except Exception as e:
                logger.warning(f"进度回调失败: {e}")

    async def _notify_complete(self, task_id: str, scene_id: str, output: Dict[str, Any]) -> None:
        """通知任务完成"""
        if self.on_task_complete:
            try:
                await self.on_task_complete(task_id, scene_id, output)
            except Exception as e:
                logger.warning(f"完成回调失败: {e}")

    async def _notify_error(self, task_id: str, scene_id: str, error: str) -> None:
        """通知任务错误"""
        if self.on_task_error:
            try:
                await self.on_task_error(task_id, scene_id, error)
            except Exception as e:
                logger.warning(f"错误回调失败: {e}")

    async def generate_image_with_task(
        self,
        scene_id: str,
        prompt: str,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """创建图像生成任务并执行

        Args:
            scene_id: 场景ID
            prompt: 提示词
            **kwargs: 其他参数

        Returns:
            包含任务ID和结果的字典
        """
        from api.services.task_queue.models import TaskPriority

        task = await self.task_manager.create_task(
            name=f"生成图像: {scene_id}",
            task_type="image_generate",
            params={"scene_id": scene_id, "prompt": prompt, **kwargs},
            priority=TaskPriority.NORMAL,
            project_id=self.project_id,
            scene_id=scene_id,
            auto_enqueue=False,
        )

        await self._notify_progress(task.id, scene_id, 0.0, "开始生成图像...")

        try:
            await self._notify_progress(task.id, scene_id, 0.3, "调用生成器...")
            result = await self.bridge.generate_image(prompt, **kwargs)

            if result.success:
                output = {
                    "image_url": result.image_url,
                    "local_path": result.local_path,
                }
                task.complete(output=output)
                await self._notify_complete(task.id, scene_id, output)
            else:
                error_msg = result.error or "未知错误"
                task.fail(error_msg)
                await self._notify_error(task.id, scene_id, error_msg)

            return {"task_id": task.id, "result": result}
        except Exception as e:
            task.fail(str(e))
            await self._notify_error(task.id, scene_id, str(e))
            raise

    async def generate_video_with_task(
        self,
        scene_id: str,
        image_url: str,
        motion_prompt: Optional[str] = None,
        duration: float = 5.0,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """创建视频生成任务并执行"""
        from api.services.task_queue.models import TaskPriority

        task = await self.task_manager.create_task(
            name=f"生成视频: {scene_id}",
            task_type="video_generate",
            params={
                "scene_id": scene_id,
                "image_url": image_url,
                "motion_prompt": motion_prompt,
                "duration": duration,
            },
            priority=TaskPriority.NORMAL,
            project_id=self.project_id,
            scene_id=scene_id,
            auto_enqueue=False,
        )

        await self._notify_progress(task.id, scene_id, 0.0, "开始生成视频...")

        try:
            await self._notify_progress(task.id, scene_id, 0.2, "调用视频API...")
            result = await self.bridge.generate_video(
                image_url, motion_prompt, duration, **kwargs
            )

            if result.success:
                output = {
                    "video_url": result.video_url,
                    "local_path": result.local_path,
                    "task_id": result.task_id,
                }
                task.complete(output=output)
                await self._notify_complete(task.id, scene_id, output)
            else:
                error_msg = result.error or "未知错误"
                task.fail(error_msg)
                await self._notify_error(task.id, scene_id, error_msg)

            return {"task_id": task.id, "result": result}
        except Exception as e:
            task.fail(str(e))
            await self._notify_error(task.id, scene_id, str(e))
            raise

    async def generate_audio_with_task(
        self,
        scene_id: str,
        text: str,
        voice: Optional[str] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """创建语音生成任务并执行"""
        from api.services.task_queue.models import TaskPriority

        task = await self.task_manager.create_task(
            name=f"生成语音: {scene_id}",
            task_type="audio_generate",
            params={"scene_id": scene_id, "text": text, "voice": voice},
            priority=TaskPriority.NORMAL,
            project_id=self.project_id,
            scene_id=scene_id,
            auto_enqueue=False,
        )

        await self._notify_progress(task.id, scene_id, 0.0, "开始生成语音...")

        try:
            await self._notify_progress(task.id, scene_id, 0.3, "调用TTS服务...")
            result = await self.bridge.generate_audio(text, voice, **kwargs)

            if result.success:
                output = {
                    "audio_url": result.audio_url,
                    "local_path": result.local_path,
                }
                task.complete(output=output)
                await self._notify_complete(task.id, scene_id, output)
            else:
                error_msg = result.error or "未知错误"
                task.fail(error_msg)
                await self._notify_error(task.id, scene_id, error_msg)

            return {"task_id": task.id, "result": result}
        except Exception as e:
            task.fail(str(e))
            await self._notify_error(task.id, scene_id, str(e))
            raise


def create_pipeline_integration(
    project_id: Optional[str] = None,
    config: Optional[Any] = None,
) -> TaskTrackedPipeline:
    """创建 Pipeline 集成实例

    Args:
        project_id: 项目ID
        config: 配置对象

    Returns:
        TaskTrackedPipeline 实例
    """
    bridge = GeneratorBridge(config=config)
    return TaskTrackedPipeline(bridge=bridge, project_id=project_id)

