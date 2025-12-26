"""
WebUI 标签页组件 - 任务队列
"""
import gradio as gr
from typing import List, Tuple, Dict, Any

from ..utils.logger import get_logger

logger = get_logger(__name__)


class TasksTab:
    """任务队列标签页"""

    def __init__(self, app: "NovelVideoApp"):
        self.app = app

    def create(self) -> None:
        """创建任务队列标签页"""
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### 任务队列")
                self.task_table = gr.Dataframe(
                    headers=["ID", "名称", "类型", "状态", "进度", "消息"],
                    label="任务列表",
                    interactive=False,
                )

                with gr.Row():
                    self.refresh_tasks_btn = gr.Button("刷新", size="sm")
                    self.clear_completed_btn = gr.Button("清除已完成", size="sm")
                    self.cancel_all_btn = gr.Button("取消全部", variant="stop", size="sm")

                self.queue_status = gr.JSON(label="队列状态")

            with gr.Column(scale=3):
                self._create_log_section()
                self._create_batch_section()

        self._bind_events()

    def _create_log_section(self) -> None:
        """创建日志区域"""
        gr.Markdown("### 实时日志")
        self.realtime_log = gr.Textbox(
            label="",
            lines=20,
            interactive=False,
            show_label=False,
            elem_id="realtime-log",
        )

        with gr.Row():
            self.auto_refresh = gr.Checkbox(label="自动刷新", value=True)
            self.refresh_interval = gr.Slider(
                label="刷新间隔(秒)", minimum=0.5, maximum=5, step=0.5, value=1
            )
            self.clear_log_btn = gr.Button("清空日志", size="sm")

        self.ws_status = gr.Markdown(
            "轮询模式 (WebSocket未连接)", elem_id="ws-status"
        )

    def _create_batch_section(self) -> None:
        """创建批量操作区域"""
        gr.Markdown("### 批量操作")
        with gr.Row():
            self.batch_scene_ids = gr.Textbox(
                label="场景ID列表 (逗号分隔)",
                placeholder="scene_01_001, scene_01_002, ...",
            )

        with gr.Row():
            self.batch_regen_image = gr.Checkbox(label="重新生成图像", value=True)
            self.batch_regen_audio = gr.Checkbox(label="重新生成音频", value=False)
            self.batch_regen_video = gr.Checkbox(label="重新生成视频", value=False)

        with gr.Row():
            self.batch_regenerate_btn = gr.Button("批量重新生成", variant="primary")
            self.batch_delete_btn = gr.Button("批量删除", variant="stop")
            self.batch_reset_status_btn = gr.Button("重置状态为待处理")

        self.batch_result = gr.Textbox(label="操作结果", interactive=False)

    def _bind_events(self) -> None:
        """绑定事件"""
        self.refresh_tasks_btn.click(
            fn=self.app.refresh_task_list,
            outputs=[self.task_table, self.queue_status],
        )
        self.clear_completed_btn.click(
            fn=self.app.clear_completed_tasks,
            outputs=[self.task_table, self.queue_status, self.batch_result],
        )
        self.clear_log_btn.click(
            fn=self.app.clear_logs,
            outputs=[self.realtime_log],
        )
        self.batch_regenerate_btn.click(
            fn=self.app.batch_regenerate,
            inputs=[
                self.batch_scene_ids,
                self.batch_regen_image,
                self.batch_regen_audio,
                self.batch_regen_video,
            ],
            outputs=[self.batch_result, self.task_table, self.queue_status],
        )
        self.batch_delete_btn.click(
            fn=self.app.batch_delete_scenes,
            inputs=[self.batch_scene_ids],
            outputs=[self.batch_result],
        )
        self.batch_reset_status_btn.click(
            fn=self.app.batch_reset_status,
            inputs=[self.batch_scene_ids],
            outputs=[self.batch_result],
        )
