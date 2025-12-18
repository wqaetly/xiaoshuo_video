"""
小说转视频 - Gradio Web界面
提供可视化的项目管理、预览和调整功能
"""
import gradio as gr
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import json
import threading

from .pipeline import PipelineController, Phase, PipelineState
from .llm import OllamaClient, StoryboardGenerator, CharacterExtractor
from .image import ComfyUIClient
from .tts import CosyVoiceClient
from .utils.config import get_config, Config
from .utils.file_utils import load_json, save_json, ensure_dir
from .utils.logger import get_logger

logger = get_logger(__name__)


class NovelVideoApp:
    """小说转视频Web应用"""

    def __init__(self):
        self.config = get_config()
        self.current_project: Optional[Path] = None
        self.pipeline: Optional[PipelineController] = None
        self.is_running = False

    def create_ui(self) -> gr.Blocks:
        """创建Gradio界面"""
        with gr.Blocks(
            title="小说转视频 - 混合方案",
            theme=gr.themes.Soft(),
            css=self._get_custom_css()
        ) as app:
            gr.Markdown("# 📚 小说转视频生成系统")
            gr.Markdown("*基于混合方案: 本地LLM + 本地图像 + 远端视频API + 本地TTS*")

            with gr.Tabs() as tabs:
                # Tab 1: 项目管理
                with gr.Tab("📁 项目管理", id="project"):
                    self._create_project_tab()

                # Tab 2: 分镜编辑
                with gr.Tab("🎬 分镜编辑", id="storyboard"):
                    self._create_storyboard_tab()

                # Tab 3: 角色管理
                with gr.Tab("👤 角色管理", id="characters"):
                    self._create_characters_tab()

                # Tab 4: 生成控制
                with gr.Tab("⚙️ 生成控制", id="generation"):
                    self._create_generation_tab()

                # Tab 5: 预览
                with gr.Tab("👁️ 预览", id="preview"):
                    self._create_preview_tab()

                # Tab 6: 设置
                with gr.Tab("🔧 设置", id="settings"):
                    self._create_settings_tab()

        return app

    def _create_project_tab(self):
        """项目管理标签页"""
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 创建新项目")
                project_name = gr.Textbox(label="项目名称", placeholder="输入项目名称")
                novel_file = gr.File(label="上传小说文件 (.txt)", file_types=[".txt"])
                video_style = gr.Dropdown(
                    label="视频风格",
                    choices=["anime", "realistic", "illustration", "chinese_fantasy"],
                    value="anime"
                )
                create_btn = gr.Button("创建项目", variant="primary")
                create_status = gr.Textbox(label="状态", interactive=False)

            with gr.Column(scale=1):
                gr.Markdown("### 打开已有项目")
                project_list = gr.Dropdown(
                    label="选择项目",
                    choices=self._get_project_list(),
                    interactive=True
                )
                refresh_btn = gr.Button("刷新列表")
                open_btn = gr.Button("打开项目")
                project_info = gr.JSON(label="项目信息")

        # 事件绑定
        create_btn.click(
            fn=self._create_project,
            inputs=[project_name, novel_file, video_style],
            outputs=[create_status, project_list]
        )
        refresh_btn.click(
            fn=lambda: gr.update(choices=self._get_project_list()),
            outputs=[project_list]
        )
        open_btn.click(
            fn=self._open_project,
            inputs=[project_list],
            outputs=[project_info]
        )

    def _create_storyboard_tab(self):
        """分镜编辑标签页"""
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### 分镜列表")
                scene_list = gr.Dataframe(
                    headers=["ID", "时长", "描述", "状态"],
                    label="场景列表",
                    interactive=False
                )
                load_scenes_btn = gr.Button("加载分镜")

            with gr.Column(scale=3):
                gr.Markdown("### 场景编辑")
                scene_id = gr.Textbox(label="场景ID", interactive=False)
                scene_duration = gr.Slider(label="时长(秒)", minimum=3, maximum=10, step=0.5, value=5)
                scene_description = gr.Textbox(label="视觉描述", lines=3)
                scene_dialogue = gr.Textbox(label="对话/旁白", lines=2)
                scene_camera = gr.Dropdown(
                    label="镜头类型",
                    choices=["static", "slow_zoom_in", "slow_zoom_out", "pan_left", "pan_right"]
                )

                with gr.Row():
                    save_scene_btn = gr.Button("保存修改")
                    regenerate_btn = gr.Button("重新生成", variant="secondary")

                scene_preview = gr.Image(label="场景预览")

        # 事件绑定
        load_scenes_btn.click(
            fn=self._load_scenes,
            outputs=[scene_list]
        )
        scene_list.select(
            fn=self._select_scene,
            outputs=[scene_id, scene_duration, scene_description, scene_dialogue, scene_camera, scene_preview]
        )
        save_scene_btn.click(
            fn=self._save_scene,
            inputs=[scene_id, scene_duration, scene_description, scene_dialogue, scene_camera],
            outputs=[scene_list]
        )

    def _create_characters_tab(self):
        """角色管理标签页"""
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 角色列表")
                char_list = gr.Dataframe(
                    headers=["ID", "名称", "性别", "音色"],
                    label="角色",
                    interactive=False
                )
                load_chars_btn = gr.Button("加载角色")

            with gr.Column(scale=2):
                gr.Markdown("### 角色编辑")
                char_id = gr.Textbox(label="角色ID", interactive=False)
                char_name = gr.Textbox(label="名称")
                char_appearance = gr.Textbox(label="外貌描述", lines=3)
                char_sd_prompt = gr.Textbox(label="SD提示词", lines=2)
                char_voice = gr.Dropdown(
                    label="音色",
                    choices=["male_heroic", "male_gentle", "female_gentle", "female_sweet"]
                )

                with gr.Row():
                    save_char_btn = gr.Button("保存修改")
                    gen_char_btn = gr.Button("重新生成立绘", variant="secondary")
                    preview_voice_btn = gr.Button("试听音色")

                with gr.Row():
                    char_images = gr.Gallery(label="角色立绘", columns=4)
                    voice_preview = gr.Audio(label="音色预览")

        # 事件绑定
        load_chars_btn.click(fn=self._load_characters, outputs=[char_list])

    def _create_generation_tab(self):
        """生成控制标签页"""
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### 服务状态")
                service_status = gr.JSON(label="本地服务")
                check_services_btn = gr.Button("检查服务")

                gr.Markdown("### 生成控制")
                phase_selector = gr.Dropdown(
                    label="选择阶段",
                    choices=[
                        ("完整流程", "full"),
                        ("仅分析", "analyze"),
                        ("仅角色设计", "character_design"),
                        ("仅图像生成", "generate_images"),
                        ("仅音频生成", "generate_audio"),
                        ("仅视频生成", "generate_video"),
                        ("仅合成", "compose")
                    ],
                    value="full"
                )
                resume_checkbox = gr.Checkbox(label="断点续传", value=True)

                with gr.Row():
                    start_btn = gr.Button("开始生成", variant="primary")
                    stop_btn = gr.Button("停止", variant="stop")

            with gr.Column(scale=3):
                gr.Markdown("### 进度")
                progress_bar = gr.Progress()
                current_phase = gr.Textbox(label="当前阶段", interactive=False)
                current_task = gr.Textbox(label="当前任务", interactive=False)
                log_output = gr.Textbox(label="日志", lines=15, interactive=False)

        # 事件绑定
        check_services_btn.click(fn=self._check_services, outputs=[service_status])
        start_btn.click(
            fn=self._start_generation,
            inputs=[phase_selector, resume_checkbox],
            outputs=[current_phase, current_task, log_output]
        )

    def _create_preview_tab(self):
        """预览标签页"""
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 预览选项")
                preview_type = gr.Radio(
                    label="预览类型",
                    choices=["单场景", "章节", "完整视频"],
                    value="单场景"
                )
                scene_selector = gr.Dropdown(label="选择场景")
                refresh_preview_btn = gr.Button("刷新")

            with gr.Column(scale=3):
                gr.Markdown("### 视频预览")
                video_preview = gr.Video(label="预览")
                audio_preview = gr.Audio(label="音频")

                with gr.Row():
                    image_preview = gr.Image(label="场景图像")
                    subtitle_preview = gr.Textbox(label="字幕", lines=2)

        # 事件绑定
        refresh_preview_btn.click(
            fn=self._refresh_preview,
            inputs=[preview_type, scene_selector],
            outputs=[video_preview, audio_preview, image_preview, subtitle_preview]
        )

    def _create_settings_tab(self):
        """设置标签页"""
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 本地服务配置")
                ollama_url = gr.Textbox(label="Ollama URL", value=self.config.local.ollama_url)
                ollama_model = gr.Textbox(label="Ollama模型", value=self.config.local.ollama_model)
                comfyui_url = gr.Textbox(label="ComfyUI URL", value=self.config.local.comfyui_url)
                cosyvoice_url = gr.Textbox(label="CosyVoice URL", value=self.config.local.cosyvoice_url)

            with gr.Column():
                gr.Markdown("### API配置")
                video_provider = gr.Dropdown(
                    label="视频API提供商",
                    choices=["jimeng", "kling"],
                    value=self.config.api.video_provider
                )
                video_api_key = gr.Textbox(label="API密钥", type="password")
                use_idle_time = gr.Checkbox(label="使用闲时折扣", value=self.config.api.use_idle_time)

            with gr.Column():
                gr.Markdown("### 视频参数")
                resolution = gr.Dropdown(
                    label="分辨率",
                    choices=["1280x720", "1920x1080", "720x1280"],
                    value=self.config.video.resolution
                )
                fps = gr.Slider(label="帧率", minimum=24, maximum=60, step=1, value=self.config.video.fps)

        save_settings_btn = gr.Button("保存设置", variant="primary")
        settings_status = gr.Textbox(label="状态", interactive=False)

        save_settings_btn.click(
            fn=self._save_settings,
            inputs=[ollama_url, ollama_model, comfyui_url, cosyvoice_url,
                   video_provider, video_api_key, use_idle_time, resolution, fps],
            outputs=[settings_status]
        )

    # 回调函数实现
    def _get_project_list(self) -> List[str]:
        """获取项目列表"""
        projects_dir = Path(self.config.paths.projects_dir)
        if not projects_dir.exists():
            return []
        return [p.name for p in projects_dir.iterdir() if p.is_dir()]

    def _create_project(
        self,
        name: str,
        novel_file,
        style: str
    ) -> Tuple[str, gr.update]:
        """创建新项目"""
        if not name:
            return "错误: 请输入项目名称", gr.update()

        project_path = Path(self.config.paths.projects_dir) / name
        if project_path.exists():
            return f"错误: 项目 {name} 已存在", gr.update()

        try:
            # 创建目录结构
            ensure_dir(project_path / "input")
            ensure_dir(project_path / "characters")
            ensure_dir(project_path / "images")
            ensure_dir(project_path / "videos")
            ensure_dir(project_path / "audio")
            ensure_dir(project_path / "output")

            # 复制小说文件
            if novel_file:
                novel_path = project_path / "input" / "novel.txt"
                with open(novel_path, "wb") as f:
                    f.write(novel_file)

            # 创建项目配置
            project_config = {
                "project": {"name": name},
                "video": {"style": style},
                "local": {
                    "ollama_url": self.config.local.ollama_url,
                    "ollama_model": self.config.local.ollama_model,
                    "comfyui_url": self.config.local.comfyui_url,
                    "cosyvoice_url": self.config.local.cosyvoice_url
                }
            }
            with open(project_path / "project.yaml", "w", encoding="utf-8") as f:
                import yaml
                yaml.dump(project_config, f, allow_unicode=True)

            self.current_project = project_path
            return f"项目 {name} 创建成功!", gr.update(choices=self._get_project_list())

        except Exception as e:
            return f"创建失败: {e}", gr.update()

    def _open_project(self, project_name: str) -> Dict[str, Any]:
        """打开项目"""
        if not project_name:
            return {"error": "请选择项目"}

        project_path = Path(self.config.paths.projects_dir) / project_name
        if not project_path.exists():
            return {"error": f"项目不存在: {project_name}"}

        self.current_project = project_path
        self.pipeline = PipelineController(project_path, self.config)

        # 加载项目信息
        info = {
            "name": project_name,
            "path": str(project_path),
            "has_novel": (project_path / "input" / "novel.txt").exists(),
            "has_storyboard": (project_path / "storyboard.json").exists(),
            "has_characters": (project_path / "characters.json").exists(),
        }

        # 加载状态
        state_file = project_path / "pipeline_state.json"
        if state_file.exists():
            state = PipelineState.load(state_file)
            info["phase"] = state.current_phase.value
            info["progress"] = state.get_progress()

        return info

    def _load_scenes(self) -> List[List[str]]:
        """加载分镜列表"""
        if not self.current_project:
            return []

        storyboard_path = self.current_project / "storyboard.json"
        if not storyboard_path.exists():
            return []

        storyboard = load_json(storyboard_path)
        scenes = storyboard.get("scenes", [])

        return [
            [
                s["id"],
                f"{s.get('duration', 5)}s",
                s.get("visual", {}).get("description", "")[:50] + "...",
                s.get("generation_status", {}).get("image", "pending")
            ]
            for s in scenes
        ]

    def _load_characters(self) -> List[List[str]]:
        """加载角色列表"""
        if not self.current_project:
            return []

        chars_path = self.current_project / "characters.json"
        if not chars_path.exists():
            return []

        characters = load_json(chars_path)
        char_list = characters.get("characters", [])

        return [
            [
                c["id"],
                c.get("name", "未知"),
                c.get("appearance", {}).get("gender", "unknown"),
                c.get("voice", {}).get("voice_id", "default")
            ]
            for c in char_list
        ]

    def _check_services(self) -> Dict[str, Any]:
        """检查服务状态"""
        status = {}

        # 检查Ollama
        try:
            llm = OllamaClient(base_url=self.config.local.ollama_url)
            status["ollama"] = "✅ 可用" if llm.check_health() else "❌ 不可用"
        except:
            status["ollama"] = "❌ 连接失败"

        # 检查ComfyUI
        try:
            comfyui = ComfyUIClient(base_url=self.config.local.comfyui_url)
            status["comfyui"] = "✅ 可用" if comfyui.check_health() else "❌ 不可用"
        except:
            status["comfyui"] = "❌ 连接失败"

        # 检查CosyVoice
        try:
            tts = CosyVoiceClient(base_url=self.config.local.cosyvoice_url)
            status["cosyvoice"] = "✅ 可用" if tts.check_health() else "❌ 不可用"
        except:
            status["cosyvoice"] = "❌ 连接失败"

        return status

    def _start_generation(
        self,
        phase: str,
        resume: bool
    ) -> Tuple[str, str, str]:
        """开始生成"""
        if not self.current_project:
            return "错误", "请先打开项目", ""

        if self.is_running:
            return "运行中", "已有任务在执行", ""

        self.is_running = True
        logs = []

        try:
            self.pipeline = PipelineController(self.current_project, self.config)

            def progress_callback(stage: str, detail: str, progress: float):
                logs.append(f"[{stage}] {detail}")

            self.pipeline.on_progress = progress_callback

            if phase == "full":
                self.pipeline.run(resume=resume)
            else:
                phase_enum = Phase(phase)
                self.pipeline.run_phase(phase_enum)

            return "完成", "生成任务完成", "\n".join(logs[-20:])

        except Exception as e:
            return "错误", str(e), "\n".join(logs[-20:])

        finally:
            self.is_running = False

    def _save_settings(self, *args) -> str:
        """保存设置"""
        # TODO: 实现设置保存
        return "设置已保存"

    def _select_scene(self, evt: gr.SelectData):
        """选择场景"""
        # TODO: 实现场景选择
        pass

    def _save_scene(self, *args):
        """保存场景"""
        # TODO: 实现场景保存
        pass

    def _refresh_preview(self, *args):
        """刷新预览"""
        # TODO: 实现预览刷新
        pass

    def _get_custom_css(self) -> str:
        """自定义CSS"""
        return """
        .gradio-container {
            max-width: 1400px !important;
        }
        """


def create_app() -> gr.Blocks:
    """创建应用实例"""
    app = NovelVideoApp()
    return app.create_ui()


def launch(
    server_name: str = "127.0.0.1",
    server_port: int = 7860,
    share: bool = False
):
    """启动Web界面"""
    app = create_app()
    app.launch(
        server_name=server_name,
        server_port=server_port,
        share=share
    )


if __name__ == "__main__":
    launch()
