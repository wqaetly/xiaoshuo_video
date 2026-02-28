"""
音频生成阶段处理器

负责场景配音的生成，支持串行和并行两种模式。
"""
from typing import Dict, Any

from .base import BasePhaseHandler
from ..state import Phase
from ..scheduler import run_parallel_sync
from ...exceptions import StopRequestedException
from ...utils.logger import get_logger
from ...utils.gpu_monitor import get_gpu_monitor

logger = get_logger(__name__)


class AudioPhaseHandler(BasePhaseHandler):
    """音频生成阶段处理器
    
    支持两种模式：
    1. 串行模式：逐个生成场景配音
    2. 并行模式：并发生成多个场景配音
    """
    
    phase = Phase.GENERATE_AUDIO
    phase_name = "音频生成"
    
    def __init__(self, controller, parallel: bool = False):
        """初始化处理器
        
        Args:
            controller: Pipeline 控制器实例
            parallel: 是否使用并行模式
        """
        super().__init__(controller)
        self.parallel = parallel
    
    def execute(self) -> None:
        """执行音频生成阶段"""
        if self.parallel:
            self._execute_parallel()
        else:
            self._execute_serial()
    
    def _execute_serial(self) -> None:
        """串行执行音频生成"""
        ctx = self.context
        
        self.report_progress("生成配音...", 0.0)
        
        storyboard = ctx.load_storyboard()
        characters = ctx.load_characters()
        scenes = storyboard.get("scenes", [])
        total = len(scenes)
        
        failed_count = 0
        success_count = 0
        regenerated_count = 0
        
        # 获取失效场景
        invalidated = set(ctx.state.get_invalidated_scenes("audio"))
        if invalidated:
            logger.info(f"检测到 {len(invalidated)} 个失效场景需要重新生成音频")
        
        # 判断是否启用任务追踪
        use_tracking = self.controller.use_bridge_mode and self.controller.enable_task_tracking
        
        for i, scene in enumerate(scenes):
            if ctx.should_stop():
                raise StopRequestedException("用户中断")
            
            scene_id = scene["id"]
            is_invalidated = scene_id in invalidated
            
            # 跳过已完成且未失效的场景
            if ctx.state.is_scene_completed(scene_id, "audio") and not is_invalidated:
                success_count += 1
                continue
            
            action = "重新生成" if is_invalidated else "生成"
            self.report_progress(f"{action}场景 {scene_id} ({i+1}/{total})", i / total)
            
            try:
                if use_tracking:
                    audio_data = self.controller._generate_audio_tracked(scene, characters)
                else:
                    audio_data = self.controller._tts.generate_scene_audio(
                        scene.get("audio", {}),
                        characters
                    )
                
                audio_data.save(ctx.project_path / "audio" / f"{scene_id}.wav")
                ctx.state.mark_scene_completed(scene_id, "audio")
                
                if is_invalidated:
                    ctx.state.clear_invalidation(scene_id, "audio")
                    regenerated_count += 1
                
                self.controller._save_state()
                success_count += 1
            except StopRequestedException:
                raise
            except Exception as e:
                failed_count += 1
                self.controller._handle_scene_error(
                    "generate_audio", scene_id, e, total, failed_count - 1
                )
                self.controller._save_state()
        
        # 报告结果
        self._report_result(success_count, regenerated_count, failed_count, total)
    
    def _report_result(self, success: int, regenerated: int, failed: int, total: int) -> None:
        """报告生成结果"""
        result_parts = [f"{success}成功"]
        if regenerated > 0:
            result_parts.append(f"{regenerated}重新生成")
        if failed > 0:
            result_parts.append(f"{failed}失败")

        self.report_progress(f"完成: {', '.join(result_parts)} (共{total}个)", 1.0)
        if failed > 0:
            logger.warning(f"音频生成阶段: {failed}/{total} 个场景失败")

    def _execute_parallel(self) -> None:
        """并行执行音频生成"""
        ctx = self.context

        if ctx.should_stop():
            raise StopRequestedException("用户中断")

        self.report_progress("生成配音 (并行)...", 0.0)

        storyboard = ctx.load_storyboard()
        characters = ctx.load_characters()
        scenes = storyboard.get("scenes", [])

        pending_scenes = [
            s for s in scenes
            if not ctx.state.is_scene_completed(s["id"], "audio")
        ]

        if not pending_scenes:
            self.report_progress("所有场景音频已生成", 1.0)
            return

        total = len(pending_scenes)
        logger.info(f"并行生成 {total} 个场景音频")

        def generate_single_audio(scene: Dict[str, Any]) -> Dict[str, Any]:
            """生成单个场景音频"""
            scene_id = scene["id"]
            try:
                audio_data = self.controller._tts.generate_scene_audio(
                    scene.get("audio", {}),
                    characters
                )
                audio_data.save(ctx.project_path / "audio" / f"{scene_id}.wav")
                return {"scene_id": scene_id, "success": True, "error": None}
            except Exception as e:
                logger.error(f"场景 {scene_id} 音频生成失败: {e}")
                return {"scene_id": scene_id, "success": False, "error": str(e)}

        tasks = [
            {"task_id": s["id"], "func": generate_single_audio, "args": (s,)}
            for s in pending_scenes
        ]

        def on_progress(task_id: str, progress: float):
            self.report_progress(f"进度 {progress*100:.0f}%", progress)

        # 动态计算并发数
        gpu_monitor = get_gpu_monitor()
        dynamic_workers = gpu_monitor.calculate_optimal_workers(
            min_workers=1,
            max_workers=self.controller.config.generation.max_concurrent_tasks,
            memory_per_task_mb=1000.0,  # TTS 任务显存占用较低
            safety_margin=0.15
        )
        logger.info(f"音频生成并发数: {dynamic_workers}")

        results = run_parallel_sync(tasks, max_workers=dynamic_workers, on_progress=on_progress)

        for r in results:
            result_data = r.get("result", {})
            if result_data and result_data.get("success"):
                ctx.state.mark_scene_completed(result_data["scene_id"], "audio")
            elif result_data:
                ctx.state.add_error("generate_audio", result_data["scene_id"], result_data.get("error", "未知错误"))

        self.controller._save_state()
        self.report_progress("配音生成完成", 1.0)

