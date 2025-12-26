"""Pipeline流程控制器"""
import gc
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
import torch

from .state import PipelineState, Phase
from .scheduler import run_parallel_sync, TaskPriority
from ..utils.config import Config, get_config
from ..utils.logger import get_logger
from ..utils.file_utils import load_json, save_json, load_yaml, ensure_dir

logger = get_logger(__name__)


class PipelineController:
    """主流程控制器 - 编排整个视频生成流程"""

    def __init__(self, project_path: Path, config: Optional[Config] = None):
        self.project_path = Path(project_path)
        self.config = config or get_config()
        self.state_file = self.project_path / "pipeline_state.json"
        self.state: Optional[PipelineState] = None

        # 模块实例 (延迟初始化)
        self._llm = None
        self._storyboard_gen = None
        self._character_extractor = None
        self._image_gen = None
        self._char_designer = None
        self._video_gen = None
        self._tts = None
        self._composer = None

        # 回调函数
        self.on_progress: Optional[Callable[[str, str, float], None]] = None
        self.on_phase_change: Optional[Callable[[Phase], None]] = None
        self.on_error: Optional[Callable[[str, str], None]] = None
        
        # 跳过失败场景选项 (默认开启)
        self.skip_failed_scenes: bool = True
        # 失败阈值 - 失败率超过此值则停止 (0.0-1.0, 默认0.5表示50%)
        self.failure_threshold: float = 0.5

    def init_modules(self) -> None:
        """初始化各个模块"""
        logger.info("初始化模块...")

        # LLM模块
        from ..llm import OllamaClient, StoryboardGenerator, CharacterExtractor
        self._llm = OllamaClient(
            base_url=self.config.local.ollama_url,
            model=self.config.local.ollama_model
        )
        self._storyboard_gen = StoryboardGenerator(self._llm)
        self._character_extractor = CharacterExtractor(self._llm)

        # 图像模块
        from ..image import ComfyUIClient, SceneGenerator, CharacterDesigner
        comfyui = ComfyUIClient(base_url=self.config.local.comfyui_url)
        self._image_gen = SceneGenerator(comfyui)
        self._char_designer = CharacterDesigner(comfyui)

        # TTS模块
        from ..tts import CosyVoiceClient
        self._tts = CosyVoiceClient(base_url=self.config.local.cosyvoice_url)

        # 视频API模块
        from ..video import create_video_client
        if self.config.api.video_api_key:
            self._video_gen = create_video_client(
                provider=self.config.api.video_provider,
                api_key=self.config.api.video_api_key
            )

        # 合成模块
        from ..compose import VideoComposer
        self._composer = VideoComposer()

        logger.info("模块初始化完成")

    def check_services(self) -> Dict[str, bool]:
        """检查本地服务状态"""
        status = {
            "ollama": False,
            "comfyui": False,
            "cosyvoice": False
        }

        if self._llm:
            status["ollama"] = self._llm.check_health()

        from ..image import ComfyUIClient
        comfyui = ComfyUIClient(base_url=self.config.local.comfyui_url)
        status["comfyui"] = comfyui.check_health()

        if self._tts:
            status["cosyvoice"] = self._tts.check_health()

        return status

    def run(self, resume: bool = True) -> None:
        """执行完整流程"""
        # 加载或创建状态
        if resume and self.state_file.exists():
            self.state = PipelineState.load(self.state_file)
            logger.info(f"从 {self.state.current_phase.value} 阶段恢复")
        else:
            self.state = PipelineState()

        try:
            # 按阶段执行
            phase_methods = {
                Phase.INIT: self._phase_init,
                Phase.ANALYZE: self._phase_analyze,
                Phase.CHARACTER_DESIGN: self._phase_character_design,
                Phase.GENERATE_IMAGES: self._phase_generate_images,
                Phase.GENERATE_AUDIO: self._phase_generate_audio,
                Phase.GENERATE_VIDEO: self._phase_generate_video,
                Phase.COMPOSE: self._phase_compose,
            }

            for phase in Phase:
                if phase in [Phase.DONE, Phase.ERROR]:
                    continue

                if self._should_run_phase(phase):
                    self._set_phase(phase)
                    phase_methods[phase]()
                    self._clear_vram()

            self._set_phase(Phase.DONE)
            logger.info("🎉 视频生成完成!")
            self._report_progress("完成", "视频已生成", 1.0)

        except Exception as e:
            logger.error(f"Pipeline执行错误: {e}")
            self.state.add_error(self.state.current_phase.value, None, str(e))
            self._set_phase(Phase.ERROR)
            self._save_state()
            raise

    def _should_run_phase(self, phase: Phase) -> bool:
        """判断是否需要执行某阶段"""
        phase_order = list(Phase)
        current_idx = phase_order.index(self.state.current_phase)
        target_idx = phase_order.index(phase)
        return target_idx >= current_idx

    def _set_phase(self, phase: Phase) -> None:
        """设置当前阶段"""
        self.state.current_phase = phase
        self._save_state()
        if self.on_phase_change:
            self.on_phase_change(phase)
        logger.info(f"进入阶段: {phase.value}")

    def _phase_init(self) -> None:
        """初始化阶段"""
        self._report_progress("初始化", "检查环境和依赖...", 0.0)

        # 确保目录存在
        for dir_name in ["characters", "images", "videos", "audio", "output"]:
            ensure_dir(self.project_path / dir_name)

        # 初始化模块
        self.init_modules()

        # 检查服务
        services = self.check_services()
        unavailable = [k for k, v in services.items() if not v]
        if unavailable:
            logger.warning(f"以下服务不可用: {unavailable}")

        self._report_progress("初始化", "环境准备完成", 1.0)

    def _phase_analyze(self) -> None:
        """分析阶段 - 提取角色和生成分镜"""
        self._report_progress("分析", "读取小说内容...", 0.0)

        novel_path = self.project_path / "input" / "novel.txt"
        if not novel_path.exists():
            raise FileNotFoundError(f"小说文件不存在: {novel_path}")

        novel_text = novel_path.read_text(encoding="utf-8")

        # 提取角色
        self._report_progress("分析", "提取角色信息...", 0.2)
        characters = self._character_extractor.extract(novel_text)
        save_json(self.project_path / "characters.json", characters)

        # 生成分镜
        self._report_progress("分析", "生成分镜脚本...", 0.5)
        storyboard = self._storyboard_gen.generate(novel_text, characters)
        save_json(self.project_path / "storyboard.json", storyboard)

        self.state.total_scenes = storyboard["total_scenes"]
        self._save_state()

        self._report_progress(
            "分析",
            f"完成: {len(characters['characters'])}个角色, {self.state.total_scenes}个场景",
            1.0
        )

    def _phase_character_design(self) -> None:
        """角色设计阶段"""
        self._report_progress("角色设计", "生成角色立绘...", 0.0)

        characters = load_json(self.project_path / "characters.json")
        char_list = characters.get("characters", [])
        total = len(char_list)

        for i, char in enumerate(char_list):
            char_id = char["id"]

            # 检查是否已完成
            if self.state.is_scene_completed(char_id, "character"):
                continue

            self._report_progress(
                "角色设计",
                f"生成 {char['name']} ({i+1}/{total})",
                i / total
            )

            try:
                self._char_designer.generate_character(
                    char,
                    self.project_path / "characters"
                )
                self.state.mark_scene_completed(char_id, "character")
                self._save_state()
            except Exception as e:
                logger.error(f"角色 {char_id} 生成失败: {e}")
                self.state.add_error("character_design", char_id, str(e))

        self._report_progress("角色设计", "角色立绘生成完成", 1.0)

    def _phase_generate_images(self) -> None:
        """图像生成阶段"""
        self._report_progress("图像生成", "生成场景图像...", 0.0)

        storyboard = load_json(self.project_path / "storyboard.json")
        characters = load_json(self.project_path / "characters.json")
        scenes = storyboard.get("scenes", [])
        total = len(scenes)
        failed_count = 0
        success_count = 0

        for i, scene in enumerate(scenes):
            scene_id = scene["id"]

            if self.state.is_scene_completed(scene_id, "image"):
                success_count += 1
                continue

            self._report_progress(
                "图像生成",
                f"场景 {scene_id} ({i+1}/{total})",
                i / total
            )

            try:
                image = self._image_gen.generate_scene(
                    scene,
                    characters,
                    style_preset=self.config.video.style
                )
                image.save(self.project_path / "images" / f"{scene_id}.png")
                self.state.mark_scene_completed(scene_id, "image")
                self.state.current_scene_index = i + 1
                self._save_state()
                success_count += 1
            except Exception as e:
                failed_count += 1
                self._handle_scene_error("generate_images", scene_id, e, total, failed_count - 1)
                self._save_state()

        # 报告最终结果
        if failed_count > 0:
            self._report_progress(
                "图像生成", 
                f"完成: {success_count}成功, {failed_count}失败 (共{total}个)", 
                1.0
            )
            logger.warning(f"图像生成阶段: {failed_count}/{total} 个场景失败")
        else:
            self._report_progress("图像生成", "场景图像生成完成", 1.0)

    def _phase_generate_audio(self) -> None:
        """音频生成阶段"""
        self._report_progress("音频生成", "生成配音...", 0.0)

        storyboard = load_json(self.project_path / "storyboard.json")
        characters = load_json(self.project_path / "characters.json")
        scenes = storyboard.get("scenes", [])
        total = len(scenes)
        failed_count = 0
        success_count = 0

        for i, scene in enumerate(scenes):
            scene_id = scene["id"]

            if self.state.is_scene_completed(scene_id, "audio"):
                success_count += 1
                continue

            self._report_progress(
                "音频生成",
                f"场景 {scene_id} ({i+1}/{total})",
                i / total
            )

            try:
                audio_data = self._tts.generate_scene_audio(
                    scene.get("audio", {}),
                    characters
                )
                audio_data.save(self.project_path / "audio" / f"{scene_id}.wav")
                self.state.mark_scene_completed(scene_id, "audio")
                self._save_state()
                success_count += 1
            except Exception as e:
                failed_count += 1
                self._handle_scene_error("generate_audio", scene_id, e, total, failed_count - 1)
                self._save_state()

        # 报告最终结果
        if failed_count > 0:
            self._report_progress(
                "音频生成", 
                f"完成: {success_count}成功, {failed_count}失败 (共{total}个)", 
                1.0
            )
            logger.warning(f"音频生成阶段: {failed_count}/{total} 个场景失败")
        else:
            self._report_progress("音频生成", "配音生成完成", 1.0)

    def _phase_generate_video(self) -> None:
        """视频生成阶段 (调用远端API)"""
        if not self._video_gen:
            logger.warning("视频API未配置，跳过视频生成阶段")
            return

        self._report_progress("视频生成", "调用API生成视频片段...", 0.0)

        storyboard = load_json(self.project_path / "storyboard.json")
        scenes = storyboard.get("scenes", [])
        total = len(scenes)
        failed_count = 0
        success_count = 0
        skipped_count = 0

        for i, scene in enumerate(scenes):
            scene_id = scene["id"]

            if self.state.is_scene_completed(scene_id, "video"):
                success_count += 1
                continue

            image_path = self.project_path / "images" / f"{scene_id}.png"
            if not image_path.exists():
                logger.warning(f"图像不存在，跳过: {scene_id}")
                skipped_count += 1
                continue

            self._report_progress(
                "视频生成",
                f"场景 {scene_id} ({i+1}/{total})",
                i / total
            )

            try:
                motion_prompt = self._build_motion_prompt(scene)
                video_data = self._video_gen.generate(
                    image_path=image_path,
                    motion_prompt=motion_prompt,
                    duration=scene.get("duration", 5.0)
                )
                video_data.save(self.project_path / "videos" / f"{scene_id}.mp4")
                self.state.mark_scene_completed(scene_id, "video")
                self._save_state()
                success_count += 1
            except Exception as e:
                failed_count += 1
                self._handle_scene_error("generate_video", scene_id, e, total, failed_count - 1)
                self._save_state()

        # 报告最终结果
        result_parts = [f"{success_count}成功"]
        if failed_count > 0:
            result_parts.append(f"{failed_count}失败")
        if skipped_count > 0:
            result_parts.append(f"{skipped_count}跳过")
        
        self._report_progress(
            "视频生成", 
            f"完成: {', '.join(result_parts)} (共{total}个)", 
            1.0
        )
        
        if failed_count > 0:
            logger.warning(f"视频生成阶段: {failed_count}/{total} 个场景失败")

    def _phase_compose(self) -> None:
        """合成阶段"""
        self._report_progress("合成", "合成最终视频...", 0.0)

        storyboard = load_json(self.project_path / "storyboard.json")
        scenes = storyboard.get("scenes", [])

        # 收集所有片段
        clips = []
        skipped_scenes = []
        
        for scene in scenes:
            scene_id = scene["id"]
            video_path = self.project_path / "videos" / f"{scene_id}.mp4"
            audio_path = self.project_path / "audio" / f"{scene_id}.wav"
            image_path = self.project_path / "images" / f"{scene_id}.png"

            # 优先使用视频，其次使用图像
            source_path = None
            if video_path.exists():
                source_path = video_path
            elif image_path.exists():
                source_path = image_path
                logger.info(f"场景 {scene_id} 使用图像替代视频")
            else:
                # 没有可用资源，跳过此场景
                skipped_scenes.append(scene_id)
                logger.warning(f"场景 {scene_id} 无可用资源，跳过")
                continue

            clips.append({
                "video": source_path,
                "audio": audio_path if audio_path.exists() else None,
                "subtitle": scene.get("subtitle", {}),
                "scene_id": scene_id,
                "duration": scene.get("duration", 5.0)
            })

        if not clips:
            raise RuntimeError("没有可用的视频片段，无法合成")
        
        # 报告跳过的场景
        if skipped_scenes:
            logger.warning(f"合成阶段跳过 {len(skipped_scenes)} 个场景: {', '.join(skipped_scenes[:5])}{'...' if len(skipped_scenes) > 5 else ''}")
            self._report_progress(
                "合成", 
                f"准备合成 {len(clips)}/{len(scenes)} 个场景 ({len(skipped_scenes)}个跳过)", 
                0.1
            )

        # 合成视频
        self._report_progress("合成", "拼接视频片段...", 0.3)
        output_path = self.project_path / "output" / "final_video.mp4"

        self._composer.compose(
            clips=clips,
            output_path=output_path
        )

        # 生成字幕 (只为有资源的场景生成)
        self._report_progress("合成", "生成字幕...", 0.7)
        from ..compose import SubtitleGenerator
        subtitle_gen = SubtitleGenerator()
        subtitle_path = self.project_path / "output" / "subtitles.srt"
        
        # 过滤出有资源的场景
        valid_scenes = [s for s in scenes if s["id"] not in skipped_scenes]
        subtitle_gen.generate_srt(valid_scenes, subtitle_path)

        # 最终报告
        result_msg = f"视频已保存: {output_path}"
        if skipped_scenes:
            result_msg += f" (跳过{len(skipped_scenes)}个失败场景)"
        self._report_progress("合成", result_msg, 1.0)

    def _build_motion_prompt(self, scene: Dict[str, Any]) -> str:
        """构建视频运动提示词"""
        camera = scene.get("visual", {}).get("camera", {})
        camera_type = camera.get("type", "static")
        start_frame = camera.get("start_frame", "medium_shot")
        end_frame = camera.get("end_frame", "medium_shot")

        return f"{camera_type} camera movement, from {start_frame} to {end_frame}"

    def _save_state(self) -> None:
        """保存状态"""
        if self.state:
            self.state.save(self.state_file)

    def _report_progress(self, stage: str, detail: str, progress: float) -> None:
        """报告进度"""
        if self.on_progress:
            self.on_progress(stage, detail, progress)
        logger.info(f"[{stage}] {detail} ({progress*100:.1f}%)")

    def _clear_vram(self) -> None:
        """清理显存"""
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def _check_failure_threshold(self, phase_name: str, total: int, failed: int) -> None:
        """检查失败率是否超过阈值"""
        if total == 0:
            return
        
        failure_rate = failed / total
        if failure_rate > self.failure_threshold:
            error_msg = f"{phase_name} 失败率 ({failure_rate*100:.1f}%) 超过阈值 ({self.failure_threshold*100:.1f}%)"
            logger.error(error_msg)
            if not self.skip_failed_scenes:
                raise RuntimeError(error_msg)
            else:
                logger.warning(f"继续执行，但 {failed}/{total} 个任务失败")

    def _handle_scene_error(
        self, 
        phase_name: str, 
        scene_id: str, 
        error: Exception,
        total_scenes: int,
        current_failed: int
    ) -> bool:
        """
        处理场景错误
        返回: True表示继续执行, False表示应该停止
        """
        error_msg = str(error)
        logger.error(f"场景 {scene_id} 处理失败: {error_msg}")
        self.state.add_error(phase_name, scene_id, error_msg)
        
        # 触发错误回调
        if self.on_error:
            self.on_error(scene_id, error_msg)
        
        if not self.skip_failed_scenes:
            # 不跳过失败场景时，立即抛出异常
            raise error
        
        # 检查失败率
        failure_rate = (current_failed + 1) / total_scenes
        if failure_rate > self.failure_threshold:
            logger.error(f"失败率 ({failure_rate*100:.1f}%) 超过阈值，停止执行")
            raise RuntimeError(f"失败率超过阈值: {current_failed + 1}/{total_scenes}")
        
        return True  # 继续执行

    # 单阶段执行方法
    def run_phase(self, phase: Phase) -> None:
        """单独执行某个阶段"""
        if self.state is None:
            self.state = PipelineState.load(self.state_file) if self.state_file.exists() else PipelineState()

        self.init_modules()

        phase_methods = {
            Phase.ANALYZE: self._phase_analyze,
            Phase.CHARACTER_DESIGN: self._phase_character_design,
            Phase.GENERATE_IMAGES: self._phase_generate_images,
            Phase.GENERATE_AUDIO: self._phase_generate_audio,
            Phase.GENERATE_VIDEO: self._phase_generate_video,
            Phase.COMPOSE: self._phase_compose,
        }

        if phase in phase_methods:
            self._set_phase(phase)
            phase_methods[phase]()
            self._clear_vram()

    def _phase_generate_images_parallel(self) -> None:
        """图像生成阶段 (并行版本)"""
        self._report_progress("图像生成", "生成场景图像 (并行)...", 0.0)

        storyboard = load_json(self.project_path / "storyboard.json")
        characters = load_json(self.project_path / "characters.json")
        scenes = storyboard.get("scenes", [])
        
        pending_scenes = [
            s for s in scenes 
            if not self.state.is_scene_completed(s["id"], "image")
        ]
        
        if not pending_scenes:
            self._report_progress("图像生成", "所有场景图像已生成", 1.0)
            return
        
        total = len(pending_scenes)
        logger.info(f"并行生成 {total} 个场景图像")
        
        def generate_single_image(scene: Dict[str, Any]) -> Dict[str, Any]:
            """生成单个场景图像"""
            scene_id = scene["id"]
            try:
                image = self._image_gen.generate_scene(
                    scene,
                    characters,
                    style_preset=self.config.video.style
                )
                image.save(self.project_path / "images" / f"{scene_id}.png")
                return {"scene_id": scene_id, "success": True, "error": None}
            except Exception as e:
                logger.error(f"场景 {scene_id} 图像生成失败: {e}")
                return {"scene_id": scene_id, "success": False, "error": str(e)}
        
        tasks = [
            {
                "task_id": s["id"],
                "func": generate_single_image,
                "args": (s,),
            }
            for s in pending_scenes
        ]
        
        def on_progress(task_id: str, progress: float):
            self._report_progress("图像生成", f"进度 {progress*100:.0f}%", progress)
        
        results = run_parallel_sync(
            tasks,
            max_workers=self.config.generation.max_concurrent_tasks,
            on_progress=on_progress
        )
        
        for r in results:
            result_data = r.get("result", {})
            if result_data and result_data.get("success"):
                self.state.mark_scene_completed(result_data["scene_id"], "image")
            elif result_data:
                self.state.add_error("generate_images", result_data["scene_id"], result_data.get("error", "未知错误"))
        
        self._save_state()
        self._report_progress("图像生成", "场景图像生成完成", 1.0)

    def _phase_generate_audio_parallel(self) -> None:
        """音频生成阶段 (并行版本)"""
        self._report_progress("音频生成", "生成配音 (并行)...", 0.0)

        storyboard = load_json(self.project_path / "storyboard.json")
        characters = load_json(self.project_path / "characters.json")
        scenes = storyboard.get("scenes", [])
        
        pending_scenes = [
            s for s in scenes
            if not self.state.is_scene_completed(s["id"], "audio")
        ]
        
        if not pending_scenes:
            self._report_progress("音频生成", "所有场景音频已生成", 1.0)
            return
        
        total = len(pending_scenes)
        logger.info(f"并行生成 {total} 个场景音频")
        
        def generate_single_audio(scene: Dict[str, Any]) -> Dict[str, Any]:
            """生成单个场景音频"""
            scene_id = scene["id"]
            try:
                audio_data = self._tts.generate_scene_audio(
                    scene.get("audio", {}),
                    characters
                )
                audio_data.save(self.project_path / "audio" / f"{scene_id}.wav")
                return {"scene_id": scene_id, "success": True, "error": None}
            except Exception as e:
                logger.error(f"场景 {scene_id} 音频生成失败: {e}")
                return {"scene_id": scene_id, "success": False, "error": str(e)}
        
        tasks = [
            {
                "task_id": s["id"],
                "func": generate_single_audio,
                "args": (s,),
            }
            for s in pending_scenes
        ]
        
        def on_progress(task_id: str, progress: float):
            self._report_progress("音频生成", f"进度 {progress*100:.0f}%", progress)
        
        results = run_parallel_sync(
            tasks,
            max_workers=self.config.generation.max_concurrent_tasks,
            on_progress=on_progress
        )
        
        for r in results:
            result_data = r.get("result", {})
            if result_data and result_data.get("success"):
                self.state.mark_scene_completed(result_data["scene_id"], "audio")
            elif result_data:
                self.state.add_error("generate_audio", result_data["scene_id"], result_data.get("error", "未知错误"))
        
        self._save_state()
        self._report_progress("音频生成", "配音生成完成", 1.0)

    def _phase_generate_images_and_audio_parallel(self) -> None:
        """图像和音频同时并行生成"""
        self._report_progress("并行生成", "同时生成图像和音频...", 0.0)

        storyboard = load_json(self.project_path / "storyboard.json")
        characters = load_json(self.project_path / "characters.json")
        scenes = storyboard.get("scenes", [])

        tasks = []
        
        for scene in scenes:
            scene_id = scene["id"]
            
            if not self.state.is_scene_completed(scene_id, "image"):
                tasks.append({
                    "task_id": f"image_{scene_id}",
                    "func": self._generate_scene_image,
                    "args": (scene, characters),
                })
            
            if not self.state.is_scene_completed(scene_id, "audio"):
                tasks.append({
                    "task_id": f"audio_{scene_id}",
                    "func": self._generate_scene_audio,
                    "args": (scene, characters),
                })

        if not tasks:
            self._report_progress("并行生成", "所有内容已生成", 1.0)
            return

        logger.info(f"并行执行 {len(tasks)} 个任务")
        
        def on_progress(task_id: str, progress: float):
            self._report_progress("并行生成", f"进度 {progress*100:.0f}%", progress)

        results = run_parallel_sync(
            tasks,
            max_workers=self.config.generation.max_concurrent_tasks,
            on_progress=on_progress
        )
        
        for r in results:
            task_id = r.get("task_id", "")
            result_data = r.get("result", {})
            
            if result_data and result_data.get("success"):
                scene_id = result_data["scene_id"]
                task_type = result_data["type"]
                self.state.mark_scene_completed(scene_id, task_type)
            elif result_data:
                self.state.add_error(
                    f"generate_{result_data.get('type', 'unknown')}",
                    result_data.get("scene_id", "unknown"),
                    result_data.get("error", "未知错误")
                )

        self._save_state()
        self._report_progress("并行生成", "图像和音频生成完成", 1.0)

    def _generate_scene_image(self, scene: Dict[str, Any], characters: Dict[str, Any]) -> Dict[str, Any]:
        """生成单个场景图像 (供并行调用)"""
        scene_id = scene["id"]
        try:
            image = self._image_gen.generate_scene(
                scene,
                characters,
                style_preset=self.config.video.style
            )
            image.save(self.project_path / "images" / f"{scene_id}.png")
            return {"scene_id": scene_id, "type": "image", "success": True, "error": None}
        except Exception as e:
            logger.error(f"场景 {scene_id} 图像生成失败: {e}")
            return {"scene_id": scene_id, "type": "image", "success": False, "error": str(e)}

    def _generate_scene_audio(self, scene: Dict[str, Any], characters: Dict[str, Any]) -> Dict[str, Any]:
        """生成单个场景音频 (供并行调用)"""
        scene_id = scene["id"]
        try:
            audio_data = self._tts.generate_scene_audio(
                scene.get("audio", {}),
                characters
            )
            audio_data.save(self.project_path / "audio" / f"{scene_id}.wav")
            return {"scene_id": scene_id, "type": "audio", "success": True, "error": None}
        except Exception as e:
            logger.error(f"场景 {scene_id} 音频生成失败: {e}")
            return {"scene_id": scene_id, "type": "audio", "success": False, "error": str(e)}

    def run_parallel(self, resume: bool = True) -> None:
        """使用并行模式执行流程"""
        if resume and self.state_file.exists():
            self.state = PipelineState.load(self.state_file)
            logger.info(f"从 {self.state.current_phase.value} 阶段恢复")
        else:
            self.state = PipelineState()

        try:
            phase_methods = {
                Phase.INIT: self._phase_init,
                Phase.ANALYZE: self._phase_analyze,
                Phase.CHARACTER_DESIGN: self._phase_character_design,
                Phase.GENERATE_IMAGES: self._phase_generate_images_parallel,
                Phase.GENERATE_AUDIO: self._phase_generate_audio_parallel,
                Phase.GENERATE_VIDEO: self._phase_generate_video,
                Phase.COMPOSE: self._phase_compose,
            }

            for phase in Phase:
                if phase in [Phase.DONE, Phase.ERROR]:
                    continue

                if self._should_run_phase(phase):
                    self._set_phase(phase)
                    phase_methods[phase]()
                    self._clear_vram()

            self._set_phase(Phase.DONE)
            logger.info("视频生成完成!")
            self._report_progress("完成", "视频已生成", 1.0)

        except Exception as e:
            logger.error(f"Pipeline执行错误: {e}")
            self.state.add_error(self.state.current_phase.value, None, str(e))
            self._set_phase(Phase.ERROR)
            self._save_state()
            raise
