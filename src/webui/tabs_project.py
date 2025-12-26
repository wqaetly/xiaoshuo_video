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
    """项目管理标签页"""

    def __init__(self, app: "NovelVideoApp"):
        self.app = app

    def create(self) -> None:
        """创建项目管理标签页"""
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 创建新项目")
                self.project_name = gr.Textbox(label="项目名称", placeholder="输入项目名称")
                self.novel_file = gr.File(label="上传小说文件 (.txt)", file_types=[".txt"])
                self.video_style = gr.Dropdown(
                    label="视频风格",
                    choices=["anime", "realistic", "illustration", "chinese_fantasy"],
                    value="anime",
                )
                self.create_btn = gr.Button("创建项目", variant="primary")
                self.create_status = gr.Textbox(label="状态", interactive=False)

            with gr.Column(scale=1):
                gr.Markdown("### 打开已有项目")
                self.project_list = gr.Dropdown(
                    label="选择项目",
                    choices=self.app.get_project_list(),
                    interactive=True,
                )
                self.refresh_btn = gr.Button("刷新列表")
                self.open_btn = gr.Button("打开项目")
                self.project_info = gr.JSON(label="项目信息")

        self._bind_events()

    def _bind_events(self) -> None:
        """绑定事件"""
        self.create_btn.click(
            fn=self.app.create_project,
            inputs=[self.project_name, self.novel_file, self.video_style],
            outputs=[self.create_status, self.project_list],
        )
        self.refresh_btn.click(
            fn=lambda: gr.update(choices=self.app.get_project_list()),
            outputs=[self.project_list],
        )
        self.open_btn.click(
            fn=self.app.open_project,
            inputs=[self.project_list],
            outputs=[self.project_info],
        )


class StoryboardTab:
    """分镜编辑标签页"""

    def __init__(self, app: "NovelVideoApp"):
        self.app = app

    def create(self) -> None:
        """创建分镜编辑标签页"""
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### 分镜列表")
                self._create_filter_section()
                self._create_scene_list_section()

            with gr.Column(scale=3):
                gr.Markdown("### 场景编辑")
                self._create_scene_editor()

        self._bind_events()

    def _create_filter_section(self) -> None:
        """创建搜索筛选区域"""
        with gr.Group():
            gr.Markdown("#### 搜索与筛选")
            with gr.Row():
                self.search_input = gr.Textbox(
                    label="搜索",
                    placeholder="输入场景ID、描述或对话关键词...",
                    scale=3,
                )
                self.search_btn = gr.Button("搜索", scale=1, size="sm")

            with gr.Row():
                self.filter_status = gr.Dropdown(
                    label="状态筛选",
                    choices=["全部", "待处理", "已完成", "失败"],
                    value="全部",
                    scale=1,
                )
                self.filter_chapter = gr.Dropdown(
                    label="章节筛选",
                    choices=["全部章节"],
                    value="全部章节",
                    scale=1,
                )
                self.clear_filter_btn = gr.Button("清除筛选", scale=1, size="sm")

            self.filter_result_info = gr.Markdown("", elem_id="filter-result-info")

    def _create_scene_list_section(self) -> None:
        """创建场景列表区域"""
        self.sortable_scene_list = gr.HTML(
            value='<div class="scene-list-empty">点击「加载分镜」按钮加载场景</div>',
            elem_id="sortable-scene-list",
        )
        self.scene_order_state = gr.Textbox(visible=False, elem_id="scene-order-state")

        with gr.Row():
            self.load_scenes_btn = gr.Button("加载分镜", variant="primary")
            self.save_order_btn = gr.Button("保存排序", variant="secondary")

        self.order_status = gr.Textbox(label="操作结果", interactive=False)

        with gr.Accordion("详细数据表格", open=False):
            self.scene_list = gr.Dataframe(
                headers=["序号", "ID", "时长", "描述", "状态"],
                label="场景列表",
                interactive=False,
            )

    def _create_scene_editor(self) -> None:
        """创建场景编辑器"""
        self.scene_id = gr.Textbox(label="场景ID", interactive=False)
        self.scene_duration = gr.Slider(
            label="时长(秒)", minimum=3, maximum=10, step=0.5, value=5
        )
        self.scene_description = gr.Textbox(label="视觉描述", lines=3)
        self.scene_dialogue = gr.Textbox(label="对话/旁白", lines=2)
        self.scene_camera = gr.Dropdown(
            label="镜头类型",
            choices=["static", "slow_zoom_in", "slow_zoom_out", "pan_left", "pan_right"],
        )

        with gr.Row():
            self.save_scene_btn = gr.Button("保存修改")
            self.regenerate_btn = gr.Button("重新生成", variant="secondary")

        self.scene_preview = gr.Image(label="场景预览")

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

        self.load_scenes_btn.click(
            fn=self.app.load_scenes_html_with_filter,
            inputs=filter_inputs,
            outputs=filter_outputs,
        )
        self.search_btn.click(
            fn=self.app.load_scenes_html_with_filter,
            inputs=filter_inputs,
            outputs=filter_outputs,
        )
        self.search_input.submit(
            fn=self.app.load_scenes_html_with_filter,
            inputs=filter_inputs,
            outputs=filter_outputs,
        )
        self.filter_status.change(
            fn=self.app.load_scenes_html_with_filter,
            inputs=filter_inputs,
            outputs=filter_outputs,
        )
        self.filter_chapter.change(
            fn=self.app.load_scenes_html_with_filter,
            inputs=filter_inputs,
            outputs=filter_outputs,
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
            fn=self.app.load_scenes_html_with_filter,
            inputs=filter_inputs,
            outputs=filter_outputs,
        )
