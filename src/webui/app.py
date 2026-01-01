"""
WebUI 主应用 - 核心逻辑
"""
import gradio as gr
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from ..pipeline import PipelineController, Phase, PipelineState
from ..llm import OllamaClient
from ..image import ComfyUIClient
from ..tts import CosyVoiceClient
from ..utils.config import get_config, Config
from ..utils.file_utils import load_json, save_json, ensure_dir
from ..utils.logger import get_logger
from ..webui_enhanced import (
    RealtimeLogHandler,
    TaskQueue,
    BatchOperations,
    get_log_handler,
    get_task_queue,
    LogLevel,
)

from .styles import get_custom_css, get_drag_sort_js
from .tabs_project import ProjectTab, StoryboardTab
from .tabs_other import CharactersTab, GenerationTab, PreviewTab, SettingsTab
from .tabs_tasks import TasksTab
from .video_editor import VideoEditorTab

logger = get_logger(__name__)


class NovelVideoApp:
    """小说转视频Web应用 (重构版)"""

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
        # 使用浅色主题
        self._theme = gr.themes.Soft(
            primary_hue="indigo",
            secondary_hue="slate",
            neutral_hue="slate",
        ).set(
            body_background_fill="#f8fafc",
            block_background_fill="#ffffff",
            block_border_width="1px",
            block_border_color="#e2e8f0",
            input_background_fill="#ffffff",
            button_primary_background_fill="linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            button_primary_text_color="#ffffff",
        )
        self._css = get_custom_css()
        self._js = get_drag_sort_js()
        
        with gr.Blocks(
            title="小说转视频 - 混合方案",
            fill_width=True,
        ) as app:
            # 全局状态栏
            with gr.Row(elem_classes=["global-status-bar"]):
                gr.Markdown("📚 小说转视频生成系统", elem_classes=["app-title-inline"])
                self.global_project_selector = gr.Dropdown(
                    label="",
                    choices=self.get_project_list(),
                    value=None,
                    interactive=True,
                    elem_classes=["global-project-dropdown"],
                    scale=1,
                    min_width=200,
                    show_label=False,
                    allow_custom_value=False,
                )
                self.global_refresh_btn = gr.Button("🔄", elem_classes=["status-bar-btn"], scale=0, min_width=44)
                # 隐藏的状态组件，用于内部状态同步
                self.global_project_status = gr.Markdown("", visible=False)

            with gr.Row(elem_classes=["main-layout"]):
                # 左侧导航栏
                with gr.Column(scale=0, min_width=140, elem_classes=["sidebar"]):
                    nav_project = gr.Button("📁 项目", elem_classes=["nav-btn"], elem_id="nav-project")
                    nav_storyboard = gr.Button("🎬 分镜", elem_classes=["nav-btn"], elem_id="nav-storyboard")
                    nav_characters = gr.Button("👤 角色", elem_classes=["nav-btn"], elem_id="nav-characters")
                    nav_generation = gr.Button("⚙️ 生成", elem_classes=["nav-btn"], elem_id="nav-generation")
                    nav_preview = gr.Button("👁️ 预览", elem_classes=["nav-btn"], elem_id="nav-preview")
                    nav_settings = gr.Button("🔧 设置", elem_classes=["nav-btn"], elem_id="nav-settings")
                    nav_tasks = gr.Button("📋 任务", elem_classes=["nav-btn"], elem_id="nav-tasks")
                    nav_editor = gr.Button("🎞️ 剪辑", elem_classes=["nav-btn"], elem_id="nav-editor")
                
                # 右侧内容区域 - 使用Tabs但隐藏tab导航
                with gr.Column(scale=1, elem_classes=["content-area"]):
                    with gr.Tabs(elem_classes=["hidden-tabs"]) as tabs:
                        with gr.Tab("项目", id=0):
                            self.tab_project = ProjectTab(self)
                            self.tab_project.create()
                        with gr.Tab("分镜", id=1):
                            self.tab_storyboard = StoryboardTab(self)
                            self.tab_storyboard.create()
                        with gr.Tab("角色", id=2):
                            self.tab_characters = CharactersTab(self)
                            self.tab_characters.create()
                        with gr.Tab("生成", id=3):
                            self.tab_generation = GenerationTab(self)
                            self.tab_generation.create()
                        with gr.Tab("预览", id=4):
                            self.tab_preview = PreviewTab(self)
                            self.tab_preview.create()
                        with gr.Tab("设置", id=5):
                            self.tab_settings = SettingsTab(self)
                            self.tab_settings.create()
                        with gr.Tab("任务", id=6):
                            self.tab_tasks = TasksTab(self)
                            self.tab_tasks.create()
                        with gr.Tab("剪辑", id=7):
                            self.tab_editor = VideoEditorTab(self)
                            self.tab_editor.create()
            
            # 导航按钮切换Tab
            nav_project.click(fn=lambda: gr.Tabs(selected=0), outputs=tabs)
            nav_storyboard.click(fn=lambda: gr.Tabs(selected=1), outputs=tabs)
            nav_characters.click(fn=lambda: gr.Tabs(selected=2), outputs=tabs)
            nav_generation.click(fn=lambda: gr.Tabs(selected=3), outputs=tabs)
            nav_preview.click(fn=lambda: gr.Tabs(selected=4), outputs=tabs)
            nav_settings.click(fn=lambda: gr.Tabs(selected=5), outputs=tabs)
            nav_tasks.click(fn=lambda: gr.Tabs(selected=6), outputs=tabs)
            nav_editor.click(fn=lambda: gr.Tabs(selected=7), outputs=tabs)

            # 全局项目切换事件 - 刷新所有Tab
            self.global_project_selector.change(
                fn=self.switch_project_and_refresh_all,
                inputs=[self.global_project_selector],
                outputs=[
                    # 状态栏
                    self.global_project_status,
                    # 项目Tab
                    self.tab_project.project_info,
                    # 分镜Tab
                    self.tab_storyboard.sortable_scene_list,
                    self.tab_storyboard.scene_list,
                    self.tab_storyboard.scene_order_state,
                    self.tab_storyboard.filter_result_info,
                    self.tab_storyboard.filter_chapter,
                    self.tab_storyboard.scene_selector,
                    # 角色Tab
                    self.tab_characters.char_list,
                    # 预览Tab
                    self.tab_preview.scene_selector,
                    self.tab_preview.chapter_selector,
                ],
            )
            self.global_refresh_btn.click(
                fn=lambda: gr.update(choices=self.get_project_list()),
                outputs=[self.global_project_selector],
            )

        return app

    # ============ 项目管理方法 ============

    def get_project_list(self) -> List[str]:
        """获取项目列表"""
        projects_dir = Path(self.config.paths.projects_dir)
        if not projects_dir.exists():
            return []
        return [p.name for p in projects_dir.iterdir() if p.is_dir()]

    def create_project(
        self, name: str, novel_file, style: str
    ) -> Tuple[str, gr.update]:
        """创建新项目"""
        if not name:
            return "错误: 请输入项目名称", gr.update()

        project_path = Path(self.config.paths.projects_dir) / name
        if project_path.exists():
            return f"错误: 项目 {name} 已存在", gr.update()

        try:
            for dir_name in ["input", "characters", "images", "videos", "audio", "output"]:
                ensure_dir(project_path / dir_name)

            if novel_file:
                novel_path = project_path / "input" / "novel.txt"
                # Gradio 6.0 返回文件路径字符串或 NamedString
                if hasattr(novel_file, 'name'):
                    # 文件对象，读取路径
                    source_path = novel_file.name
                else:
                    # 直接是路径字符串
                    source_path = str(novel_file)
                
                # 复制文件内容
                import shutil
                shutil.copy(source_path, novel_path)

            project_config = {
                "project": {"name": name},
                "video": {"style": style},
                "local": {
                    "ollama_url": self.config.local.ollama_url,
                    "ollama_model": self.config.local.ollama_model,
                    "comfyui_url": self.config.local.comfyui_url,
                    "cosyvoice_url": self.config.local.cosyvoice_url,
                },
            }
            import yaml
            with open(project_path / "project.yaml", "w", encoding="utf-8") as f:
                yaml.dump(project_config, f, allow_unicode=True)

            self.current_project = project_path
            return f"项目 {name} 创建成功!", gr.update(choices=self.get_project_list())

        except Exception as e:
            return f"创建失败: {e}", gr.update()

    def open_project(self, project_name: str) -> Dict[str, Any]:
        """打开项目"""
        if not project_name:
            return {"error": "请选择项目"}

        project_path = Path(self.config.paths.projects_dir) / project_name
        if not project_path.exists():
            return {"error": f"项目不存在: {project_name}"}

        self.current_project = project_path
        self.pipeline = PipelineController(project_path, self.config)

        info = {
            "name": project_name,
            "path": str(project_path),
            "has_novel": (project_path / "input" / "novel.txt").exists(),
            "has_storyboard": (project_path / "storyboard.json").exists(),
            "has_characters": (project_path / "characters.json").exists(),
        }

        state_file = project_path / "pipeline_state.json"
        if state_file.exists():
            state = PipelineState.load(state_file)
            info["phase"] = state.current_phase.value
            info["progress"] = state.get_progress()

        return info

    def switch_project_global(self, project_name: str) -> str:
        """全局切换项目 - 状态栏使用"""
        if not project_name:
            self.current_project = None
            self.pipeline = None
            return "未选择项目"

        project_path = Path(self.config.paths.projects_dir) / project_name
        if not project_path.exists():
            return f"❌ 项目不存在: {project_name}"

        self.current_project = project_path
        self.pipeline = PipelineController(project_path, self.config)

        # 构建状态信息
        has_storyboard = (project_path / "storyboard.json").exists()
        has_characters = (project_path / "characters.json").exists()
        
        scene_count = 0
        if has_storyboard:
            storyboard = load_json(project_path / "storyboard.json")
            scene_count = len(storyboard.get("scenes", []))
        
        status_parts = [f"📁 **{project_name}**"]
        if scene_count > 0:
            status_parts.append(f"🎬 {scene_count}个场景")
        if has_characters:
            status_parts.append("👤 已有角色")
        
        return " | ".join(status_parts)

    def switch_project_and_refresh_all(self, project_name: str) -> Tuple:
        """全局切换项目并刷新所有Tab数据"""
        # 先执行项目切换
        status_text = self.switch_project_global(project_name)
        
        if not project_name or not self.current_project:
            # 未选择项目，返回空数据
            return (
                status_text,  # global_project_status
                {},  # project_info
                '<div class="scene-list-empty">请先选择项目</div>',  # sortable_scene_list
                [],  # scene_list
                "",  # scene_order_state
                "",  # filter_result_info
                gr.update(choices=["全部章节"], value="全部章节"),  # filter_chapter
                gr.update(choices=[], value=None),  # storyboard scene_selector
                [],  # char_list
                gr.update(choices=[]),  # preview scene_selector
                gr.update(choices=[]),  # preview chapter_selector
            )
        
        # 加载项目信息
        project_info = self.open_project(project_name)
        
        # 加载分镜数据
        storyboard_html, storyboard_table, scene_order, filter_info, chapter_dropdown = \
            self.load_scenes_html_with_filter("", "全部", "全部章节")
        
        # 提取场景ID列表用于下拉框
        scene_ids = scene_order.split(",") if scene_order else []
        
        # 加载角色数据
        char_list = self.load_characters()
        
        # 加载预览列表
        preview_scene_update, preview_chapter_update = self.load_preview_lists("单场景")
        
        return (
            status_text,  # global_project_status
            project_info,  # project_info
            storyboard_html,  # sortable_scene_list
            storyboard_table,  # scene_list
            scene_order,  # scene_order_state
            filter_info,  # filter_result_info
            chapter_dropdown,  # filter_chapter
            gr.update(choices=scene_ids, value=None),  # storyboard scene_selector
            char_list,  # char_list
            preview_scene_update,  # preview scene_selector
            preview_chapter_update,  # preview chapter_selector
        )

    # ============ 分镜管理方法 ============

    def load_scenes(self) -> List[List[str]]:
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
                str(i),
                s["id"],
                f"{s.get('duration', 5)}s",
                s.get("visual", {}).get("description", "")[:50] + "...",
                s.get("generation_status", {}).get("image", "pending"),
            ]
            for i, s in enumerate(scenes)
        ]

    def load_scenes_html(self) -> Tuple[str, List[List[str]], str]:
        """加载分镜列表为可拖拽HTML"""
        if not self.current_project:
            return '<div class="scene-list-empty">请先打开项目</div>', [], ""

        storyboard_path = self.current_project / "storyboard.json"
        if not storyboard_path.exists():
            return '<div class="scene-list-empty">暂无分镜数据</div>', [], ""

        storyboard = load_json(storyboard_path)
        scenes = storyboard.get("scenes", [])

        if not scenes:
            return '<div class="scene-list-empty">暂无场景</div>', [], ""

        html_items = []
        scene_ids = []
        for i, s in enumerate(scenes):
            scene_id = s.get("id", f"scene_{i}")
            scene_ids.append(scene_id)
            duration = s.get("duration", 5)
            desc = s.get("visual", {}).get("description", "")[:40]
            status = s.get("generation_status", {}).get("image", "pending")
            status_icon = {"pending": "...", "completed": "[OK]", "failed": "[X]"}.get(status, "?")

            image_path = self.current_project / "images" / f"{scene_id}.png"
            thumb_style = f"background-image: url('file={image_path}');" if image_path.exists() else ""

            html_items.append(f'''
                <div class="scene-item" draggable="true" data-scene-id="{scene_id}" data-index="{i}">
                    <div class="scene-drag-handle">::</div>
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
            <div class="drag-hint">拖拽场景项可调整顺序，拖拽后点击"保存排序"</div>
        '''

        table_data = [
            [str(i), s["id"], f"{s.get('duration', 5)}s",
             s.get("visual", {}).get("description", "")[:50] + "...",
             s.get("generation_status", {}).get("image", "pending")]
            for i, s in enumerate(scenes)
        ]

        return html_content, table_data, ",".join(scene_ids)

    def _register_task_handlers(self):
        """注册任务处理器"""
        self.task_queue.register_handler("regenerate_image", self._handle_regenerate_image)
        self.task_queue.register_handler("regenerate_audio", self._handle_regenerate_audio)
        self.task_queue.register_handler("regenerate_video", self._handle_regenerate_video)

        def on_progress(task_id: str, progress: float, message: str):
            self.log_handler.info("Task", f"{task_id}: {progress*100:.0f}% - {message}")

        def on_complete(task_id: str, success: bool, message: str):
            level = LogLevel.INFO if success else LogLevel.ERROR
            status = "完成" if success else "失败"
            self.log_handler.add_log(level, "Task", f"{task_id}: {status} - {message}")

        self.task_queue.set_callbacks(on_progress, on_complete)

    def _handle_regenerate_image(self, params: Dict, progress_cb) -> Any:
        """处理图像重新生成任务"""
        scene_id = params.get("scene_id")
        if not self.current_project or not scene_id:
            raise ValueError("项目未打开或场景ID无效")

        progress_cb(0.1, "加载场景数据...")
        storyboard = load_json(self.current_project / "storyboard.json")
        characters = load_json(self.current_project / "characters.json")

        scene = next((s for s in storyboard.get("scenes", []) if s.get("id") == scene_id), None)
        if not scene:
            raise ValueError(f"场景不存在: {scene_id}")

        progress_cb(0.3, "初始化图像生成器...")
        from ..image import ComfyUIClient, SceneGenerator
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

        scene = next((s for s in storyboard.get("scenes", []) if s.get("id") == scene_id), None)
        if not scene:
            raise ValueError(f"场景不存在: {scene_id}")

        progress_cb(0.3, "初始化TTS...")
        from ..tts import create_tts_client
        tts = create_tts_client("edge")

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

        scene = next((s for s in storyboard.get("scenes", []) if s.get("id") == scene_id), None)
        if not scene:
            raise ValueError(f"场景不存在: {scene_id}")

        progress_cb(0.3, "初始化视频API...")
        from ..video import create_video_client
        video_client = create_video_client(
            provider=self.config.api.video_provider,
            api_key=self.config.api.video_api_key,
        )

        progress_cb(0.4, "生成视频...")
        camera = scene.get("visual", {}).get("camera", {})
        motion_prompt = f"{camera.get('type', 'static')} camera movement"

        video_data = video_client.generate(
            image_path=image_path,
            motion_prompt=motion_prompt,
            duration=scene.get("duration", 5.0),
        )

        progress_cb(0.9, "保存视频...")
        video_data.save(self.current_project / "videos" / f"{scene_id}.mp4")

        return {"scene_id": scene_id, "success": True}

    # ============ 分镜筛选方法 ============

    def load_scenes_html_with_filter(
        self,
        search_query: str = "",
        status_filter: str = "全部",
        chapter_filter: str = "全部章节",
    ) -> Tuple[str, List[List[str]], str, str, gr.update]:
        """加载分镜列表，支持搜索和筛选"""
        if not self.current_project:
            empty = '<div class="scene-list-empty">请先打开项目</div>'
            return empty, [], "", "", gr.update(choices=["全部章节"], value="全部章节")

        storyboard_path = self.current_project / "storyboard.json"
        if not storyboard_path.exists():
            empty = '<div class="scene-list-empty">暂无分镜数据</div>'
            return empty, [], "", "", gr.update(choices=["全部章节"], value="全部章节")

        storyboard = load_json(storyboard_path)
        all_scenes = storyboard.get("scenes", [])

        if not all_scenes:
            empty = '<div class="scene-list-empty">暂无场景</div>'
            return empty, [], "", "", gr.update(choices=["全部章节"], value="全部章节")

        chapter_choices = self._extract_chapter_choices(all_scenes)
        filtered_scenes = self._filter_scenes(all_scenes, search_query, status_filter, chapter_filter)

        total_count = len(all_scenes)
        filtered_count = len(filtered_scenes)
        filter_info = f"筛选结果: {filtered_count} / {total_count} 个场景"

        if not filtered_scenes:
            empty = '<div class="scene-list-empty">没有匹配的场景</div>'
            return empty, [], "", filter_info, gr.update(choices=chapter_choices, value=chapter_filter)

        html_items, scene_ids = self._build_scene_html_items(filtered_scenes, search_query)
        html_content = f'''
            <div class="sortable-scene-container" id="scene-container">{"".join(html_items)}</div>
            <div class="drag-hint">拖拽场景项可调整顺序</div>
        '''

        table_data = [
            [str(s.get("_original_index", i)), s["id"], f"{s.get('duration', 5)}s",
             s.get("visual", {}).get("description", "")[:50] + "...",
             s.get("generation_status", {}).get("image", "pending")]
            for i, s in enumerate(filtered_scenes)
        ]

        return html_content, table_data, ",".join(scene_ids), filter_info, gr.update(choices=chapter_choices, value=chapter_filter)

    def _filter_scenes(self, scenes: List[Dict], search_query: str, status_filter: str, chapter_filter: str) -> List[Dict]:
        """筛选场景列表"""
        status_map = {"待处理": "pending", "已完成": "completed", "失败": "failed"}
        target_status = status_map.get(status_filter)
        filtered = []

        for i, scene in enumerate(scenes):
            scene["_original_index"] = i

            if target_status and scene.get("generation_status", {}).get("image", "pending") != target_status:
                continue

            if chapter_filter and chapter_filter != "全部章节":
                parts = scene.get("id", "").split("_")
                if len(parts) >= 2 and f"第{parts[1]}章" != chapter_filter:
                    continue

            if search_query:
                query_lower = search_query.lower()
                match = (
                    query_lower in scene.get("id", "").lower() or
                    query_lower in scene.get("visual", {}).get("description", "").lower() or
                    query_lower in scene.get("audio", {}).get("narration", {}).get("text", "").lower()
                )
                if not match:
                    continue

            filtered.append(scene)
        return filtered

    def _extract_chapter_choices(self, scenes: List[Dict]) -> List[str]:
        """从场景列表提取章节选项"""
        chapter_nums = set()
        for scene in scenes:
            parts = scene.get("id", "").split("_")
            if len(parts) >= 2:
                chapter_nums.add(parts[1])
        return ["全部章节"] + [f"第{num}章" for num in sorted(chapter_nums)]

    def _build_scene_html_items(self, scenes: List[Dict], search_query: str = "") -> Tuple[List[str], List[str]]:
        """构建场景HTML列表项"""
        html_items = []
        scene_ids = []

        for i, s in enumerate(scenes):
            scene_id = s.get("id", f"scene_{i}")
            scene_ids.append(scene_id)
            duration = s.get("duration", 5)
            desc = s.get("visual", {}).get("description", "")[:40]
            status = s.get("generation_status", {}).get("image", "pending")
            status_icon = {"pending": "...", "completed": "[OK]", "failed": "[X]"}.get(status, "?")
            original_idx = s.get("_original_index", i)

            image_path = self.current_project / "images" / f"{scene_id}.png"
            thumb_style = f"background-image: url('file={image_path}');" if image_path.exists() else ""

            html_items.append(f'''
                <div class="scene-item" draggable="true" data-scene-id="{scene_id}" data-index="{original_idx}">
                    <div class="scene-drag-handle">::</div>
                    <div class="scene-index">{original_idx}</div>
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
        return html_items, scene_ids

    def clear_scene_filter(self) -> Tuple[str, str, str, str, List[List[str]], str, str]:
        """清除场景筛选条件"""
        html_content, table_data, order_state = self.load_scenes_html()
        filter_info = ""
        if self.current_project:
            storyboard_path = self.current_project / "storyboard.json"
            if storyboard_path.exists():
                total = len(load_json(storyboard_path).get("scenes", []))
                filter_info = f"共 {total} 个场景"
        return "", "全部", "全部章节", html_content, table_data, order_state, filter_info

    def save_scene_order(self, order_state: str) -> Tuple[str, List[List[str]], str, str]:
        """保存场景排序"""
        if not self.current_project or not order_state:
            return "", [], "请先打开项目或无排序数据", ""

        storyboard_path = self.current_project / "storyboard.json"
        if not storyboard_path.exists():
            return "", [], "分镜数据不存在", ""

        try:
            new_order = [s.strip() for s in order_state.split(",") if s.strip()]
            storyboard = load_json(storyboard_path)
            scenes = storyboard.get("scenes", [])
            scene_map = {s.get("id"): s for s in scenes}

            reordered = [scene_map[sid] for sid in new_order if sid in scene_map]
            existing_ids = set(new_order)
            reordered.extend(s for s in scenes if s.get("id") not in existing_ids)

            storyboard["scenes"] = reordered
            save_json(storyboard_path, storyboard)

            html_content, table_data, new_order_state = self.load_scenes_html()
            return html_content, table_data, f"排序已保存 ({len(reordered)} 个场景)", new_order_state
        except Exception as e:
            logger.error(f"保存排序失败: {e}")
            html_content, table_data, _ = self.load_scenes_html()
            return html_content, table_data, f"保存失败: {e}", order_state

    def load_scene_detail(self, scene_id: str) -> Tuple[str, float, str, str, str, str, Optional[str]]:
        """加载场景详情到编辑器"""
        if not self.current_project or not scene_id:
            return "", 5.0, "", "", "", "static", None

        storyboard_path = self.current_project / "storyboard.json"
        if not storyboard_path.exists():
            return "", 5.0, "", "", "", "static", None

        storyboard = load_json(storyboard_path)
        scene = next((s for s in storyboard.get("scenes", []) if s.get("id") == scene_id), None)

        if not scene:
            return "", 5.0, "", "", "", "static", None

        # 提取场景数据
        duration = float(scene.get("duration", 5.0))
        visual = scene.get("visual", {})
        description = visual.get("description", "") or ""
        sd_prompt = visual.get("sd_prompt", "") or ""
        
        # 获取对话/旁白 - 优先从 narration 获取，否则从 dialogues 或 subtitle 获取
        dialogue = ""
        audio_data = scene.get("audio", {})
        if audio_data:
            narration = audio_data.get("narration")
            if narration and isinstance(narration, dict):
                dialogue = narration.get("text", "") or ""
            elif not dialogue:
                # 尝试从 dialogues 获取
                dialogues = audio_data.get("dialogues", [])
                if dialogues and len(dialogues) > 0:
                    dialogue = dialogues[0].get("text", "") or ""
        # 如果还是空的，尝试从 subtitle 获取
        if not dialogue:
            subtitle = scene.get("subtitle", {})
            if subtitle and isinstance(subtitle, dict):
                dialogue = subtitle.get("text", "") or ""
        
        # 获取镜头类型，确保返回有效值
        camera_type = scene.get("visual", {}).get("camera", {}).get("type", "static") or "static"

        # 检查预览图片
        image_path = self.current_project / "images" / f"{scene_id}.png"
        preview_image = str(image_path) if image_path.exists() else None

        return scene_id, duration, description, sd_prompt, dialogue, camera_type, preview_image

    def save_scene(self, scene_id: str, duration: float, description: str, dialogue: str, camera_type: str) -> List[List[str]]:
        """保存场景修改"""
        if not self.current_project or not scene_id:
            return self.load_scenes()

        storyboard_path = self.current_project / "storyboard.json"
        if not storyboard_path.exists():
            return self.load_scenes()

        storyboard = load_json(storyboard_path)
        for scene in storyboard.get("scenes", []):
            if scene.get("id") == scene_id:
                scene["duration"] = duration
                scene.setdefault("visual", {})["description"] = description
                scene["visual"].setdefault("camera", {})["type"] = camera_type
                break

        save_json(storyboard_path, storyboard)
        return self.load_scenes()

    def regenerate_scene(self, scene_id: str) -> str:
        """重新生成单个场景的图像（异步任务队列）"""
        if not self.current_project or not scene_id:
            return "错误: 请先打开项目并选择场景"
        
        # 添加任务到队列
        import uuid
        task_id = f"regen_{scene_id}_{uuid.uuid4().hex[:8]}"
        self.task_queue.add_task(
            task_id=task_id,
            name=f"重新生成图像: {scene_id}",
            task_type="regenerate_image",
            scene_id=scene_id
        )
        self.task_queue.start()
        
        self.log_handler.info("Scene", f"已添加场景 {scene_id} 的图像重新生成任务: {task_id}")
        return f"已添加重新生成任务: {scene_id}"

    def regenerate_scene_sync(self, scene_id: str) -> Tuple[str, Optional[str]]:
        """同步重新生成单个场景的图像（直接执行，用于编辑后立即生成）"""
        if not self.current_project or not scene_id:
            return "错误: 请先打开项目并选择场景", None
        
        try:
            # 加载场景数据
            storyboard = load_json(self.current_project / "storyboard.json")
            characters_path = self.current_project / "characters.json"
            characters = load_json(characters_path) if characters_path.exists() else {"characters": []}
            
            scene = next((s for s in storyboard.get("scenes", []) if s.get("id") == scene_id), None)
            if not scene:
                return f"场景不存在: {scene_id}", None
            
            # 初始化图像生成器
            from ..image import ComfyUIClient, SceneGenerator
            comfyui = ComfyUIClient(base_url=self.config.local.comfyui_url)
            image_gen = SceneGenerator(comfyui)
            
            # 生成图像
            logger.info(f"开始生成场景图像: {scene_id}")
            image = image_gen.generate_scene(scene, characters, style_preset=self.config.video.style)
            
            # 保存图像
            image_path = self.current_project / "images" / f"{scene_id}.png"
            ensure_dir(image_path.parent)
            image.save(image_path)
            
            # 更新场景状态
            for s in storyboard.get("scenes", []):
                if s.get("id") == scene_id:
                    s.setdefault("generation_status", {})["image"] = "completed"
                    break
            save_json(self.current_project / "storyboard.json", storyboard)
            
            logger.info(f"场景图像生成完成: {scene_id}")
            return f"图像生成成功: {scene_id}", str(image_path)
            
        except Exception as e:
            logger.error(f"场景图像生成失败: {e}")
            return f"生成失败: {e}", None

    # ============ 角色管理方法 ============

    def load_characters(self) -> List[List[str]]:
        """加载角色列表"""
        if not self.current_project:
            return []
        chars_path = self.current_project / "characters.json"
        if not chars_path.exists():
            return []
        characters = load_json(chars_path)
        return [
            [c["id"], c.get("name", "未知"), c.get("appearance", {}).get("gender", "unknown"),
             c.get("voice", {}).get("voice_id", "default")]
            for c in characters.get("characters", [])
        ]

    # ============ 服务检查方法 ============

    def check_services(self) -> Dict[str, Any]:
        """检查服务状态"""
        status = {}
        try:
            llm = OllamaClient(base_url=self.config.local.ollama_url)
            status["ollama"] = "可用" if llm.check_health() else "不可用"
        except Exception:
            status["ollama"] = "连接失败"
        try:
            comfyui = ComfyUIClient(base_url=self.config.local.comfyui_url)
            status["comfyui"] = "可用" if comfyui.check_health() else "不可用"
        except Exception:
            status["comfyui"] = "连接失败"
        try:
            tts = CosyVoiceClient(base_url=self.config.local.cosyvoice_url)
            status["cosyvoice"] = "可用" if tts.check_health() else "不可用"
        except Exception:
            status["cosyvoice"] = "连接失败"
        return status

    # ============ 生成控制方法 ============

    def start_generation(self, phase: str, resume: bool, skip_failed: bool, failure_threshold: float) -> Tuple[str, str, str]:
        """开始生成"""
        if not self.current_project:
            return "错误", "请先打开项目", ""
        if self.is_running:
            return "运行中", "已有任务在执行", ""

        self.is_running = True
        logs = []
        try:
            self.pipeline = PipelineController(self.current_project, self.config)
            self.pipeline.skip_failed_scenes = skip_failed
            self.pipeline.failure_threshold = failure_threshold / 100.0

            def progress_callback(stage: str, detail: str, progress: float):
                logs.append(f"[{stage}] {detail}")

            self.pipeline.on_progress = progress_callback

            if phase == "full":
                self.pipeline.run(resume=resume)
            else:
                self.pipeline.run_phase(Phase(phase))

            return "完成", "生成任务完成", "\n".join(logs[-20:])
        except Exception as e:
            return "错误", str(e), "\n".join(logs[-20:])
        finally:
            self.is_running = False

    # ============ 预览方法 ============

    def load_preview_lists(self, preview_type: str) -> Tuple[gr.update, gr.update]:
        """加载预览列表"""
        if not self.current_project:
            return gr.update(choices=[]), gr.update(choices=[])

        storyboard_path = self.current_project / "storyboard.json"
        if not storyboard_path.exists():
            return gr.update(choices=[]), gr.update(choices=[])

        storyboard = load_json(storyboard_path)
        scenes = storyboard.get("scenes", [])
        scene_ids = [s.get("id") for s in scenes]
        chapters = list(set(s.get("id", "").split("_")[1] for s in scenes if len(s.get("id", "").split("_")) >= 2))

        return gr.update(choices=scene_ids), gr.update(choices=[f"第{c}章" for c in sorted(chapters)])

    def refresh_preview(self, preview_type: str, scene_selector: Optional[str], chapter_selector: Optional[str]) -> Tuple:
        """刷新预览内容"""
        if not self.current_project:
            return None, None, None, "请先打开项目", None, None

        if preview_type == "单场景" and scene_selector:
            video_path = self.current_project / "videos" / f"{scene_selector}.mp4"
            audio_path = self.current_project / "audio" / f"{scene_selector}.wav"
            image_path = self.current_project / "images" / f"{scene_selector}.png"

            return (
                str(video_path) if video_path.exists() else None,
                str(audio_path) if audio_path.exists() else None,
                str(image_path) if image_path.exists() else None,
                "",
                None,
                None,
            )
        elif preview_type == "完整视频":
            output_path = self.current_project / "output" / "final_video.mp4"
            return str(output_path) if output_path.exists() else None, None, None, "", None, None

        return None, None, None, "", None, None

    # ============ 设置方法 ============

    def save_settings(self, ollama_url, ollama_model, comfyui_url, cosyvoice_url,
                      video_provider, video_api_key, use_idle_time, resolution, fps) -> str:
        """保存设置"""
        try:
            import yaml
            config_path = Path(__file__).parent.parent.parent / "config" / "settings.yaml"
            config_data = {
                "local": {"ollama_url": ollama_url, "ollama_model": ollama_model,
                          "comfyui_url": comfyui_url, "cosyvoice_url": cosyvoice_url},
                "api": {"video_provider": video_provider, "use_idle_time": use_idle_time},
                "video": {"resolution": resolution, "fps": fps},
            }
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(config_data, f, allow_unicode=True)

            if video_api_key:
                env_path = Path(__file__).parent.parent.parent / ".env"
                key_name = "JIMENG_API_KEY" if video_provider == "jimeng" else "KLING_API_KEY"
                env_content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
                import re
                if key_name in env_content:
                    env_content = re.sub(f"{key_name}=.*", f"{key_name}={video_api_key}", env_content)
                else:
                    env_content += f"\n{key_name}={video_api_key}"
                env_path.write_text(env_content.strip() + "\n", encoding="utf-8")

            from ..utils.config import reload_config
            self.config = reload_config()
            return "设置已保存"
        except Exception as e:
            logger.error(f"保存设置失败: {e}")
            return f"保存失败: {e}"

    # ============ 任务队列方法 ============

    def refresh_task_list(self) -> Tuple[List[List[str]], Dict[str, Any]]:
        """刷新任务列表"""
        tasks = self.task_queue.get_all_tasks()
        table_data = [
            [t.task_id[:20], t.name[:30], t.task_type, t.status.value,
             f"{t.progress*100:.0f}%", (t.message or t.error or "")[:50]]
            for t in tasks
        ]
        return table_data, self.task_queue.get_queue_status()

    def clear_completed_tasks(self) -> Tuple[List[List[str]], Dict[str, Any], str]:
        """清除已完成的任务"""
        removed = self.task_queue.clear_completed()
        table_data, status = self.refresh_task_list()
        return table_data, status, f"已清除 {removed} 个任务"

    def clear_logs(self) -> str:
        """清空日志"""
        self.log_handler.clear()
        return ""

    def batch_regenerate(self, scene_ids_str: str, regen_image: bool, regen_audio: bool, regen_video: bool) -> Tuple[str, List[List[str]], Dict[str, Any]]:
        """批量重新生成"""
        if not self.current_project or not scene_ids_str.strip():
            return "错误: 请先打开项目并输入场景ID", [], {}

        scene_ids = [s.strip() for s in scene_ids_str.split(",") if s.strip()]
        if not self.batch_ops:
            self.batch_ops = BatchOperations(self.task_queue, self.log_handler)

        task_ids = self.batch_ops.regenerate_scenes(scene_ids, regen_image, regen_audio, regen_video)
        self.task_queue.start()
        table_data, status = self.refresh_task_list()
        return f"已添加 {len(task_ids)} 个任务到队列", table_data, status

    def batch_delete_scenes(self, scene_ids_str: str) -> str:
        """批量删除场景"""
        if not self.current_project or not scene_ids_str.strip():
            return "错误: 请先打开项目并输入场景ID"

        scene_ids = [s.strip() for s in scene_ids_str.split(",") if s.strip()]
        if not self.batch_ops:
            self.batch_ops = BatchOperations(self.task_queue, self.log_handler)

        deleted = self.batch_ops.delete_scenes(scene_ids, self.current_project / "storyboard.json")
        return f"已删除 {deleted} 个场景"

    def batch_reset_status(self, scene_ids_str: str) -> str:
        """批量重置场景状态"""
        if not self.current_project or not scene_ids_str.strip():
            return "错误: 请先打开项目并输入场景ID"

        scene_ids = [s.strip() for s in scene_ids_str.split(",") if s.strip()]
        if not self.batch_ops:
            self.batch_ops = BatchOperations(self.task_queue, self.log_handler)

        updated = 0
        for status_type in ["image", "audio", "video"]:
            updated += self.batch_ops.update_scene_status(scene_ids, status_type, "pending", self.current_project / "storyboard.json")
        return f"已重置 {updated} 个状态"


def launch(server_name: str = "127.0.0.1", server_port: int = 7860, share: bool = False):
    """启动 WebUI"""
    app = NovelVideoApp()
    ui = app.create_ui()
    ui.launch(
        server_name=server_name,
        server_port=server_port,
        share=share,
        theme=app._theme,
        css=app._css,
        js=app._js,
        inbrowser=True,
    )
