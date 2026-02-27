"""Pipeline流程控制器"""
import gc
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
import torch

from .state import PipelineState, Phase
from .scheduler import run_parallel_sync, TaskPriority
from ..exceptions import StopRequestedException
from ..utils.config import Config, get_config
from ..utils.logger import get_logger
from ..utils.file_utils import load_json, save_json, load_yaml, ensure_dir
from ..utils.gpu_monitor import get_gpu_monitor

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

        # 中断控制
        self._stop_requested: bool = False
        self._is_running: bool = False

    def request_stop(self) -> None:
        """请求停止当前任务"""
        if self._is_running:
            logger.info("收到停止请求，将在当前场景完成后停止...")
            self._stop_requested = True

    def is_stop_requested(self) -> bool:
        """检查是否请求了停止"""
        return self._stop_requested

    def _check_stop(self) -> bool:
        """检查点：如果请求停止则抛出异常

        Returns:
            True 如果应该继续，抛出 StopRequestedException 如果应该停止
        """
        if self._stop_requested:
            logger.info("检测到停止请求，正在优雅停止...")
            raise StopRequestedException("任务被用户中断")
        return True

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
        from ..image import ComfyUIClient, SceneGenerator, CharacterDesigner, CharacterReferenceManager
        comfyui = ComfyUIClient(base_url=self.config.local.comfyui_url)

        # 初始化角色参考图管理器 (用于角色一致性)
        self._reference_manager = CharacterReferenceManager(comfyui, self.project_path)

        # 获取角色一致性配置
        char_consistency = getattr(self.config.image, 'character_consistency', None)
        consistency_method = char_consistency.method if char_consistency else "none"

        # 获取 IP-Adapter 配置
        ipadapter_config = getattr(self.config.image, 'ipadapter', None)
        ipadapter_enabled = ipadapter_config.enabled if ipadapter_config else False

        # 获取 Z-Image-i2L 配置
        i2l_config = getattr(self.config.image, 'i2l', None)
        i2l_enabled = i2l_config.enabled if i2l_config else False

        # 配置工作流路径
        workflow_dir = Path("config/comfyui_workflows")
        base_workflow = workflow_dir / self.config.image.workflow
        ipadapter_workflow = None
        i2l_workflow = None

        # IP-Adapter 工作流
        if ipadapter_enabled and ipadapter_config:
            ipadapter_workflow_name = getattr(ipadapter_config, 'workflow', 'z_image_turbo_ipadapter.json')
            ipadapter_workflow = workflow_dir / ipadapter_workflow_name

        # i2L 工作流
        if i2l_enabled and i2l_config:
            i2l_workflow_name = getattr(i2l_config, 'workflow', 'z_image_i2l.json')
            i2l_workflow = workflow_dir / i2l_workflow_name

        # 决定是否启用参考图管理器
        use_reference_manager = (consistency_method != "none") and (ipadapter_enabled or i2l_enabled)

        # 初始化场景生成器
        self._image_gen = SceneGenerator(
            comfyui,
            workflow_path=base_workflow if base_workflow.exists() else None,
            ipadapter_workflow_path=ipadapter_workflow if ipadapter_workflow and ipadapter_workflow.exists() else None,
            i2l_workflow_path=i2l_workflow if i2l_workflow and i2l_workflow.exists() else None,
            reference_manager=self._reference_manager if use_reference_manager else None,
            consistency_method=consistency_method
        )

        # 配置 IP-Adapter 参数
        if ipadapter_enabled and ipadapter_config:
            self._image_gen.configure_ipadapter(
                weight=getattr(ipadapter_config, 'weight', 0.8),
                noise=getattr(ipadapter_config, 'noise', 0.0),
                weight_type=getattr(ipadapter_config, 'weight_type', 'standard'),
                start_at=getattr(ipadapter_config, 'start_at', 0.0),
                end_at=getattr(ipadapter_config, 'end_at', 1.0)
            )

        # 配置 i2L 参数
        if i2l_enabled and i2l_config:
            self._image_gen.configure_i2l(
                lora_strength=getattr(i2l_config, 'lora_strength', 1.0),
                apply_to_unet=getattr(i2l_config, 'apply_to_unet', True)
            )

        # 初始化角色设计器
        self._char_designer = CharacterDesigner(comfyui)
        self._char_designer.reference_manager = self._reference_manager

        # TTS模块
        from ..tts import CosyVoiceClient
        self._tts = CosyVoiceClient(base_url=self.config.local.cosyvoice_url)

        # 视频生成模块
        video_provider = getattr(self.config.video, 'provider', 'api')

        if video_provider == "local":
            # 本地视频生成 (Wan 2.1)
            from ..video import WanLocalVideoGenerator
            video_local_config = getattr(self.config.video, 'local', None)
            wan_workflow = None

            if video_local_config:
                wan_workflow_name = getattr(video_local_config, 'workflow', 'wan2_i2v.json')
                wan_workflow = workflow_dir / wan_workflow_name

            self._video_gen = WanLocalVideoGenerator(
                comfyui_client=comfyui,
                workflow_path=wan_workflow if wan_workflow and wan_workflow.exists() else None,
                default_video_length=getattr(video_local_config, 'video_length', 81) if video_local_config else 81,
                default_fps=getattr(video_local_config, 'fps', 16) if video_local_config else 16
            )
            logger.info("使用本地 Wan 2.1 视频生成")
        else:
            # 远端 API 视频生成
            from ..video import create_video_client
            if self.config.api.video_api_key:
                self._video_gen = create_video_client(
                    provider=self.config.api.video_provider,
                    api_key=self.config.api.video_api_key
                )
                logger.info(f"使用远端 API 视频生成: {self.config.api.video_provider}")

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
        # 重置中断状态
        self._stop_requested = False
        self._is_running = True

        # 加载或创建状态
        if resume and self.state_file.exists():
            self.state = PipelineState.load(self.state_file)
            logger.info(f"从 {self.state.current_phase.value} 阶段恢复")
        else:
            self.state = PipelineState()

        try:
            # 根据配置选择并行或串行模式
            use_parallel = getattr(self.config.generation, 'enable_parallel', True)

            # 按阶段执行
            if use_parallel:
                logger.info("使用并行执行模式（图像和音频同时生成）")
                phase_methods = {
                    Phase.INIT: self._phase_init,
                    Phase.ANALYZE: self._phase_analyze,
                    Phase.CHARACTER_DESIGN: self._phase_character_design,
                    Phase.GENERATE_IMAGES: self._phase_generate_images_parallel,
                    Phase.GENERATE_AUDIO: self._phase_generate_audio_parallel,
                    Phase.GENERATE_VIDEO: self._phase_generate_video,
                    Phase.COMPOSE: self._phase_compose,
                }
            else:
                logger.info("使用串行执行模式")
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

                # 阶段间检查点
                self._check_stop()

                if self._should_run_phase(phase):
                    self._set_phase(phase)
                    phase_methods[phase]()
                    self._clear_vram()

            self._set_phase(Phase.DONE)
            logger.info("🎉 视频生成完成!")
            self._report_progress("完成", "视频已生成", 1.0)

        except StopRequestedException:
            logger.info("任务已被用户停止")
            self._report_progress(self.state.current_phase.value, "任务已停止", 0.0)
            self._save_state()
            # 不设置 ERROR 状态，保持当前状态以便恢复
        except Exception as e:
            logger.error(f"Pipeline执行错误: {e}")
            self.state.add_error(self.state.current_phase.value, None, str(e))
            self._set_phase(Phase.ERROR)
            self._save_state()
            raise
        finally:
            # 重置运行状态
            self._is_running = False

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
            # 角色级检查点
            self._check_stop()

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
            except StopRequestedException:
                raise  # 重新抛出中断异常
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
        regenerated_count = 0

        # 加载角色参考图 (用于 IP-Adapter 角色一致性)
        self._load_character_references(characters)

        # 获取失效的场景列表
        invalidated = set(self.state.get_invalidated_scenes("image"))
        if invalidated:
            logger.info(f"检测到 {len(invalidated)} 个失效场景需要重新生成图像")

        for i, scene in enumerate(scenes):
            # 场景级检查点
            self._check_stop()

            scene_id = scene["id"]
            is_invalidated = scene_id in invalidated

            # 跳过已完成且未失效的场景
            if self.state.is_scene_completed(scene_id, "image") and not is_invalidated:
                success_count += 1
                continue

            action = "重新生成" if is_invalidated else "生成"
            self._report_progress(
                "图像生成",
                f"{action}场景 {scene_id} ({i+1}/{total})",
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
                # 清除失效标记
                if is_invalidated:
                    self.state.clear_invalidation(scene_id, "image")
                    regenerated_count += 1
                self.state.current_scene_index = i + 1
                self._save_state()
                success_count += 1
            except StopRequestedException:
                raise  # 重新抛出中断异常
            except Exception as e:
                failed_count += 1
                self._handle_scene_error("generate_images", scene_id, e, total, failed_count - 1)
                self._save_state()

        # 报告最终结果
        result_parts = [f"{success_count}成功"]
        if regenerated_count > 0:
            result_parts.append(f"{regenerated_count}重新生成")
        if failed_count > 0:
            result_parts.append(f"{failed_count}失败")

        self._report_progress(
            "图像生成",
            f"完成: {', '.join(result_parts)} (共{total}个)",
            1.0
        )
        if failed_count > 0:
            logger.warning(f"图像生成阶段: {failed_count}/{total} 个场景失败")

    def _phase_generate_audio(self) -> None:
        """音频生成阶段"""
        self._report_progress("音频生成", "生成配音...", 0.0)

        storyboard = load_json(self.project_path / "storyboard.json")
        characters = load_json(self.project_path / "characters.json")
        scenes = storyboard.get("scenes", [])
        total = len(scenes)
        failed_count = 0
        success_count = 0
        regenerated_count = 0

        # 获取失效的场景列表
        invalidated = set(self.state.get_invalidated_scenes("audio"))
        if invalidated:
            logger.info(f"检测到 {len(invalidated)} 个失效场景需要重新生成音频")

        for i, scene in enumerate(scenes):
            # 场景级检查点
            self._check_stop()

            scene_id = scene["id"]
            is_invalidated = scene_id in invalidated

            # 跳过已完成且未失效的场景
            if self.state.is_scene_completed(scene_id, "audio") and not is_invalidated:
                success_count += 1
                continue

            action = "重新生成" if is_invalidated else "生成"
            self._report_progress(
                "音频生成",
                f"{action}场景 {scene_id} ({i+1}/{total})",
                i / total
            )

            try:
                audio_data = self._tts.generate_scene_audio(
                    scene.get("audio", {}),
                    characters
                )
                audio_data.save(self.project_path / "audio" / f"{scene_id}.wav")
                self.state.mark_scene_completed(scene_id, "audio")
                # 清除失效标记
                if is_invalidated:
                    self.state.clear_invalidation(scene_id, "audio")
                    regenerated_count += 1
                self._save_state()
                success_count += 1
            except StopRequestedException:
                raise  # 重新抛出中断异常
            except Exception as e:
                failed_count += 1
                self._handle_scene_error("generate_audio", scene_id, e, total, failed_count - 1)
                self._save_state()

        # 报告最终结果
        result_parts = [f"{success_count}成功"]
        if regenerated_count > 0:
            result_parts.append(f"{regenerated_count}重新生成")
        if failed_count > 0:
            result_parts.append(f"{failed_count}失败")

        self._report_progress(
            "音频生成",
            f"完成: {', '.join(result_parts)} (共{total}个)",
            1.0
        )
        if failed_count > 0:
            logger.warning(f"音频生成阶段: {failed_count}/{total} 个场景失败")

    def _phase_generate_video(self) -> None:
        """视频生成阶段 (调用远端API)"""
        if not self._video_gen:
            logger.warning("视频API未配置，跳过视频生成阶段")
            return

        self._report_progress("视频生成", "检查 API 配额...", 0.0)

        storyboard = load_json(self.project_path / "storyboard.json")
        scenes = storyboard.get("scenes", [])
        total = len(scenes)

        # 获取失效的场景列表
        invalidated = set(self.state.get_invalidated_scenes("video"))
        if invalidated:
            logger.info(f"检测到 {len(invalidated)} 个失效场景需要重新生成视频")

        # 计算待生成的场景数量
        pending_scenes = [
            s for s in scenes
            if not self.state.is_scene_completed(s["id"], "video") or s["id"] in invalidated
        ]
        pending_count = len(pending_scenes)

        # 配额预检查
        if pending_count > 0:
            is_sufficient, quota_msg = self._video_gen.check_quota_sufficient(pending_count)
            logger.info(f"视频配额检查: {quota_msg}")

            if not is_sufficient:
                self.state.add_error("generate_video", None, f"配额不足: {quota_msg}")
                self._save_state()
                raise RuntimeError(f"视频生成配额不足: {quota_msg}，请充值后重试")

        self._report_progress("视频生成", "调用API生成视频片段...", 0.0)

        failed_count = 0
        success_count = 0
        skipped_count = 0
        regenerated_count = 0

        for i, scene in enumerate(scenes):
            # 场景级检查点
            self._check_stop()

            scene_id = scene["id"]
            is_invalidated = scene_id in invalidated

            # 跳过已完成且未失效的场景
            if self.state.is_scene_completed(scene_id, "video") and not is_invalidated:
                success_count += 1
                continue

            image_path = self.project_path / "images" / f"{scene_id}.png"
            if not image_path.exists():
                logger.warning(f"图像不存在，跳过: {scene_id}")
                skipped_count += 1
                continue

            action = "重新生成" if is_invalidated else "生成"
            self._report_progress(
                "视频生成",
                f"{action}场景 {scene_id} ({i+1}/{total})",
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
                # 清除失效标记
                if is_invalidated:
                    self.state.clear_invalidation(scene_id, "video")
                    regenerated_count += 1
                self._save_state()
                success_count += 1
            except StopRequestedException:
                raise  # 重新抛出中断异常
            except Exception as e:
                failed_count += 1
                self._handle_scene_error("generate_video", scene_id, e, total, failed_count - 1)
                self._save_state()

        # 报告最终结果
        result_parts = [f"{success_count}成功"]
        if regenerated_count > 0:
            result_parts.append(f"{regenerated_count}重新生成")
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
            # 场景级检查点
            self._check_stop()

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

    def _load_character_references(self, characters: Dict[str, Any]) -> None:
        """加载角色参考图到 IP-Adapter 管理器

        从已生成的角色立绘中加载参考图，用于场景生成时的角色一致性控制。

        Args:
            characters: 角色配置字典
        """
        if not hasattr(self, '_reference_manager') or not self._reference_manager:
            logger.debug("参考图管理器未初始化，跳过加载")
            return

        ipadapter_config = getattr(self.config.image, 'ipadapter', None)
        if not ipadapter_config or not ipadapter_config.enabled:
            logger.debug("IP-Adapter 未启用，跳过加载参考图")
            return

        # 设置项目目录
        self._reference_manager.set_project_dir(self.project_path)

        # 从角色配置批量加载参考图
        char_dir = self.project_path / "characters"
        loaded = self._reference_manager.load_from_characters_json(characters, char_dir)

        if loaded:
            logger.info(f"已加载 {len(loaded)} 个角色的参考图用于 IP-Adapter")
        else:
            logger.info("未找到可用的角色参考图")

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

    def run_from_phase(self, start_phase: Phase) -> None:
        """从指定阶段开始执行后续所有阶段

        Args:
            start_phase: 起始阶段
        """
        if self.state is None:
            self.state = PipelineState.load(self.state_file) if self.state_file.exists() else PipelineState()

        self.init_modules()

        phase_methods = {
            Phase.INIT: self._phase_init,
            Phase.ANALYZE: self._phase_analyze,
            Phase.CHARACTER_DESIGN: self._phase_character_design,
            Phase.GENERATE_IMAGES: self._phase_generate_images,
            Phase.GENERATE_AUDIO: self._phase_generate_audio,
            Phase.GENERATE_VIDEO: self._phase_generate_video,
            Phase.COMPOSE: self._phase_compose,
        }

        phase_order = list(Phase)
        start_idx = phase_order.index(start_phase)

        try:
            for phase in phase_order[start_idx:]:
                if phase in [Phase.DONE, Phase.ERROR]:
                    continue
                if phase in phase_methods:
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

    def run_invalidated_only(self) -> Dict[str, Any]:
        """仅处理失效的场景

        用于分镜修改后的增量更新，只重新生成被标记为失效的场景资源。

        Returns:
            包含处理结果的字典
        """
        if self.state is None:
            self.state = PipelineState.load(self.state_file) if self.state_file.exists() else PipelineState()

        if not self.state.has_invalidated_scenes():
            logger.info("没有失效的场景需要处理")
            return {"success": True, "message": "没有失效的场景", "regenerated": {}}

        self.init_modules()

        result = {
            "success": True,
            "regenerated": {
                "image": 0,
                "audio": 0,
                "video": 0,
            },
            "errors": []
        }

        storyboard = load_json(self.project_path / "storyboard.json")
        characters = load_json(self.project_path / "characters.json")
        scenes = storyboard.get("scenes", [])
        scene_map = {s["id"]: s for s in scenes}

        # 加载角色参考图
        self._load_character_references(characters)

        # 处理失效的图像
        for scene_id in list(self.state.get_invalidated_scenes("image")):
            if scene_id not in scene_map:
                continue
            scene = scene_map[scene_id]
            try:
                self._report_progress("增量更新", f"重新生成图像: {scene_id}", 0.3)
                image = self._image_gen.generate_scene(scene, characters, style_preset=self.config.video.style)
                image.save(self.project_path / "images" / f"{scene_id}.png")
                self.state.mark_scene_completed(scene_id, "image")
                self.state.clear_invalidation(scene_id, "image")
                result["regenerated"]["image"] += 1
            except Exception as e:
                result["errors"].append({"scene_id": scene_id, "type": "image", "error": str(e)})

        # 处理失效的音频
        for scene_id in list(self.state.get_invalidated_scenes("audio")):
            if scene_id not in scene_map:
                continue
            scene = scene_map[scene_id]
            try:
                self._report_progress("增量更新", f"重新生成音频: {scene_id}", 0.5)
                audio_data = self._tts.generate_scene_audio(scene.get("audio", {}), characters)
                audio_data.save(self.project_path / "audio" / f"{scene_id}.wav")
                self.state.mark_scene_completed(scene_id, "audio")
                self.state.clear_invalidation(scene_id, "audio")
                result["regenerated"]["audio"] += 1
            except Exception as e:
                result["errors"].append({"scene_id": scene_id, "type": "audio", "error": str(e)})

        # 处理失效的视频
        if self._video_gen:
            for scene_id in list(self.state.get_invalidated_scenes("video")):
                if scene_id not in scene_map:
                    continue
                scene = scene_map[scene_id]
                image_path = self.project_path / "images" / f"{scene_id}.png"
                if not image_path.exists():
                    continue
                try:
                    self._report_progress("增量更新", f"重新生成视频: {scene_id}", 0.7)
                    motion_prompt = self._build_motion_prompt(scene)
                    video_data = self._video_gen.generate(
                        image_path=image_path,
                        motion_prompt=motion_prompt,
                        duration=scene.get("duration", 5.0)
                    )
                    video_data.save(self.project_path / "videos" / f"{scene_id}.mp4")
                    self.state.mark_scene_completed(scene_id, "video")
                    self.state.clear_invalidation(scene_id, "video")
                    result["regenerated"]["video"] += 1
                except Exception as e:
                    result["errors"].append({"scene_id": scene_id, "type": "video", "error": str(e)})

        self._save_state()
        self._clear_vram()

        total_regenerated = sum(result["regenerated"].values())
        if result["errors"]:
            result["success"] = False
            result["message"] = f"重新生成完成，{total_regenerated}成功，{len(result['errors'])}失败"
        else:
            result["message"] = f"重新生成完成，共{total_regenerated}个资源"

        self._report_progress("增量更新", result["message"], 1.0)
        return result

    def _phase_generate_images_parallel(self) -> None:
        """图像生成阶段 (并行版本)"""
        # 阶段开始前检查中断
        self._check_stop()

        self._report_progress("图像生成", "生成场景图像 (并行)...", 0.0)

        storyboard = load_json(self.project_path / "storyboard.json")
        characters = load_json(self.project_path / "characters.json")
        scenes = storyboard.get("scenes", [])

        # 加载角色参考图 (用于 IP-Adapter 角色一致性)
        self._load_character_references(characters)

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

        # 动态计算并发数：基于当前 GPU 显存可用量
        gpu_monitor = get_gpu_monitor()
        dynamic_workers = gpu_monitor.calculate_optimal_workers(
            min_workers=1,
            max_workers=self.config.generation.max_concurrent_tasks,
            memory_per_task_mb=2500.0,  # ComfyUI 单任务预估显存占用
            safety_margin=0.2
        )
        logger.info(f"图像生成并发数: {dynamic_workers} (配置上限: {self.config.generation.max_concurrent_tasks})")

        results = run_parallel_sync(
            tasks,
            max_workers=dynamic_workers,
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
        # 阶段开始前检查中断
        self._check_stop()

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

        # 音频生成对显存要求较低，但仍使用动态计算以防止资源冲突
        gpu_monitor = get_gpu_monitor()
        dynamic_workers = gpu_monitor.calculate_optimal_workers(
            min_workers=1,
            max_workers=self.config.generation.max_concurrent_tasks,
            memory_per_task_mb=1000.0,  # TTS 任务显存占用较低
            safety_margin=0.15
        )
        logger.info(f"音频生成并发数: {dynamic_workers} (配置上限: {self.config.generation.max_concurrent_tasks})")

        results = run_parallel_sync(
            tasks,
            max_workers=dynamic_workers,
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

        # 加载角色参考图 (用于 IP-Adapter 角色一致性)
        self._load_character_references(characters)

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
