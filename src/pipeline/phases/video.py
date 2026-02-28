"""
视频生成阶段处理器

负责调用远端 API 生成视频片段。
"""
from pathlib import Path
from typing import Dict, Any

from .base import BasePhaseHandler
from ..state import Phase
from ...exceptions import StopRequestedException
from ...utils.logger import get_logger

logger = get_logger(__name__)


class VideoPhaseHandler(BasePhaseHandler):
    """视频生成阶段处理器
    
    调用远端 API (即梦/可灵) 生成视频片段。
    """
    
    phase = Phase.GENERATE_VIDEO
    phase_name = "视频生成"
    
    def execute(self) -> None:
        """执行视频生成阶段"""
        ctx = self.context
        
        video_gen = self.controller.get_video_generator()
        if not video_gen:
            logger.warning("视频API未配置，跳过视频生成阶段")
            return
        
        self.report_progress("检查 API 配额...", 0.0)
        
        storyboard = ctx.load_storyboard()
        scenes = storyboard.get("scenes", [])
        total = len(scenes)
        
        # 获取失效场景
        invalidated = set(ctx.state.get_invalidated_scenes("video"))
        if invalidated:
            logger.info(f"检测到 {len(invalidated)} 个失效场景需要重新生成视频")
        
        # 计算待生成的场景数量
        pending_scenes = [
            s for s in scenes
            if not ctx.state.is_scene_completed(s["id"], "video") or s["id"] in invalidated
        ]
        pending_count = len(pending_scenes)
        
        # 配额预检查
        if pending_count > 0:
            is_sufficient, quota_msg = video_gen.check_quota_sufficient(pending_count)
            logger.info(f"视频配额检查: {quota_msg}")
            
            if not is_sufficient:
                ctx.state.add_error("generate_video", None, f"配额不足: {quota_msg}")
                self.controller._save_state()
                raise RuntimeError(f"视频生成配额不足: {quota_msg}，请充值后重试")
        
        self.report_progress("调用API生成视频片段...", 0.0)
        
        # 判断是否启用任务追踪
        use_tracking = self.controller.use_bridge_mode and self.controller.enable_task_tracking
        
        failed_count = 0
        success_count = 0
        skipped_count = 0
        regenerated_count = 0
        
        for i, scene in enumerate(scenes):
            if ctx.should_stop():
                raise StopRequestedException("用户中断")
            
            scene_id = scene["id"]
            is_invalidated = scene_id in invalidated
            
            # 跳过已完成且未失效的场景
            if ctx.state.is_scene_completed(scene_id, "video") and not is_invalidated:
                success_count += 1
                continue
            
            image_path = ctx.project_path / "images" / f"{scene_id}.png"
            if not image_path.exists():
                logger.warning(f"图像不存在，跳过: {scene_id}")
                skipped_count += 1
                continue
            
            action = "重新生成" if is_invalidated else "生成"
            self.report_progress(f"{action}场景 {scene_id} ({i+1}/{total})", i / total)
            
            try:
                motion_prompt = self.controller._build_motion_prompt(scene)
                duration = scene.get("duration", 5.0)
                
                if use_tracking:
                    video_data = self.controller._generate_video_tracked(
                        scene, image_path, motion_prompt, duration, video_gen
                    )
                else:
                    video_data = video_gen.generate(
                        image_path=image_path,
                        motion_prompt=motion_prompt,
                        duration=duration
                    )
                
                video_data.save(ctx.project_path / "videos" / f"{scene_id}.mp4")
                ctx.state.mark_scene_completed(scene_id, "video")
                
                if is_invalidated:
                    ctx.state.clear_invalidation(scene_id, "video")
                    regenerated_count += 1
                
                self.controller._save_state()
                success_count += 1
            except StopRequestedException:
                raise
            except Exception as e:
                failed_count += 1
                self.controller._handle_scene_error(
                    "generate_video", scene_id, e, total, failed_count - 1
                )
                self.controller._save_state()
        
        # 报告结果
        self._report_result(success_count, regenerated_count, failed_count, skipped_count, total)
    
    def _report_result(self, success: int, regenerated: int, failed: int, skipped: int, total: int) -> None:
        """报告生成结果"""
        result_parts = [f"{success}成功"]
        if regenerated > 0:
            result_parts.append(f"{regenerated}重新生成")
        if failed > 0:
            result_parts.append(f"{failed}失败")
        if skipped > 0:
            result_parts.append(f"{skipped}跳过")
        
        self.report_progress(f"完成: {', '.join(result_parts)} (共{total}个)", 1.0)
        if failed > 0:
            logger.warning(f"视频生成阶段: {failed}/{total} 个场景失败")

