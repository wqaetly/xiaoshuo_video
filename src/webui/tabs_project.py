"""
WebUI 标签页组件 - 项目管理和分镜编辑
"""
import gradio as gr
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

from ..utils.file_utils import load_json, save_json, ensure_dir
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ProjectTab:
    """项目管理标签页 - 优化版：项目仪表盘+快捷操作"""

    def __init__(self, app: "NovelVideoApp"):
        self.app = app
        # 需要刷新的组件引用
        self.project_info = None
        self.project_list = None

    def create(self) -> None:
        """创建项目管理标签页 - 优化为仪表盘风格"""
        # 项目状态概览
        gr.Markdown("### 📊 项目概览")
        gr.Markdown("*从顶部下拉框选择或切换项目*", elem_classes=["hint-text"])

        self.project_info = gr.JSON(label="当前项目信息", elem_classes=["project-info-card"])

        # 快捷操作区
        gr.Markdown("### ⚡ 快捷操作")
        with gr.Row():
            self.quick_analyze_btn = gr.Button("📝 分析小说生成分镜", variant="primary", scale=1)
            self.quick_generate_btn = gr.Button("🎨 一键生成全部", variant="primary", scale=1)
            self.quick_preview_btn = gr.Button("👁️ 预览成品视频", variant="secondary", scale=1)

        self.quick_status = gr.Textbox(label="操作状态", interactive=False, lines=2)

        # 项目进度统计
        gr.Markdown("### 📈 生成进度")
        self.progress_stats = gr.JSON(label="进度统计", elem_classes=["progress-stats"])
        self.refresh_stats_btn = gr.Button("🔄 刷新统计", size="sm")

        # 新建项目区（折叠）
        with gr.Accordion("➕ 创建新项目", open=False):
            with gr.Row():
                with gr.Column(scale=2):
                    self.project_name = gr.Textbox(label="项目名称", placeholder="输入项目名称...")
                    self.novel_file = gr.File(label="上传小说文件 (.txt)", file_types=[".txt"])
                with gr.Column(scale=1):
                    self.video_style = gr.Dropdown(
                        label="视频风格",
                        choices=["anime", "realistic", "illustration", "chinese_fantasy", "xianxia", "realistic_gufeng"],
                        value="xianxia",
                    )
                    self.create_btn = gr.Button("创建项目", variant="primary")
            self.create_status = gr.Textbox(label="创建状态", interactive=False)

        # 保留隐藏的project_list用于兼容
        self.project_list = gr.Dropdown(visible=False, choices=self.app.get_project_list())

        self._bind_events()

    def _bind_events(self) -> None:
        """绑定事件"""
        # 创建项目
        self.create_btn.click(
            fn=self._create_and_switch_project,
            inputs=[self.project_name, self.novel_file, self.video_style],
            outputs=[self.create_status, self.project_list, self.project_info, self.progress_stats],
        )

        # 刷新统计
        self.refresh_stats_btn.click(
            fn=self._get_project_stats,
            outputs=[self.progress_stats],
        )

        # 快捷操作
        self.quick_analyze_btn.click(
            fn=self._quick_analyze,
            outputs=[self.quick_status],
        )
        self.quick_generate_btn.click(
            fn=self._quick_generate_all,
            outputs=[self.quick_status],
        )
        self.quick_preview_btn.click(
            fn=self._quick_preview,
            outputs=[self.quick_status],
        )

    def _create_and_switch_project(self, name, novel_file, style):
        """创建项目并自动切换"""
        status, project_list_update = self.app.create_project(name, novel_file, style)
        if "成功" in status:
            # 自动打开新创建的项目
            project_info = self.app.open_project(name)
            stats = self._get_project_stats()
            return status, project_list_update, project_info, stats
        return status, project_list_update, {}, {}

    def _get_project_stats(self):
        """获取项目进度统计 - 代理到app方法"""
        return self.app._get_project_stats()

    def _quick_analyze(self):
        """快捷分析小说"""
        if not self.app.current_project:
            return "❌ 请先选择项目"

        novel_path = self.app.current_project / "input" / "novel.txt"
        if not novel_path.exists():
            return "❌ 未找到小说文件，请上传小说"

        return "⏳ 请前往「生成」页面，选择「仅分析」阶段开始"

    def _quick_generate_all(self):
        """快捷一键生成"""
        if not self.app.current_project:
            return "❌ 请先选择项目"

        storyboard_path = self.app.current_project / "storyboard.json"
        if not storyboard_path.exists():
            return "❌ 请先分析小说生成分镜"

        return "⏳ 请前往「生成」页面，选择「完整流程」开始"

    def _quick_preview(self):
        """快捷预览"""
        if not self.app.current_project:
            return "❌ 请先选择项目"

        output_path = self.app.current_project / "output" / "final_video.mp4"
        if output_path.exists():
            return f"✅ 成品视频已生成: {output_path.name}\n请前往「预览」页面查看"
        return "⏳ 成品视频尚未生成，请先完成生成流程"


class StoryboardTab:
    """分镜编辑标签页"""

    def __init__(self, app: "NovelVideoApp"):
        self.app = app
        # 需要刷新的组件引用
        self.sortable_scene_list = None
        self.scene_list = None
        self.scene_order_state = None
        self.filter_result_info = None
        self.filter_chapter = None
        self.scene_selector = None

    def create(self) -> None:
        """创建分镜编辑标签页 - 优化布局防止溢出"""
        with gr.Row(equal_height=False):
            with gr.Column(scale=2, min_width=280):
                gr.Markdown("### 📋 分镜列表")
                self._create_filter_section()
                self._create_scene_list_section()

            with gr.Column(scale=3, min_width=360):
                gr.Markdown("### ✏️ 场景编辑")
                self._create_scene_editor()

        self._bind_events()

    def _create_filter_section(self) -> None:
        """创建搜索筛选区域 - 紧凑布局"""
        with gr.Group():
            with gr.Row():
                self.search_input = gr.Textbox(
                    label="🔍 搜索",
                    placeholder="场景ID、描述...",
                    scale=4,
                    container=True,
                )
                self.search_btn = gr.Button("搜索", scale=1, size="sm", min_width=60)

            with gr.Row():
                self.filter_status = gr.Dropdown(
                    label="状态",
                    choices=["全部", "待处理", "已完成", "失败"],
                    value="全部",
                    scale=1,
                    min_width=80,
                )
                self.filter_chapter = gr.Dropdown(
                    label="章节",
                    choices=["全部章节"],
                    value="全部章节",
                    scale=1,
                    min_width=90,
                )
                self.clear_filter_btn = gr.Button("清除", scale=1, size="sm", min_width=50)

            self.filter_result_info = gr.Markdown("", elem_id="filter-result-info")

    def _create_scene_list_section(self) -> None:
        """创建场景列表区域 - 优化版：自动加载，点击即选"""
        gr.Markdown("*💡 点击场景卡片直接加载编辑，拖拽可调整顺序*", elem_classes=["hint-text"])

        self.sortable_scene_list = gr.HTML(
            value='<div class="scene-list-empty">选择项目后自动加载分镜...</div>',
            elem_id="sortable-scene-list",
        )
        self.scene_order_state = gr.Textbox(visible=False, elem_id="scene-order-state")

        with gr.Row():
            self.refresh_scenes_btn = gr.Button("🔄 刷新列表", size="sm", scale=1)
            self.save_order_btn = gr.Button("💾 保存排序", variant="secondary", size="sm", scale=1)

        self.order_status = gr.Textbox(label="操作结果", interactive=False, lines=1)

        with gr.Accordion("📋 详细数据表格", open=False):
            self.scene_list = gr.Dataframe(
                headers=["序号", "ID", "时长", "描述", "状态"],
                label="场景列表",
                interactive=False,
            )

        # 保留 load_scenes_btn 用于兼容性，但设为隐藏
        self.load_scenes_btn = gr.Button("加载分镜", visible=False)

    def _create_scene_editor(self) -> None:
        """创建场景编辑器 - 紧凑布局"""
        # 场景选择和ID在一行
        with gr.Row():
            self.scene_selector = gr.Dropdown(
                label="当前场景",
                choices=[],
                interactive=True,
                elem_id="scene-selector-dropdown",
                scale=2,
                min_width=150,
            )
            self.scene_id = gr.Textbox(label="ID", interactive=False, scale=1, min_width=80)
            self.scene_duration = gr.Slider(
                label="时长(秒)", minimum=3, maximum=10, step=0.5, value=5, scale=1
            )

        # 保留 load_scene_btn 用于兼容性，但设为隐藏
        self.load_scene_btn = gr.Button("加载场景", size="sm", visible=False)

        # 核心编辑字段
        self.scene_description = gr.Textbox(label="视觉描述", lines=2, max_lines=4)
        self.scene_sd_prompt = gr.Textbox(label="SD Prompt", lines=2, max_lines=3, interactive=False)

        with gr.Row():
            self.scene_dialogue = gr.Textbox(label="对话/旁白", lines=2, scale=3)
            self.scene_camera = gr.Dropdown(
                label="镜头",
                choices=["static", "slow_zoom_in", "slow_zoom_out", "pan_left", "pan_right", "tilt_up", "tilt_down"],
                allow_custom_value=True,
                scale=1,
                min_width=100,
            )

        with gr.Row():
            self.save_scene_btn = gr.Button("💾 保存", variant="primary", scale=1)
            self.save_and_regenerate_btn = gr.Button("🎨 保存并重新生成", variant="secondary", scale=2)

        self.regenerate_status = gr.Textbox(label="状态", interactive=False, lines=1)
        self.scene_preview = gr.Image(label="场景预览", height=200)

    def _bind_events(self) -> None:
        """绑定事件"""
        filter_inputs = [self.search_input, self.filter_status, self.filter_chapter]
        filter_outputs = [
            self.sortable_scene_list,
            self.scene_list,
            self.scene_order_state,
            self.filter_result_info,
            self.filter_chapter,
        ]
        
        # 场景编辑器输出
        scene_editor_outputs = [
            self.scene_id,
            self.scene_duration,
            self.scene_description,
            self.scene_sd_prompt,
            self.scene_dialogue,
            self.scene_camera,
            self.scene_preview,
        ]

        # 加载分镜时同时更新场景选择下拉框
        def load_scenes_and_update_selector(*args):
            result = self.app.load_scenes_html_with_filter(*args)
            # 从 scene_order_state 提取场景ID列表
            scene_ids = result[2].split(",") if result[2] else []
            return result + (gr.update(choices=scene_ids, value=None),)

        # 保留隐藏按钮的事件（用于兼容自动刷新等）
        self.load_scenes_btn.click(
            fn=load_scenes_and_update_selector,
            inputs=filter_inputs,
            outputs=filter_outputs + [self.scene_selector],
        )

        # 刷新按钮 - 新增的显示按钮
        self.refresh_scenes_btn.click(
            fn=load_scenes_and_update_selector,
            inputs=filter_inputs,
            outputs=filter_outputs + [self.scene_selector],
        )

        # 场景选择下拉框变化时自动加载场景详情（点击卡片会同步此下拉框）
        self.scene_selector.change(
            fn=self.app.load_scene_detail,
            inputs=[self.scene_selector],
            outputs=scene_editor_outputs,
        )

        # 保留隐藏加载按钮事件（兼容性）
        self.load_scene_btn.click(
            fn=self.app.load_scene_detail,
            inputs=[self.scene_selector],
            outputs=scene_editor_outputs,
        )

        self.search_btn.click(
            fn=load_scenes_and_update_selector,
            inputs=filter_inputs,
            outputs=filter_outputs + [self.scene_selector],
        )
        self.search_input.submit(
            fn=load_scenes_and_update_selector,
            inputs=filter_inputs,
            outputs=filter_outputs + [self.scene_selector],
        )
        self.filter_status.change(
            fn=load_scenes_and_update_selector,
            inputs=filter_inputs,
            outputs=filter_outputs + [self.scene_selector],
        )
        self.filter_chapter.change(
            fn=load_scenes_and_update_selector,
            inputs=filter_inputs,
            outputs=filter_outputs + [self.scene_selector],
        )
        self.clear_filter_btn.click(
            fn=self.app.clear_scene_filter,
            outputs=[
                self.search_input,
                self.filter_status,
                self.filter_chapter,
                self.sortable_scene_list,
                self.scene_list,
                self.scene_order_state,
                self.filter_result_info,
            ],
        )
        self.save_order_btn.click(
            fn=self.app.save_scene_order,
            inputs=[self.scene_order_state],
            outputs=[
                self.sortable_scene_list,
                self.scene_list,
                self.order_status,
                self.scene_order_state,
            ],
        )
        self.save_scene_btn.click(
            fn=self.app.save_scene,
            inputs=[
                self.scene_id,
                self.scene_duration,
                self.scene_description,
                self.scene_dialogue,
                self.scene_camera,
            ],
            outputs=[self.scene_list],
        ).then(
            fn=load_scenes_and_update_selector,
            inputs=filter_inputs,
            outputs=filter_outputs + [self.scene_selector],
        )
        
        # 保存并重新生成图像按钮
        self.save_and_regenerate_btn.click(
            fn=self.app.save_scene,
            inputs=[
                self.scene_id,
                self.scene_duration,
                self.scene_description,
                self.scene_dialogue,
                self.scene_camera,
            ],
            outputs=[self.scene_list],
        ).then(
            fn=self.app.regenerate_scene_sync,
            inputs=[self.scene_id],
            outputs=[self.regenerate_status, self.scene_preview],
        ).then(
            fn=load_scenes_and_update_selector,
            inputs=filter_inputs,
            outputs=filter_outputs + [self.scene_selector],
        )
