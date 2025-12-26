"""
WebUI 模块

将 Gradio Web 界面拆分为多个子模块，提高可维护性
"""
from .app import NovelVideoApp, launch
from .styles import get_custom_css, get_drag_sort_js
from .video_editor import VideoEditorTab, FFmpegEditor

__all__ = [
    "NovelVideoApp",
    "launch",
    "get_custom_css",
    "get_drag_sort_js",
    "VideoEditorTab",
    "FFmpegEditor",
]
