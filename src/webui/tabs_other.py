"""
WebUI 标签页组件 - 生成控制、预览、设置
"""
import gradio as gr
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

from ..utils.logger import get_logger

logger = get_logger(__name__)


class CharactersTab:
    """角色管理标签页"""

    def __init__(self, app: "NovelVideoApp"):
        self.app = app

    def create(self) -> None:
        """创建角色管理标签页"""
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 角色列表")
                self.char_list = gr.Dataframe(
                    headers=["ID", "名称", "性别", "音色"],
                    label="角色",
                    interactive=False,
                )
                self.load_chars_btn = gr.Button("加载角色")

            with gr.Column(scale=2):
                gr.Markdown("### 角色编辑")
                self.char_id = gr.Textbox(label="角色ID", interactive=False)
                self.char_name = gr.Textbox(label="名称")
                self.char_appearance = gr.Textbox(label="外貌描述", lines=3)
                self.char_sd_prompt = gr.Textbox(label="SD提示词", lines=2)
                self.char_voice = gr.Dropdown(
                    label="音色",
                    choices=["male_heroic", "male_gentle", "female_gentle", "female_sweet"],
                )

                with gr.Row():
                    self.save_char_btn = gr.Button("保存修改")
                    self.gen_char_btn = gr.Button("重新生成立绘", variant="secondary")
                    self.preview_voice_btn = gr.Button("试听音色")

                with gr.Row():
                    self.char_images = gr.Gallery(label="角色立绘", columns=4)
                    self.voice_preview = gr.Audio(label="音色预览")

        self._bind_events()

    def _bind_events(self) -> None:
        """绑定事件"""
        self.load_chars_btn.click(fn=self.app.load_characters, outputs=[self.char_list])


class GenerationTab:
    """生成控制标签页"""

    def __init__(self, app: "NovelVideoApp"):
        self.app = app

    def create(self) -> None:
        """创建生成控制标签页"""
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### 服务状态")
                self.service_status = gr.JSON(label="本地服务")
                self.check_services_btn = gr.Button("检查服务")

                gr.Markdown("### 生成控制")
                self.phase_selector = gr.Dropdown(
                    label="选择阶段",
                    choices=[
                        ("完整流程", "full"),
                        ("仅分析", "analyze"),
                        ("仅角色设计", "character_design"),
                        ("仅图像生成", "generate_images"),
                        ("仅音频生成", "generate_audio"),
                        ("仅视频生成", "generate_video"),
                        ("仅合成", "compose"),
                    ],
                    value="full",
                )
                self.resume_checkbox = gr.Checkbox(label="断点续传", value=True)
                self.skip_failed_checkbox = gr.Checkbox(label="跳过失败场景继续执行", value=True)

                with gr.Accordion("高级选项", open=False):
                    self.failure_threshold = gr.Slider(
                        label="失败阈值 (%)",
                        minimum=10,
                        maximum=100,
                        step=5,
                        value=50,
                        info="失败率超过此阈值时停止执行",
                    )

                with gr.Row():
                    self.start_btn = gr.Button("开始生成", variant="primary")
                    self.stop_btn = gr.Button("停止", variant="stop")

            with gr.Column(scale=3):
                gr.Markdown("### 进度")
                self.progress_bar = gr.Progress()
                self.current_phase = gr.Textbox(label="当前阶段", interactive=False)
                self.current_task = gr.Textbox(label="当前任务", interactive=False)
                self.log_output = gr.Textbox(label="日志", lines=15, interactive=False)

        self._bind_events()

    def _bind_events(self) -> None:
        """绑定事件"""
        self.check_services_btn.click(
            fn=self.app.check_services, outputs=[self.service_status]
        )
        self.start_btn.click(
            fn=self.app.start_generation,
            inputs=[
                self.phase_selector,
                self.resume_checkbox,
                self.skip_failed_checkbox,
                self.failure_threshold,
            ],
            outputs=[self.current_phase, self.current_task, self.log_output],
        )


class PreviewTab:
    """预览标签页"""

    def __init__(self, app: "NovelVideoApp"):
        self.app = app

    def create(self) -> None:
        """创建预览标签页"""
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 预览选项")
                self.preview_type = gr.Radio(
                    label="预览类型",
                    choices=["单场景", "章节", "完整视频"],
                    value="单场景",
                )
                self.scene_selector = gr.Dropdown(
                    label="选择场景", choices=[], interactive=True, visible=True
                )
                self.chapter_selector = gr.Dropdown(
                    label="选择章节", choices=[], interactive=True, visible=False
                )
                self.load_scenes_preview_btn = gr.Button("加载列表")
                self.refresh_preview_btn = gr.Button("刷新预览", variant="primary")

                gr.Markdown("### 章节信息")
                self.chapter_info = gr.JSON(label="章节概览", visible=False)

            with gr.Column(scale=3):
                gr.Markdown("### 视频预览")
                self.video_preview = gr.Video(label="预览")
                self.audio_preview = gr.Audio(label="音频")

                with gr.Row():
                    self.image_preview = gr.Image(label="场景图像")
                    self.subtitle_preview = gr.Textbox(label="字幕", lines=2, interactive=False)

                self.chapter_scenes_gallery = gr.Gallery(
                    label="章节场景预览", columns=4, visible=False, show_label=True
                )

        self._bind_events()

    def _bind_events(self) -> None:
        """绑定事件"""

        def toggle_selectors(ptype):
            if ptype == "单场景":
                return (
                    gr.update(visible=True),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                )
            elif ptype == "章节":
                return (
                    gr.update(visible=False),
                    gr.update(visible=True),
                    gr.update(visible=True),
                    gr.update(visible=True),
                )
            else:
                return (
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                )

        self.preview_type.change(
            fn=toggle_selectors,
            inputs=[self.preview_type],
            outputs=[
                self.scene_selector,
                self.chapter_selector,
                self.chapter_info,
                self.chapter_scenes_gallery,
            ],
        )
        self.load_scenes_preview_btn.click(
            fn=self.app.load_preview_lists,
            inputs=[self.preview_type],
            outputs=[self.scene_selector, self.chapter_selector],
        )
        self.refresh_preview_btn.click(
            fn=self.app.refresh_preview,
            inputs=[self.preview_type, self.scene_selector, self.chapter_selector],
            outputs=[
                self.video_preview,
                self.audio_preview,
                self.image_preview,
                self.subtitle_preview,
                self.chapter_info,
                self.chapter_scenes_gallery,
            ],
        )


class SettingsTab:
    """设置标签页"""

    def __init__(self, app: "NovelVideoApp"):
        self.app = app
        self.config = app.config

    def create(self) -> None:
        """创建设置标签页"""
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 本地服务配置")
                self.ollama_url = gr.Textbox(
                    label="Ollama URL", value=self.config.local.ollama_url
                )
                self.ollama_model = gr.Textbox(
                    label="Ollama模型", value=self.config.local.ollama_model
                )
                self.comfyui_url = gr.Textbox(
                    label="ComfyUI URL", value=self.config.local.comfyui_url
                )
                self.cosyvoice_url = gr.Textbox(
                    label="CosyVoice URL", value=self.config.local.cosyvoice_url
                )

            with gr.Column():
                gr.Markdown("### API配置")
                self.video_provider = gr.Dropdown(
                    label="视频API提供商",
                    choices=["jimeng", "kling"],
                    value=self.config.api.video_provider,
                )
                self.video_api_key = gr.Textbox(label="API密钥", type="password")
                self.use_idle_time = gr.Checkbox(
                    label="使用闲时折扣", value=self.config.api.use_idle_time
                )

            with gr.Column():
                gr.Markdown("### 视频参数")
                self.resolution = gr.Dropdown(
                    label="分辨率",
                    choices=["1280x720", "1920x1080", "720x1280"],
                    value=self.config.video.resolution,
                )
                self.fps = gr.Slider(
                    label="帧率", minimum=24, maximum=60, step=1, value=self.config.video.fps
                )

        self.save_settings_btn = gr.Button("保存设置", variant="primary")
        self.settings_status = gr.Textbox(label="状态", interactive=False)

        self._bind_events()

    def _bind_events(self) -> None:
        """绑定事件"""
        self.save_settings_btn.click(
            fn=self.app.save_settings,
            inputs=[
                self.ollama_url,
                self.ollama_model,
                self.comfyui_url,
                self.cosyvoice_url,
                self.video_provider,
                self.video_api_key,
                self.use_idle_time,
                self.resolution,
                self.fps,
            ],
            outputs=[self.settings_status],
        )
