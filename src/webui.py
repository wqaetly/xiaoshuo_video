"""
小说转视频 - Gradio Web界面
提供可视化的项目管理、预览和调整功能
"""
import gradio as gr
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import json
import threading
import time

from .pipeline import PipelineController, Phase, PipelineState
from .llm import OllamaClient, StoryboardGenerator, CharacterExtractor
from .image import ComfyUIClient
from .tts import CosyVoiceClient
from .utils.config import get_config, Config
from .utils.file_utils import load_json, save_json, ensure_dir
from .utils.logger import get_logger
from .webui_enhanced import (
    RealtimeLogHandler,
    TaskQueue,
    BatchOperations,
    get_log_handler,
    get_task_queue,
    LogLevel,
    TaskStatus,
)

logger = get_logger(__name__)


class NovelVideoApp:
    """小说转视频Web应用"""

    def __init__(self):
        self.config = get_config()
        self.current_project: Optional[Path] = None
        self.pipeline: Optional[PipelineController] = None
        self.is_running = False
        
        # 增强功能
        self.log_handler = get_log_handler()
        self.task_queue = get_task_queue()
        self.batch_ops: Optional[BatchOperations] = None
        
        # 注册任务处理器
        self._register_task_handlers()

    def create_ui(self) -> gr.Blocks:
        """创建Gradio界面"""
        with gr.Blocks(
            title="小说转视频 - 混合方案",
            theme=gr.themes.Soft(),
            css=self._get_custom_css(),
            js=self._get_drag_sort_js(),
            fill_width=True
        ) as app:
            gr.Markdown("# 📚 小说转视频生成系统")
            gr.Markdown("*基于混合方案: 本地LLM + 本地图像 + 远端视频API + 本地TTS*")

            with gr.Tabs(elem_id="main-tabs") as tabs:
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

                # Tab 7: 任务队列 (新增)
                with gr.Tab("📋 任务队列", id="tasks"):
                    self._create_tasks_tab()

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
                
                # 搜索和筛选区域
                with gr.Group():
                    gr.Markdown("#### 🔍 搜索与筛选")
                    with gr.Row():
                        scene_search_input = gr.Textbox(
                            label="搜索",
                            placeholder="输入场景ID、描述或对话关键词...",
                            scale=3
                        )
                        search_btn = gr.Button("搜索", scale=1, size="sm")
                    
                    with gr.Row():
                        filter_status = gr.Dropdown(
                            label="状态筛选",
                            choices=["全部", "待处理", "已完成", "失败"],
                            value="全部",
                            scale=1
                        )
                        filter_chapter = gr.Dropdown(
                            label="章节筛选",
                            choices=["全部章节"],
                            value="全部章节",
                            scale=1
                        )
                        clear_filter_btn = gr.Button("清除筛选", scale=1, size="sm")
                    
                    filter_result_info = gr.Markdown("", elem_id="filter-result-info")
                
                # 可拖拽排序的场景列表
                sortable_scene_list = gr.HTML(
                    value='<div class="scene-list-empty">点击「加载分镜」按钮加载场景</div>',
                    elem_id="sortable-scene-list"
                )
                
                # 隐藏的状态存储
                scene_order_state = gr.Textbox(visible=False, elem_id="scene-order-state")
                
                with gr.Row():
                    load_scenes_btn = gr.Button("加载分镜", variant="primary")
                    save_order_btn = gr.Button("保存排序", variant="secondary")
                
                order_status = gr.Textbox(label="操作结果", interactive=False)
                
                # 保留原有Dataframe用于数据展示(可折叠)
                with gr.Accordion("详细数据表格", open=False):
                    scene_list = gr.Dataframe(
                        headers=["序号", "ID", "时长", "描述", "状态"],
                        label="场景列表",
                        interactive=False
                    )

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
            fn=self._load_scenes_html_with_filter,
            inputs=[scene_search_input, filter_status, filter_chapter],
            outputs=[sortable_scene_list, scene_list, scene_order_state, filter_result_info, filter_chapter]
        )
        
        # 搜索按钮
        search_btn.click(
            fn=self._load_scenes_html_with_filter,
            inputs=[scene_search_input, filter_status, filter_chapter],
            outputs=[sortable_scene_list, scene_list, scene_order_state, filter_result_info, filter_chapter]
        )
        
        # 搜索框回车触发搜索
        scene_search_input.submit(
            fn=self._load_scenes_html_with_filter,
            inputs=[scene_search_input, filter_status, filter_chapter],
            outputs=[sortable_scene_list, scene_list, scene_order_state, filter_result_info, filter_chapter]
        )
        
        # 状态筛选变化
        filter_status.change(
            fn=self._load_scenes_html_with_filter,
            inputs=[scene_search_input, filter_status, filter_chapter],
            outputs=[sortable_scene_list, scene_list, scene_order_state, filter_result_info, filter_chapter]
        )
        
        # 章节筛选变化
        filter_chapter.change(
            fn=self._load_scenes_html_with_filter,
            inputs=[scene_search_input, filter_status, filter_chapter],
            outputs=[sortable_scene_list, scene_list, scene_order_state, filter_result_info, filter_chapter]
        )
        
        # 清除筛选
        clear_filter_btn.click(
            fn=self._clear_scene_filter,
            outputs=[scene_search_input, filter_status, filter_chapter, sortable_scene_list, scene_list, scene_order_state, filter_result_info]
        )
        
        # 保存拖拽后的排序
        save_order_btn.click(
            fn=self._save_scene_order,
            inputs=[scene_order_state],
            outputs=[sortable_scene_list, scene_list, order_status, scene_order_state]
        )
        
        # 点击场景项触发选择
        sortable_scene_list.change(
            fn=self._on_scene_html_click,
            inputs=[sortable_scene_list],
            outputs=[scene_id, scene_duration, scene_description, scene_dialogue, scene_camera, scene_preview]
        )
        
        save_scene_btn.click(
            fn=self._save_scene,
            inputs=[scene_id, scene_duration, scene_description, scene_dialogue, scene_camera],
            outputs=[scene_list]
        ).then(
            fn=self._load_scenes_html_with_filter,
            inputs=[scene_search_input, filter_status, filter_chapter],
            outputs=[sortable_scene_list, scene_list, scene_order_state, filter_result_info, filter_chapter]
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
                skip_failed_checkbox = gr.Checkbox(label="跳过失败场景继续执行", value=True)
                
                with gr.Accordion("高级选项", open=False):
                    failure_threshold = gr.Slider(
                        label="失败阈值 (%)",
                        minimum=10,
                        maximum=100,
                        step=5,
                        value=50,
                        info="失败率超过此阈值时停止执行"
                    )

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
            inputs=[phase_selector, resume_checkbox, skip_failed_checkbox, failure_threshold],
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
                scene_selector = gr.Dropdown(label="选择场景", choices=[], interactive=True, visible=True)
                chapter_selector = gr.Dropdown(label="选择章节", choices=[], interactive=True, visible=False)
                load_scenes_preview_btn = gr.Button("加载列表")
                refresh_preview_btn = gr.Button("刷新预览", variant="primary")
                
                gr.Markdown("### 章节信息")
                chapter_info = gr.JSON(label="章节概览", visible=False)

            with gr.Column(scale=3):
                gr.Markdown("### 视频预览")
                video_preview = gr.Video(label="预览")
                audio_preview = gr.Audio(label="音频")

                with gr.Row():
                    image_preview = gr.Image(label="场景图像")
                    subtitle_preview = gr.Textbox(label="字幕", lines=2, interactive=False)
                    
                # 章节预览时的场景列表
                chapter_scenes_gallery = gr.Gallery(
                    label="章节场景预览",
                    columns=4,
                    visible=False,
                    show_label=True
                )

        # 根据预览类型切换显示
        def toggle_selectors(ptype):
            if ptype == "单场景":
                return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)
            elif ptype == "章节":
                return gr.update(visible=False), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True)
            else:
                return gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)
        
        preview_type.change(
            fn=toggle_selectors,
            inputs=[preview_type],
            outputs=[scene_selector, chapter_selector, chapter_info, chapter_scenes_gallery]
        )
        
        # 事件绑定
        load_scenes_preview_btn.click(
            fn=self._load_preview_lists,
            inputs=[preview_type],
            outputs=[scene_selector, chapter_selector]
        )
        refresh_preview_btn.click(
            fn=self._refresh_preview,
            inputs=[preview_type, scene_selector, chapter_selector],
            outputs=[video_preview, audio_preview, image_preview, subtitle_preview, chapter_info, chapter_scenes_gallery]
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

    def _create_tasks_tab(self):
        """任务队列标签页"""
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### 任务队列")
                task_table = gr.Dataframe(
                    headers=["ID", "名称", "类型", "状态", "进度", "消息"],
                    label="任务列表",
                    interactive=False
                )
                
                with gr.Row():
                    refresh_tasks_btn = gr.Button("刷新", size="sm")
                    clear_completed_btn = gr.Button("清除已完成", size="sm")
                    cancel_all_btn = gr.Button("取消全部", variant="stop", size="sm")
                
                queue_status = gr.JSON(label="队列状态")

            with gr.Column(scale=3):
                gr.Markdown("### 实时日志")
                realtime_log = gr.Textbox(
                    label="",
                    lines=20,
                    interactive=False,
                    show_label=False,
                    elem_id="realtime-log"
                )
                
                with gr.Row():
                    auto_refresh = gr.Checkbox(label="自动刷新", value=True)
                    refresh_interval = gr.Slider(label="刷新间隔(秒)", minimum=0.5, maximum=5, step=0.5, value=1)
                    clear_log_btn = gr.Button("清空日志", size="sm")
                
                # WebSocket状态指示
                ws_status = gr.Markdown("🔴 轮询模式 (WebSocket未连接)", elem_id="ws-status")
                
                gr.Markdown("### 批量操作")
                with gr.Row():
                    batch_scene_ids = gr.Textbox(
                        label="场景ID列表 (逗号分隔)",
                        placeholder="scene_01_001, scene_01_002, ..."
                    )
                
                with gr.Row():
                    batch_regen_image = gr.Checkbox(label="重新生成图像", value=True)
                    batch_regen_audio = gr.Checkbox(label="重新生成音频", value=False)
                    batch_regen_video = gr.Checkbox(label="重新生成视频", value=False)
                
                with gr.Row():
                    batch_regenerate_btn = gr.Button("批量重新生成", variant="primary")
                    batch_delete_btn = gr.Button("批量删除", variant="stop")
                    batch_reset_status_btn = gr.Button("重置状态为待处理")
                
                batch_result = gr.Textbox(label="操作结果", interactive=False)

        # 事件绑定
        refresh_tasks_btn.click(
            fn=self._refresh_task_list,
            outputs=[task_table, queue_status]
        )
        clear_completed_btn.click(
            fn=self._clear_completed_tasks,
            outputs=[task_table, queue_status, batch_result]
        )
        clear_log_btn.click(
            fn=self._clear_logs,
            outputs=[realtime_log]
        )
        batch_regenerate_btn.click(
            fn=self._batch_regenerate,
            inputs=[batch_scene_ids, batch_regen_image, batch_regen_audio, batch_regen_video],
            outputs=[batch_result, task_table, queue_status]
        )
        batch_delete_btn.click(
            fn=self._batch_delete_scenes,
            inputs=[batch_scene_ids],
            outputs=[batch_result]
        )
        batch_reset_status_btn.click(
            fn=self._batch_reset_status,
            inputs=[batch_scene_ids],
            outputs=[batch_result]
        )
        
        # 自动刷新日志 - 基于配置的刷新间隔
        def auto_refresh_logs(auto_on, interval):
            if auto_on:
                return self._get_recent_logs()
            return gr.update()
        
        # 使用定时器进行日志刷新
        realtime_log.change(
            fn=lambda: self._get_recent_logs(),
            outputs=[realtime_log],
            every=1,
            trigger_mode="always_last"
        )

    def _register_task_handlers(self):
        """注册任务处理器"""
        self.task_queue.register_handler("regenerate_image", self._handle_regenerate_image)
        self.task_queue.register_handler("regenerate_audio", self._handle_regenerate_audio)
        self.task_queue.register_handler("regenerate_video", self._handle_regenerate_video)
        
        def on_progress(task_id: str, progress: float, message: str):
            self.log_handler.info("Task", f"{task_id}: {progress*100:.0f}% - {message}")
        
        def on_complete(task_id: str, success: bool, message: str):
            level = LogLevel.INFO if success else LogLevel.ERROR
            self.log_handler.add_log(level, "Task", f"{task_id}: {'完成' if success else '失败'} - {message}")
        
        self.task_queue.set_callbacks(on_progress, on_complete)

    def _handle_regenerate_image(self, params: Dict, progress_cb) -> Any:
        """处理图像重新生成任务"""
        scene_id = params.get("scene_id")
        if not self.current_project or not scene_id:
            raise ValueError("项目未打开或场景ID无效")
        
        progress_cb(0.1, "加载场景数据...")
        storyboard = load_json(self.current_project / "storyboard.json")
        characters = load_json(self.current_project / "characters.json")
        
        scene = None
        for s in storyboard.get("scenes", []):
            if s.get("id") == scene_id:
                scene = s
                break
        
        if not scene:
            raise ValueError(f"场景不存在: {scene_id}")
        
        progress_cb(0.3, "初始化图像生成器...")
        from .image import ComfyUIClient, SceneGenerator
        comfyui = ComfyUIClient(base_url=self.config.local.comfyui_url)
        image_gen = SceneGenerator(comfyui)
        
        progress_cb(0.5, "生成图像...")
        image = image_gen.generate_scene(scene, characters, style_preset=self.config.video.style)
        
        progress_cb(0.9, "保存图像...")
        image.save(self.current_project / "images" / f"{scene_id}.png")
        
        return {"scene_id": scene_id, "success": True}

    def _handle_regenerate_audio(self, params: Dict, progress_cb) -> Any:
        """处理音频重新生成任务"""
        scene_id = params.get("scene_id")
        if not self.current_project or not scene_id:
            raise ValueError("项目未打开或场景ID无效")
        
        progress_cb(0.1, "加载场景数据...")
        storyboard = load_json(self.current_project / "storyboard.json")
        characters = load_json(self.current_project / "characters.json")
        
        scene = None
        for s in storyboard.get("scenes", []):
            if s.get("id") == scene_id:
                scene = s
                break
        
        if not scene:
            raise ValueError(f"场景不存在: {scene_id}")
        
        progress_cb(0.3, "初始化TTS...")
        from .tts import create_tts_client
        tts = create_tts_client("edge")  # 使用Edge TTS作为默认
        
        progress_cb(0.5, "生成音频...")
        audio_data = tts.generate_scene_audio(scene.get("audio", {}), characters)
        
        progress_cb(0.9, "保存音频...")
        audio_data.save(self.current_project / "audio" / f"{scene_id}.wav")
        
        return {"scene_id": scene_id, "success": True}

    def _handle_regenerate_video(self, params: Dict, progress_cb) -> Any:
        """处理视频重新生成任务"""
        scene_id = params.get("scene_id")
        if not self.current_project or not scene_id:
            raise ValueError("项目未打开或场景ID无效")
        
        if not self.config.api.video_api_key:
            raise ValueError("视频API密钥未配置")
        
        progress_cb(0.1, "检查图像...")
        image_path = self.current_project / "images" / f"{scene_id}.png"
        if not image_path.exists():
            raise ValueError(f"场景图像不存在: {scene_id}")
        
        progress_cb(0.2, "加载场景数据...")
        storyboard = load_json(self.current_project / "storyboard.json")
        
        scene = None
        for s in storyboard.get("scenes", []):
            if s.get("id") == scene_id:
                scene = s
                break
        
        if not scene:
            raise ValueError(f"场景不存在: {scene_id}")
        
        progress_cb(0.3, "初始化视频API...")
        from .video import create_video_client
        video_client = create_video_client(
            provider=self.config.api.video_provider,
            api_key=self.config.api.video_api_key
        )
        
        progress_cb(0.4, "生成视频...")
        camera = scene.get("visual", {}).get("camera", {})
        motion_prompt = f"{camera.get('type', 'static')} camera movement"
        
        video_data = video_client.generate(
            image_path=image_path,
            motion_prompt=motion_prompt,
            duration=scene.get("duration", 5.0)
        )
        
        progress_cb(0.9, "保存视频...")
        video_data.save(self.current_project / "videos" / f"{scene_id}.mp4")
        
        return {"scene_id": scene_id, "success": True}

    def _refresh_task_list(self) -> Tuple[List[List[str]], Dict[str, Any]]:
        """刷新任务列表"""
        tasks = self.task_queue.get_all_tasks()
        table_data = [
            [
                t.task_id[:20],
                t.name[:30],
                t.task_type,
                t.status.value,
                f"{t.progress*100:.0f}%",
                t.message[:50] if t.message else (t.error[:50] if t.error else "")
            ]
            for t in tasks
        ]
        status = self.task_queue.get_queue_status()
        return table_data, status

    def _clear_completed_tasks(self) -> Tuple[List[List[str]], Dict[str, Any], str]:
        """清除已完成的任务"""
        removed = self.task_queue.clear_completed()
        table_data, status = self._refresh_task_list()
        return table_data, status, f"已清除 {removed} 个任务"

    def _clear_logs(self) -> str:
        """清空日志"""
        self.log_handler.clear()
        return ""

    def _get_recent_logs(self) -> str:
        """获取最近的日志"""
        logs = self.log_handler.get_recent(50)
        return "\n".join(logs)

    def _batch_regenerate(
        self,
        scene_ids_str: str,
        regen_image: bool,
        regen_audio: bool,
        regen_video: bool
    ) -> Tuple[str, List[List[str]], Dict[str, Any]]:
        """批量重新生成"""
        if not self.current_project:
            return "错误: 请先打开项目", [], {}
        
        if not scene_ids_str.strip():
            return "错误: 请输入场景ID", [], {}
        
        scene_ids = [s.strip() for s in scene_ids_str.split(",") if s.strip()]
        
        if not self.batch_ops:
            self.batch_ops = BatchOperations(self.task_queue, self.log_handler)
        
        task_ids = self.batch_ops.regenerate_scenes(
            scene_ids,
            regenerate_image=regen_image,
            regenerate_audio=regen_audio,
            regenerate_video=regen_video
        )
        
        # 启动任务队列
        self.task_queue.start()
        
        table_data, status = self._refresh_task_list()
        return f"已添加 {len(task_ids)} 个任务到队列", table_data, status

    def _batch_delete_scenes(self, scene_ids_str: str) -> str:
        """批量删除场景"""
        if not self.current_project:
            return "错误: 请先打开项目"
        
        if not scene_ids_str.strip():
            return "错误: 请输入场景ID"
        
        scene_ids = [s.strip() for s in scene_ids_str.split(",") if s.strip()]
        
        if not self.batch_ops:
            self.batch_ops = BatchOperations(self.task_queue, self.log_handler)
        
        storyboard_path = self.current_project / "storyboard.json"
        deleted = self.batch_ops.delete_scenes(scene_ids, storyboard_path)
        
        return f"已删除 {deleted} 个场景"

    def _batch_reset_status(self, scene_ids_str: str) -> str:
        """批量重置场景状态"""
        if not self.current_project:
            return "错误: 请先打开项目"
        
        if not scene_ids_str.strip():
            return "错误: 请输入场景ID"
        
        scene_ids = [s.strip() for s in scene_ids_str.split(",") if s.strip()]
        
        if not self.batch_ops:
            self.batch_ops = BatchOperations(self.task_queue, self.log_handler)
        
        storyboard_path = self.current_project / "storyboard.json"
        
        updated = 0
        for status_type in ["image", "audio", "video"]:
            updated += self.batch_ops.update_scene_status(
                scene_ids, status_type, "pending", storyboard_path
            )
        
        return f"已重置 {updated} 个状态"

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
                str(i),  # 序号
                s["id"],
                f"{s.get('duration', 5)}s",
                s.get("visual", {}).get("description", "")[:50] + "...",
                s.get("generation_status", {}).get("image", "pending")
            ]
            for i, s in enumerate(scenes)
        ]

    def _load_scenes_html(self) -> Tuple[str, List[List[str]], str]:
        """加载分镜列表为可拖拽HTML"""
        if not self.current_project:
            empty_html = "<div class='scene-list-empty'>请先打开项目</div>"
            return empty_html, [], ""

        storyboard_path = self.current_project / "storyboard.json"
        if not storyboard_path.exists():
            empty_html = "<div class='scene-list-empty'>暂无分镜数据</div>"
            return empty_html, [], ""

        storyboard = load_json(storyboard_path)
        scenes = storyboard.get("scenes", [])

        if not scenes:
            empty_html = "<div class='scene-list-empty'>暂无场景</div>"
            return empty_html, [], ""

        # 构建可拖拽的HTML列表
        html_items = []
        scene_ids = []
        for i, s in enumerate(scenes):
            scene_id = s.get("id", f"scene_{i}")
            scene_ids.append(scene_id)
            duration = s.get("duration", 5)
            desc = s.get("visual", {}).get("description", "")[:40]
            status = s.get("generation_status", {}).get("image", "pending")
            status_icon = {"pending": "⏳", "completed": "✅", "failed": "❌"}.get(status, "❓")
            
            # 检查是否有预览图
            image_path = self.current_project / "images" / f"{scene_id}.png"
            has_image = image_path.exists()
            thumb_style = f"background-image: url('file={image_path}');" if has_image else ""
            
            html_items.append(f'''
                <div class="scene-item" draggable="true" data-scene-id="{scene_id}" data-index="{i}">
                    <div class="scene-drag-handle">⋮⋮</div>
                    <div class="scene-index">{i}</div>
                    <div class="scene-thumb" style="{thumb_style}"></div>
                    <div class="scene-info">
                        <div class="scene-id">{scene_id}</div>
                        <div class="scene-desc">{desc}...</div>
                    </div>
                    <div class="scene-meta">
                        <span class="scene-duration">{duration}s</span>
                        <span class="scene-status">{status_icon}</span>
                    </div>
                </div>
            ''')

        html_content = f'''
            <div class="sortable-scene-container" id="scene-container">
                {"".join(html_items)}
            </div>
            <div class="drag-hint">💡 拖拽场景项可调整顺序，拖拽后点击"保存排序"</div>
        '''

        # Dataframe数据
        table_data = [
            [str(i), s["id"], f"{s.get('duration', 5)}s", 
             s.get("visual", {}).get("description", "")[:50] + "...",
             s.get("generation_status", {}).get("image", "pending")]
            for i, s in enumerate(scenes)
        ]

        return html_content, table_data, ",".join(scene_ids)

    def _load_scenes_html_with_filter(
        self,
        search_query: str = "",
        status_filter: str = "全部",
        chapter_filter: str = "全部章节"
    ) -> Tuple[str, List[List[str]], str, str, gr.update]:
        """加载分镜列表，支持搜索和筛选"""
        if not self.current_project:
            empty_html = "<div class='scene-list-empty'>请先打开项目</div>"
            return empty_html, [], "", "", gr.update(choices=["全部章节"], value="全部章节")

        storyboard_path = self.current_project / "storyboard.json"
        if not storyboard_path.exists():
            empty_html = "<div class='scene-list-empty'>暂无分镜数据</div>"
            return empty_html, [], "", "", gr.update(choices=["全部章节"], value="全部章节")

        storyboard = load_json(storyboard_path)
        all_scenes = storyboard.get("scenes", [])
        
        if not all_scenes:
            empty_html = "<div class='scene-list-empty'>暂无场景</div>"
            return empty_html, [], "", "", gr.update(choices=["全部章节"], value="全部章节")

        # 获取章节列表用于下拉框
        chapter_choices = self._extract_chapter_choices(all_scenes)
        
        # 应用筛选条件
        filtered_scenes = self._filter_scenes(
            all_scenes,
            search_query=search_query,
            status_filter=status_filter,
            chapter_filter=chapter_filter
        )
        
        # 生成结果信息
        total_count = len(all_scenes)
        filtered_count = len(filtered_scenes)
        
        if search_query or status_filter != "全部" or chapter_filter != "全部章节":
            filter_info = f"📊 筛选结果: **{filtered_count}** / {total_count} 个场景"
            active_filters = []
            if search_query:
                active_filters.append(f"关键词: '{search_query}'")
            if status_filter != "全部":
                active_filters.append(f"状态: {status_filter}")
            if chapter_filter != "全部章节":
                active_filters.append(f"章节: {chapter_filter}")
            if active_filters:
                filter_info += f"  |  筛选条件: {', '.join(active_filters)}"
        else:
            filter_info = f"📊 共 **{total_count}** 个场景"

        if not filtered_scenes:
            empty_html = "<div class='scene-list-empty'>没有匹配的场景</div>"
            return empty_html, [], "", filter_info, gr.update(choices=chapter_choices, value=chapter_filter)

        # 构建可拖拽的HTML列表
        html_items = []
        scene_ids = []
        for i, s in enumerate(filtered_scenes):
            scene_id = s.get("id", f"scene_{i}")
            scene_ids.append(scene_id)
            duration = s.get("duration", 5)
            desc = s.get("visual", {}).get("description", "")[:40]
            status = s.get("generation_status", {}).get("image", "pending")
            status_icon = {"pending": "⏳", "completed": "✅", "failed": "❌"}.get(status, "❓")
            
            # 高亮搜索关键词
            display_id = scene_id
            display_desc = desc
            if search_query:
                search_lower = search_query.lower()
                if search_lower in scene_id.lower():
                    display_id = scene_id.replace(search_query, f"<mark>{search_query}</mark>")
                if search_lower in desc.lower():
                    # 简单高亮
                    idx = desc.lower().find(search_lower)
                    if idx >= 0:
                        matched_text = desc[idx:idx+len(search_query)]
                        display_desc = desc.replace(matched_text, f"<mark>{matched_text}</mark>")
            
            # 检查是否有预览图
            image_path = self.current_project / "images" / f"{scene_id}.png"
            has_image = image_path.exists()
            thumb_style = f"background-image: url('file={image_path}');" if has_image else ""
            
            # 获取原始索引
            original_idx = s.get("_original_index", i)
            
            html_items.append(f'''
                <div class="scene-item" draggable="true" data-scene-id="{scene_id}" data-index="{original_idx}">
                    <div class="scene-drag-handle">⋮⋮</div>
                    <div class="scene-index">{original_idx}</div>
                    <div class="scene-thumb" style="{thumb_style}"></div>
                    <div class="scene-info">
                        <div class="scene-id">{display_id}</div>
                        <div class="scene-desc">{display_desc}...</div>
                    </div>
                    <div class="scene-meta">
                        <span class="scene-duration">{duration}s</span>
                        <span class="scene-status">{status_icon}</span>
                    </div>
                </div>
            ''')

        html_content = f'''
            <div class="sortable-scene-container" id="scene-container">
                {"".join(html_items)}
            </div>
            <div class="drag-hint">💡 拖拽场景项可调整顺序，拖拽后点击"保存排序"</div>
        '''

        # Dataframe数据
        table_data = [
            [str(s.get("_original_index", i)), s["id"], f"{s.get('duration', 5)}s", 
             s.get("visual", {}).get("description", "")[:50] + "...",
             s.get("generation_status", {}).get("image", "pending")]
            for i, s in enumerate(filtered_scenes)
        ]

        return html_content, table_data, ",".join(scene_ids), filter_info, gr.update(choices=chapter_choices, value=chapter_filter)

    def _filter_scenes(
        self,
        scenes: List[Dict],
        search_query: str = "",
        status_filter: str = "全部",
        chapter_filter: str = "全部章节"
    ) -> List[Dict]:
        """筛选场景列表"""
        filtered = []
        
        # 状态映射
        status_map = {
            "待处理": "pending",
            "已完成": "completed",
            "失败": "failed"
        }
        target_status = status_map.get(status_filter)
        
        for i, scene in enumerate(scenes):
            # 保存原始索引
            scene["_original_index"] = i
            
            # 状态筛选
            if target_status:
                scene_status = scene.get("generation_status", {}).get("image", "pending")
                if scene_status != target_status:
                    continue
            
            # 章节筛选
            if chapter_filter and chapter_filter != "全部章节":
                scene_id = scene.get("id", "")
                # 从场景ID提取章节号 (假设格式: scene_01_001)
                parts = scene_id.split("_")
                if len(parts) >= 2:
                    chapter_num = parts[1]
                    expected_chapter = f"第{chapter_num}章"
                    if chapter_filter != expected_chapter:
                        continue
                else:
                    continue
            
            # 搜索筛选 - 搜索场景ID、描述、对话内容
            if search_query:
                query_lower = search_query.lower()
                match = False
                
                # 搜索场景ID
                if query_lower in scene.get("id", "").lower():
                    match = True
                
                # 搜索视觉描述
                if not match:
                    desc = scene.get("visual", {}).get("description", "").lower()
                    if query_lower in desc:
                        match = True
                
                # 搜索对话内容
                if not match:
                    audio = scene.get("audio", {})
                    # 搜索旁白
                    narration = audio.get("narration", {}).get("text", "").lower()
                    if query_lower in narration:
                        match = True
                    
                    # 搜索对话
                    if not match:
                        dialogues = audio.get("dialogues", [])
                        for d in dialogues:
                            if query_lower in d.get("text", "").lower():
                                match = True
                                break
                            if query_lower in d.get("character_id", "").lower():
                                match = True
                                break
                
                if not match:
                    continue
            
            filtered.append(scene)
        
        return filtered

    def _extract_chapter_choices(self, scenes: List[Dict]) -> List[str]:
        """从场景列表提取章节选项"""
        chapter_nums = set()
        for scene in scenes:
            scene_id = scene.get("id", "")
            parts = scene_id.split("_")
            if len(parts) >= 2:
                chapter_nums.add(parts[1])
        
        choices = ["全部章节"]
        for num in sorted(chapter_nums):
            choices.append(f"第{num}章")
        
        return choices

    def _clear_scene_filter(self) -> Tuple[str, str, str, str, List[List[str]], str, str]:
        """清除场景筛选条件"""
        # 重新加载全部场景
        html_content, table_data, order_state = self._load_scenes_html()
        
        # 计算场景数量
        if self.current_project:
            storyboard_path = self.current_project / "storyboard.json"
            if storyboard_path.exists():
                storyboard = load_json(storyboard_path)
                total = len(storyboard.get("scenes", []))
                filter_info = f"📊 共 **{total}** 个场景"
            else:
                filter_info = ""
        else:
            filter_info = ""
        
        return "", "全部", "全部章节", html_content, table_data, order_state, filter_info

    def _save_scene_order(self, order_state: str) -> Tuple[str, List[List[str]], str, str]:
        """保存场景排序"""
        if not self.current_project:
            return "", [], "请先打开项目", ""

        if not order_state:
            return "", [], "没有排序数据", ""

        storyboard_path = self.current_project / "storyboard.json"
        if not storyboard_path.exists():
            return "", [], "分镜数据不存在", ""

        try:
            new_order = [s.strip() for s in order_state.split(",") if s.strip()]
            
            storyboard = load_json(storyboard_path)
            scenes = storyboard.get("scenes", [])
            
            # 创建ID到场景的映射
            scene_map = {s.get("id"): s for s in scenes}
            
            # 按新顺序重排
            reordered_scenes = []
            for scene_id in new_order:
                if scene_id in scene_map:
                    reordered_scenes.append(scene_map[scene_id])
            
            # 添加未在新顺序中的场景(防止丢失)
            existing_ids = set(new_order)
            for scene in scenes:
                if scene.get("id") not in existing_ids:
                    reordered_scenes.append(scene)
            
            storyboard["scenes"] = reordered_scenes
            save_json(storyboard_path, storyboard)
            
            logger.info(f"场景顺序已保存: {len(reordered_scenes)} 个场景")
            
            # 重新加载
            html_content, table_data, new_order_state = self._load_scenes_html()
            return html_content, table_data, f"✅ 排序已保存 ({len(reordered_scenes)} 个场景)", new_order_state

        except Exception as e:
            logger.error(f"保存排序失败: {e}")
            html_content, table_data, _ = self._load_scenes_html()
            return html_content, table_data, f"❌ 保存失败: {e}", order_state

    def _on_scene_html_click(self, html_value: str) -> Tuple[str, float, str, str, str, Optional[str]]:
        """处理HTML场景列表点击(从前端传递的值解析)"""
        # 这个方法主要用于接收前端点击事件
        # 实际场景选择通过JavaScript直接触发
        return "", 5.0, "", "", "static", None

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
        resume: bool,
        skip_failed: bool = True,
        failure_threshold: float = 50
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
            
            # 设置跳过失败场景选项
            self.pipeline.skip_failed_scenes = skip_failed
            self.pipeline.failure_threshold = failure_threshold / 100.0  # 转换为0-1范围

            def progress_callback(stage: str, detail: str, progress: float):
                logs.append(f"[{stage}] {detail}")
            
            def error_callback(scene_id: str, error: str):
                logs.append(f"[错误] 场景 {scene_id}: {error}")

            self.pipeline.on_progress = progress_callback
            self.pipeline.on_error = error_callback

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

    def _save_settings(
        self,
        ollama_url: str,
        ollama_model: str,
        comfyui_url: str,
        cosyvoice_url: str,
        video_provider: str,
        video_api_key: str,
        use_idle_time: bool,
        resolution: str,
        fps: int
    ) -> str:
        """保存设置到配置文件"""
        try:
            import yaml
            config_path = Path(__file__).parent.parent / "config" / "settings.yaml"

            # 构建配置数据
            config_data = {
                "local": {
                    "ollama_url": ollama_url,
                    "ollama_model": ollama_model,
                    "comfyui_url": comfyui_url,
                    "cosyvoice_url": cosyvoice_url
                },
                "api": {
                    "video_provider": video_provider,
                    "use_idle_time": use_idle_time
                },
                "video": {
                    "resolution": resolution,
                    "fps": fps
                }
            }

            # 保存到文件
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False)

            # 保存API密钥到.env文件
            if video_api_key:
                env_path = Path(__file__).parent.parent / ".env"
                env_content = ""
                if env_path.exists():
                    env_content = env_path.read_text(encoding="utf-8")

                # 更新或添加API密钥
                key_name = "JIMENG_API_KEY" if video_provider == "jimeng" else "KLING_API_KEY"
                if key_name in env_content:
                    import re
                    env_content = re.sub(f"{key_name}=.*", f"{key_name}={video_api_key}", env_content)
                else:
                    env_content += f"\n{key_name}={video_api_key}"
                env_path.write_text(env_content.strip() + "\n", encoding="utf-8")

            # 重新加载配置
            from .utils.config import reload_config
            self.config = reload_config()

            return "✅ 设置已保存"
        except Exception as e:
            logger.error(f"保存设置失败: {e}")
            return f"❌ 保存失败: {e}"

    def _select_scene(self, evt: gr.SelectData) -> Tuple[str, float, str, str, str, Optional[str]]:
        """选择场景 - 加载场景详细信息"""
        if not self.current_project:
            return "", 5.0, "", "", "static", None

        try:
            storyboard_path = self.current_project / "storyboard.json"
            if not storyboard_path.exists():
                return "", 5.0, "", "", "static", None

            storyboard = load_json(storyboard_path)
            scenes = storyboard.get("scenes", [])

            # 获取选中的行索引
            row_idx = evt.index[0] if isinstance(evt.index, (list, tuple)) else evt.index

            if row_idx < 0 or row_idx >= len(scenes):
                return "", 5.0, "", "", "static", None

            scene = scenes[row_idx]
            scene_id = scene.get("id", "")
            duration = float(scene.get("duration", 5.0))

            # 获取视觉描述
            visual = scene.get("visual", {})
            description = visual.get("description", "")

            # 获取对话/旁白
            audio = scene.get("audio", {})
            dialogue_text = ""
            if audio.get("narration") and audio["narration"].get("text"):
                dialogue_text = f"[旁白] {audio['narration']['text']}"
            dialogues = audio.get("dialogues", [])
            for d in dialogues:
                if d.get("text"):
                    char_id = d.get("character_id", "未知")
                    dialogue_text += f"\n[{char_id}] {d['text']}"

            # 获取镜头类型
            camera = visual.get("camera", {})
            camera_type = camera.get("type", "static")

            # 获取预览图像
            image_path = self.current_project / "images" / f"{scene_id}.png"
            preview_image = str(image_path) if image_path.exists() else None

            return scene_id, duration, description, dialogue_text.strip(), camera_type, preview_image

        except Exception as e:
            logger.error(f"选择场景失败: {e}")
            return "", 5.0, "", "", "static", None

    def _save_scene(
        self,
        scene_id: str,
        duration: float,
        description: str,
        dialogue: str,
        camera_type: str
    ) -> List[List[str]]:
        """保存场景修改"""
        if not self.current_project or not scene_id:
            return self._load_scenes()

        try:
            storyboard_path = self.current_project / "storyboard.json"
            if not storyboard_path.exists():
                return self._load_scenes()

            storyboard = load_json(storyboard_path)
            scenes = storyboard.get("scenes", [])

            # 找到并更新场景
            for scene in scenes:
                if scene.get("id") == scene_id:
                    scene["duration"] = duration

                    # 更新视觉描述
                    if "visual" not in scene:
                        scene["visual"] = {}
                    scene["visual"]["description"] = description

                    # 更新镜头
                    if "camera" not in scene["visual"]:
                        scene["visual"]["camera"] = {}
                    scene["visual"]["camera"]["type"] = camera_type

                    # 解析并更新对话/旁白
                    if dialogue:
                        if "audio" not in scene:
                            scene["audio"] = {}

                        lines = dialogue.strip().split("\n")
                        scene["audio"]["dialogues"] = []

                        for line in lines:
                            line = line.strip()
                            if line.startswith("[旁白]"):
                                text = line.replace("[旁白]", "").strip()
                                scene["audio"]["narration"] = {"text": text, "emotion": "narrative"}
                            elif line.startswith("[") and "]" in line:
                                # 解析 [角色ID] 内容
                                bracket_end = line.index("]")
                                char_id = line[1:bracket_end]
                                text = line[bracket_end + 1:].strip()
                                scene["audio"]["dialogues"].append({
                                    "character_id": char_id,
                                    "text": text,
                                    "emotion": "neutral"
                                })

                    # 重置生成状态
                    if "generation_status" in scene:
                        scene["generation_status"]["image"] = "pending"

                    break

            # 保存
            save_json(storyboard_path, storyboard)
            logger.info(f"场景 {scene_id} 已保存")

            return self._load_scenes()

        except Exception as e:
            logger.error(f"保存场景失败: {e}")
            return self._load_scenes()

    def _refresh_preview(
        self,
        preview_type: str,
        scene_selector: Optional[str],
        chapter_selector: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str], Optional[str], str, Optional[Dict], Optional[List]]:
        """刷新预览内容"""
        if not self.current_project:
            return None, None, None, "请先打开项目", None, None

        try:
            if preview_type == "单场景":
                video, audio, image, subtitle = self._preview_single_scene(scene_selector)
                return video, audio, image, subtitle, None, None
            elif preview_type == "章节":
                return self._preview_chapter(chapter_selector)
            elif preview_type == "完整视频":
                video, audio, image, subtitle = self._preview_full_video()
                return video, audio, image, subtitle, None, None
            else:
                return None, None, None, "", None, None

        except Exception as e:
            logger.error(f"刷新预览失败: {e}")
            return None, None, None, f"预览失败: {e}", None, None

    def _preview_single_scene(
        self,
        scene_id: Optional[str]
    ) -> Tuple[Optional[str], Optional[str], Optional[str], str]:
        """预览单个场景"""
        if not scene_id:
            # 如果没有选择场景，尝试获取第一个
            storyboard_path = self.current_project / "storyboard.json"
            if storyboard_path.exists():
                storyboard = load_json(storyboard_path)
                scenes = storyboard.get("scenes", [])
                if scenes:
                    scene_id = scenes[0].get("id")

        if not scene_id:
            return None, None, None, "没有可预览的场景"

        # 获取各资源路径
        video_path = self.current_project / "videos" / f"{scene_id}.mp4"
        audio_path = self.current_project / "audio" / f"{scene_id}.wav"
        image_path = self.current_project / "images" / f"{scene_id}.png"

        video = str(video_path) if video_path.exists() else None
        audio = str(audio_path) if audio_path.exists() else None
        image = str(image_path) if image_path.exists() else None

        # 获取字幕
        subtitle = ""
        storyboard_path = self.current_project / "storyboard.json"
        if storyboard_path.exists():
            storyboard = load_json(storyboard_path)
            for scene in storyboard.get("scenes", []):
                if scene.get("id") == scene_id:
                    subtitle_data = scene.get("subtitle", {})
                    subtitle = subtitle_data.get("text", "")
                    break

        return video, audio, image, subtitle

    def _preview_chapter(
        self,
        chapter_id: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str], Optional[str], str, Optional[Dict], Optional[List]]:
        """预览章节 - 显示章节内所有场景的预览"""
        if not self.current_project:
            return None, None, None, "请先打开项目", None, None
        
        storyboard_path = self.current_project / "storyboard.json"
        if not storyboard_path.exists():
            return None, None, None, "分镜数据不存在", None, None
        
        storyboard = load_json(storyboard_path)
        scenes = storyboard.get("scenes", [])
        chapters = storyboard.get("chapters", [])
        
        # 如果没有章节数据，尝试从场景ID推断
        if not chapters:
            # 从场景ID提取章节信息 (假设格式: scene_01_001 -> chapter 01)
            chapter_map = {}
            for scene in scenes:
                scene_id = scene.get("id", "")
                parts = scene_id.split("_")
                if len(parts) >= 2:
                    chap_num = parts[1]
                    if chap_num not in chapter_map:
                        chapter_map[chap_num] = []
                    chapter_map[chap_num].append(scene)
            
            # 转换为章节列表
            chapters = [
                {"id": f"chapter_{k}", "name": f"第{k}章", "scene_ids": [s["id"] for s in v]}
                for k, v in sorted(chapter_map.items())
            ]
        
        if not chapters:
            return None, None, None, "没有章节数据", None, None
        
        # 选择要预览的章节
        target_chapter = None
        if chapter_id:
            for chap in chapters:
                if chap.get("id") == chapter_id or chap.get("name") == chapter_id:
                    target_chapter = chap
                    break
        
        if not target_chapter:
            target_chapter = chapters[0]  # 默认第一章
        
        # 获取章节场景
        chapter_scene_ids = target_chapter.get("scene_ids", [])
        chapter_scenes = [s for s in scenes if s.get("id") in chapter_scene_ids]
        
        # 构建章节信息
        chapter_info = {
            "id": target_chapter.get("id"),
            "name": target_chapter.get("name", "未命名章节"),
            "scene_count": len(chapter_scenes),
            "total_duration": sum(s.get("duration", 5) for s in chapter_scenes),
            "scenes": [
                {
                    "id": s.get("id"),
                    "duration": s.get("duration", 5),
                    "status": s.get("generation_status", {})
                }
                for s in chapter_scenes
            ]
        }
        
        # 获取章节场景图像预览
        gallery_images = []
        for scene in chapter_scenes:
            scene_id = scene.get("id")
            image_path = self.current_project / "images" / f"{scene_id}.png"
            if image_path.exists():
                gallery_images.append((str(image_path), scene_id))
        
        # 检查是否有合成的章节视频
        chapter_video_path = self.current_project / "output" / f"{target_chapter.get('id')}.mp4"
        chapter_video = str(chapter_video_path) if chapter_video_path.exists() else None
        
        # 获取第一个场景的预览图
        first_scene_image = None
        if chapter_scenes:
            first_id = chapter_scenes[0].get("id")
            first_image_path = self.current_project / "images" / f"{first_id}.png"
            if first_image_path.exists():
                first_scene_image = str(first_image_path)
        
        status_msg = f"章节: {target_chapter.get('name')} | 场景数: {len(chapter_scenes)} | 总时长: {chapter_info['total_duration']}秒"
        
        return chapter_video, None, first_scene_image, status_msg, chapter_info, gallery_images

    def _preview_full_video(self) -> Tuple[Optional[str], Optional[str], Optional[str], str]:
        """预览完整视频"""
        output_path = self.current_project / "output" / "final_video.mp4"
        if output_path.exists():
            return str(output_path), None, None, "最终视频"
        return None, None, None, "完整视频尚未生成"

    def _get_scene_choices(self) -> List[str]:
        """获取场景选择列表"""
        if not self.current_project:
            return []

        storyboard_path = self.current_project / "storyboard.json"
        if not storyboard_path.exists():
            return []

        storyboard = load_json(storyboard_path)
        scenes = storyboard.get("scenes", [])
        return [s.get("id", f"scene_{i}") for i, s in enumerate(scenes)]

    def _get_chapter_list(self) -> List[str]:
        """获取章节列表"""
        if not self.current_project:
            return []

        storyboard_path = self.current_project / "storyboard.json"
        if not storyboard_path.exists():
            return []

        storyboard = load_json(storyboard_path)
        chapters = storyboard.get("chapters", [])
        
        # 如果没有章节数据，从场景ID推断
        if not chapters:
            scenes = storyboard.get("scenes", [])
            chapter_nums = set()
            for scene in scenes:
                scene_id = scene.get("id", "")
                parts = scene_id.split("_")
                if len(parts) >= 2:
                    chapter_nums.add(parts[1])
            
            return [f"第{num}章" for num in sorted(chapter_nums)]
        
        return [c.get("name", c.get("id", f"章节{i}")) for i, c in enumerate(chapters)]

    def _load_preview_lists(self, preview_type: str) -> Tuple[gr.update, gr.update]:
        """加载预览列表"""
        scene_choices = self._get_scene_choices()
        chapter_choices = self._get_chapter_list()
        
        return gr.update(choices=scene_choices), gr.update(choices=chapter_choices)

    def _select_scene_with_index(
        self, evt: gr.SelectData
    ) -> Tuple[str, float, str, str, str, Optional[str], int]:
        """选择场景 - 返回场景信息和索引"""
        scene_id, duration, description, dialogue, camera, preview = self._select_scene(evt)
        
        # 获取行索引
        row_idx = evt.index[0] if isinstance(evt.index, (list, tuple)) else evt.index
        
        return scene_id, duration, description, dialogue, camera, preview, row_idx

    def _move_scene(
        self, 
        current_idx: int, 
        direction: str
    ) -> Tuple[List[List[str]], str, int]:
        """移动场景位置"""
        if not self.current_project:
            return [], "请先打开项目", current_idx

        storyboard_path = self.current_project / "storyboard.json"
        if not storyboard_path.exists():
            return [], "分镜数据不存在", current_idx

        try:
            storyboard = load_json(storyboard_path)
            scenes = storyboard.get("scenes", [])
            
            if not scenes:
                return [], "没有场景", current_idx
            
            current_idx = int(current_idx)
            new_idx = current_idx
            
            if direction == "up" and current_idx > 0:
                # 上移
                scenes[current_idx], scenes[current_idx - 1] = scenes[current_idx - 1], scenes[current_idx]
                new_idx = current_idx - 1
            elif direction == "down" and current_idx < len(scenes) - 1:
                # 下移
                scenes[current_idx], scenes[current_idx + 1] = scenes[current_idx + 1], scenes[current_idx]
                new_idx = current_idx + 1
            elif direction == "top" and current_idx > 0:
                # 置顶
                scene = scenes.pop(current_idx)
                scenes.insert(0, scene)
                new_idx = 0
            elif direction == "bottom" and current_idx < len(scenes) - 1:
                # 置底
                scene = scenes.pop(current_idx)
                scenes.append(scene)
                new_idx = len(scenes) - 1
            else:
                return self._load_scenes(), "无法移动", current_idx
            
            # 保存更改
            storyboard["scenes"] = scenes
            save_json(storyboard_path, storyboard)
            
            action_name = {"up": "上移", "down": "下移", "top": "置顶", "bottom": "置底"}.get(direction, direction)
            logger.info(f"场景 {current_idx} {action_name}成功")
            
            return self._load_scenes(), f"✅ 场景已{action_name}", new_idx

        except Exception as e:
            logger.error(f"移动场景失败: {e}")
            return self._load_scenes(), f"❌ 移动失败: {e}", current_idx

    def _get_custom_css(self) -> str:
        """自定义CSS - 全屏居中布局 + 拖拽排序样式"""
        return """
        /* 根容器居中 */
        .gradio-container {
            max-width: 1600px !important;
            width: 100% !important;
            margin: 0 auto !important;
            padding: 20px 40px !important;
            box-sizing: border-box !important;
        }
        
        /* 确保所有子容器也居中 */
        .gradio-container > .main {
            max-width: 100% !important;
            margin: 0 auto !important;
        }
        
        /* Gradio 4.x 兼容 */
        .app {
            max-width: 1600px !important;
            margin: 0 auto !important;
        }
        
        .contain {
            max-width: 100% !important;
            margin: 0 auto !important;
        }
        
        /* Tabs 居中 */
        .tabs {
            width: 100% !important;
        }
        .tabitem {
            width: 100% !important;
        }
        /* 隐藏顶部Tab导航栏（左侧已有侧边栏导航） */
        #main-tabs > .tab-nav,
        #main-tabs > div:first-child:has(button),
        .tabs > .tab-nav,
        div[id="main-tabs"] > div:first-child {
            display: none !important;
        }
        
        /* 表单和块元素 */
        .form {
            width: 100% !important;
        }
        .block {
            width: 100% !important;
        }
        
        /* 隐藏页脚 */
        footer {
            display: none !important;
        }
        
        /* 标题居中 */
        h1 {
            text-align: center !important;
            margin-bottom: 10px !important;
        }
        h1 + p {
            text-align: center !important;
            margin-bottom: 20px !important;
        }
        
        /* 确保 body 不会限制宽度 */
        body {
            display: flex !important;
            justify-content: center !important;
        }
        
        /* 可拖拽场景列表样式 */
        .sortable-scene-container {
            max-height: 500px;
            overflow-y: auto;
            border: 1px solid var(--border-color-primary);
            border-radius: 8px;
            padding: 8px;
            background: var(--background-fill-secondary);
        }
        
        .scene-item {
            display: flex;
            align-items: center;
            padding: 10px 12px;
            margin: 4px 0;
            background: var(--background-fill-primary);
            border: 1px solid var(--border-color-primary);
            border-radius: 6px;
            cursor: grab;
            transition: all 0.2s ease;
            user-select: none;
        }
        
        .scene-item:hover {
            background: var(--background-fill-secondary);
            border-color: var(--color-accent);
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .scene-item:active {
            cursor: grabbing;
        }
        
        .scene-item.dragging {
            opacity: 0.5;
            background: var(--color-accent-soft);
            border: 2px dashed var(--color-accent);
        }
        
        .scene-item.drag-over {
            border-top: 3px solid var(--color-accent);
            margin-top: 8px;
        }
        
        .scene-drag-handle {
            color: var(--body-text-color-subdued);
            font-size: 16px;
            margin-right: 10px;
            cursor: grab;
        }
        
        .scene-index {
            min-width: 30px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--color-accent);
            color: white;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
            margin-right: 10px;
        }
        
        .scene-thumb {
            width: 60px;
            height: 40px;
            background: var(--background-fill-secondary);
            background-size: cover;
            background-position: center;
            border-radius: 4px;
            margin-right: 12px;
            flex-shrink: 0;
        }
        
        .scene-info {
            flex: 1;
            min-width: 0;
        }
        
        .scene-id {
            font-weight: 600;
            font-size: 13px;
            color: var(--body-text-color);
            margin-bottom: 2px;
        }
        
        .scene-desc {
            font-size: 12px;
            color: var(--body-text-color-subdued);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .scene-meta {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 4px;
            margin-left: 12px;
        }
        
        .scene-duration {
            font-size: 11px;
            color: var(--body-text-color-subdued);
            background: var(--background-fill-secondary);
            padding: 2px 6px;
            border-radius: 4px;
        }
        
        .scene-status {
            font-size: 14px;
        }
        
        .scene-list-empty {
            text-align: center;
            padding: 40px;
            color: var(--body-text-color-subdued);
            font-size: 14px;
        }
        
        .drag-hint {
            text-align: center;
            padding: 8px;
            font-size: 12px;
            color: var(--body-text-color-subdued);
            background: var(--background-fill-secondary);
            border-radius: 4px;
            margin-top: 8px;
        }
        
        /* 搜索高亮样式 */
        mark {
            background-color: #ffeb3b;
            color: #000;
            padding: 0 2px;
            border-radius: 2px;
        }
        
        /* 筛选结果信息样式 */
        #filter-result-info {
            padding: 8px 12px;
            background: var(--background-fill-secondary);
            border-radius: 4px;
            font-size: 13px;
            margin-top: 8px;
        }
        
        #filter-result-info strong {
            color: var(--color-accent);
        }
        """

    def _get_drag_sort_js(self) -> str:
        """获取拖拽排序的JavaScript代码"""
        return """
        <script>
        (function() {
            let draggedItem = null;
            
            function initDragSort() {
                const container = document.getElementById('scene-container');
                if (!container) {
                    setTimeout(initDragSort, 500);
                    return;
                }
                
                const items = container.querySelectorAll('.scene-item');
                items.forEach(item => {
                    item.addEventListener('dragstart', handleDragStart);
                    item.addEventListener('dragend', handleDragEnd);
                    item.addEventListener('dragover', handleDragOver);
                    item.addEventListener('drop', handleDrop);
                    item.addEventListener('dragleave', handleDragLeave);
                });
            }
            
            function handleDragStart(e) {
                draggedItem = this;
                this.classList.add('dragging');
                e.dataTransfer.effectAllowed = 'move';
                e.dataTransfer.setData('text/plain', this.dataset.sceneId);
            }
            
            function handleDragEnd(e) {
                this.classList.remove('dragging');
                document.querySelectorAll('.scene-item').forEach(item => {
                    item.classList.remove('drag-over');
                });
                updateOrderState();
            }
            
            function handleDragOver(e) {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
                
                if (this !== draggedItem) {
                    this.classList.add('drag-over');
                }
            }
            
            function handleDragLeave(e) {
                this.classList.remove('drag-over');
            }
            
            function handleDrop(e) {
                e.preventDefault();
                this.classList.remove('drag-over');
                
                if (this !== draggedItem && draggedItem) {
                    const container = document.getElementById('scene-container');
                    const items = Array.from(container.querySelectorAll('.scene-item'));
                    const draggedIdx = items.indexOf(draggedItem);
                    const dropIdx = items.indexOf(this);
                    
                    if (draggedIdx < dropIdx) {
                        this.parentNode.insertBefore(draggedItem, this.nextSibling);
                    } else {
                        this.parentNode.insertBefore(draggedItem, this);
                    }
                    
                    updateIndices();
                    updateOrderState();
                }
            }
            
            function updateIndices() {
                const container = document.getElementById('scene-container');
                if (!container) return;
                
                const items = container.querySelectorAll('.scene-item');
                items.forEach((item, idx) => {
                    const indexEl = item.querySelector('.scene-index');
                    if (indexEl) {
                        indexEl.textContent = idx;
                    }
                    item.dataset.index = idx;
                });
            }
            
            function updateOrderState() {
                const container = document.getElementById('scene-container');
                if (!container) return;
                
                const items = container.querySelectorAll('.scene-item');
                const order = Array.from(items).map(item => item.dataset.sceneId);
                
                // 更新隐藏的状态输入框
                const stateInput = document.querySelector('#scene-order-state textarea, #scene-order-state input');
                if (stateInput) {
                    stateInput.value = order.join(',');
                    stateInput.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }
            
            // 初始化
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', initDragSort);
            } else {
                initDragSort();
            }
            
            // 监听DOM变化，重新绑定事件
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.addedNodes.length > 0) {
                        setTimeout(initDragSort, 100);
                    }
                });
            });
            
            observer.observe(document.body, { childList: true, subtree: true });
        })();
        </script>
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
