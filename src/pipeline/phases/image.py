"""
图像生成阶段处理器

负责场景图像的生成，支持串行和并行两种模式。
"""
from typing import Dict, Any, List

from .base import BasePhaseHandler
from ..state import Phase
from ..scheduler import run_parallel_sync
from ...exceptions import StopRequestedException
from ...utils.logger import get_logger
from ...utils.file_utils import load_json
from ...utils.gpu_monitor import get_gpu_monitor

logger = get_logger(__name__)


class ImagePhaseHandler(BasePhaseHandler):
    """图像生成阶段处理器
    
    支持两种模式：
    1. 串行模式：逐个生成场景图像
    2. 并行模式：并发生成多个场景图像
    """
    
    phase = Phase.GENERATE_IMAGES
    phase_name = "图像生成"
    
    def __init__(self, controller, parallel: bool = False):
        """初始化处理器
        
        Args:
            controller: Pipeline 控制器实例
            parallel: 是否使用并行模式
        """
        super().__init__(controller)
        self.parallel = parallel
    
    def execute(self) -> None:
        """执行图像生成阶段"""
        if self.parallel:
            self._execute_parallel()
        else:
            self._execute_serial()
    
    def _execute_serial(self) -> None:
        """串行执行图像生成"""
        ctx = self.context
        
        self.report_progress("生成场景图像...", 0.0)
        
        storyboard = ctx.load_storyboard()
        characters = ctx.load_characters()
        scenes = storyboard.get("scenes", [])
        total = len(scenes)
        
        failed_count = 0
        success_count = 0
        regenerated_count = 0
        
        # 加载角色参考图
        self._load_character_references(characters)
        
        # 确保基础种子
        from ...image.scene_generator import derive_scene_seed
        base_seed = self.controller._ensure_base_seed()
        
        # 获取失效场景
        invalidated = set(ctx.state.get_invalidated_scenes("image"))
        if invalidated:
            logger.info(f"检测到 {len(invalidated)} 个失效场景需要重新生成图像")
        
        # 判断是否启用任务追踪
        use_tracking = self.controller.use_bridge_mode and self.controller.enable_task_tracking
        
        for i, scene in enumerate(scenes):
            if ctx.should_stop():
                raise StopRequestedException("用户中断")
            
            scene_id = scene["id"]
            is_invalidated = scene_id in invalidated
            
            # 跳过已完成且未失效的场景
            if ctx.state.is_scene_completed(scene_id, "image") and not is_invalidated:
                success_count += 1
                continue
            
            action = "重新生成" if is_invalidated else "生成"
            self.report_progress(f"{action}场景 {scene_id} ({i+1}/{total})", i / total)
            
            try:
                scene_seed = derive_scene_seed(base_seed, scene_id)
                if use_tracking:
                    image = self.controller._generate_image_tracked(scene, characters, seed=scene_seed)
                else:
                    image = self.controller._image_gen.generate_scene(
                        scene,
                        characters,
                        style_preset=self.controller.config.video.style,
                        seed=scene_seed
                    )
                
                image.save(ctx.project_path / "images" / f"{scene_id}.png")
                ctx.state.mark_scene_completed(scene_id, "image")
                
                if is_invalidated:
                    ctx.state.clear_invalidation(scene_id, "image")
                    regenerated_count += 1
                
                ctx.state.current_scene_index = i + 1
                self.controller._save_state()
                success_count += 1
            except StopRequestedException:
                raise
            except Exception as e:
                failed_count += 1
                self.controller._handle_scene_error(
                    "generate_images", scene_id, e, total, failed_count - 1
                )
                self.controller._save_state()
        
        # 报告结果
        self._report_result(success_count, regenerated_count, failed_count, total)
    
    def _load_character_references(self, characters: Dict[str, Any]) -> None:
        """加载角色参考图"""
        self.controller._load_character_references(characters)
    
    def _report_result(self, success: int, regenerated: int, failed: int, total: int) -> None:
        """报告生成结果"""
        result_parts = [f"{success}成功"]
        if regenerated > 0:
            result_parts.append(f"{regenerated}重新生成")
        if failed > 0:
            result_parts.append(f"{failed}失败")

        self.report_progress(f"完成: {', '.join(result_parts)} (共{total}个)", 1.0)
        if failed > 0:
            logger.warning(f"图像生成阶段: {failed}/{total} 个场景失败")

    def _execute_parallel(self) -> None:
        """并行执行图像生成"""
        ctx = self.context

        if ctx.should_stop():
            raise StopRequestedException("用户中断")

        self.report_progress("生成场景图像 (并行)...", 0.0)

        storyboard = ctx.load_storyboard()
        characters = ctx.load_characters()
        scenes = storyboard.get("scenes", [])

        # 加载角色参考图
        self._load_character_references(characters)

        # 确保基础种子
        from ...image.scene_generator import derive_scene_seed
        base_seed = self.controller._ensure_base_seed()

        pending_scenes = [
            s for s in scenes
            if not ctx.state.is_scene_completed(s["id"], "image")
        ]

        if not pending_scenes:
            self.report_progress("所有场景图像已生成", 1.0)
            return

        total = len(pending_scenes)
        logger.info(f"并行生成 {total} 个场景图像")

        def generate_single_image(scene: Dict[str, Any]) -> Dict[str, Any]:
            """生成单个场景图像"""
            scene_id = scene["id"]
            try:
                image = self.controller._image_gen.generate_scene(
                    scene,
                    characters,
                    style_preset=self.controller.config.video.style,
                    seed=derive_scene_seed(base_seed, scene_id)
                )
                image.save(ctx.project_path / "images" / f"{scene_id}.png")
                return {"scene_id": scene_id, "success": True, "error": None}
            except Exception as e:
                logger.error(f"场景 {scene_id} 图像生成失败: {e}")
                return {"scene_id": scene_id, "success": False, "error": str(e)}

        tasks = [
            {"task_id": s["id"], "func": generate_single_image, "args": (s,)}
            for s in pending_scenes
        ]

        def on_progress(task_id: str, progress: float):
            self.report_progress(f"进度 {progress*100:.0f}%", progress)

        # 动态计算并发数
        gpu_monitor = get_gpu_monitor()
        dynamic_workers = gpu_monitor.calculate_optimal_workers(
            min_workers=1,
            max_workers=self.controller.config.generation.max_concurrent_tasks,
            memory_per_task_mb=2500.0,
            safety_margin=0.2
        )
        logger.info(f"图像生成并发数: {dynamic_workers}")

        results = run_parallel_sync(tasks, max_workers=dynamic_workers, on_progress=on_progress)

        for r in results:
            result_data = r.get("result", {})
            if result_data and result_data.get("success"):
                ctx.state.mark_scene_completed(result_data["scene_id"], "image")
            elif result_data:
                ctx.state.add_error("generate_images", result_data["scene_id"], result_data.get("error", "未知错误"))

        self.controller._save_state()
        self.report_progress("场景图像生成完成", 1.0)

