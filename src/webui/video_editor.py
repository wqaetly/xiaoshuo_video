"""
视频剪辑模块 - 基于 Gradio + FFmpeg
提供视频裁剪、拼接、预览等功能
"""
import gradio as gr
import subprocess
import tempfile
import shutil
import json
import sys
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from ..utils.logger import get_logger

# 导入 FFmpeg 路径获取函数
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
try:
    from install_ffmpeg import get_ffmpeg_path, get_ffprobe_path
except ImportError:
    # 回退方案
    def get_ffmpeg_path():
        return shutil.which("ffmpeg") or "ffmpeg"
    def get_ffprobe_path():
        return shutil.which("ffprobe") or "ffprobe"

logger = get_logger(__name__)


@dataclass
class ClipSegment:
    """视频片段"""
    source_path: str
    start_time: float  # 秒
    end_time: float    # 秒
    order: int = 0
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_path": self.source_path,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "order": self.order
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClipSegment":
        return cls(**data)


@dataclass
class EditProject:
    """剪辑项目"""
    name: str
    segments: List[ClipSegment] = field(default_factory=list)
    output_path: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_segment(self, segment: ClipSegment):
        segment.order = len(self.segments)
        self.segments.append(segment)
    
    def remove_segment(self, index: int):
        if 0 <= index < len(self.segments):
            self.segments.pop(index)
            # 重新排序
            for i, seg in enumerate(self.segments):
                seg.order = i
    
    def reorder_segments(self, new_order: List[int]):
        """重新排序片段"""
        if len(new_order) != len(self.segments):
            return
        reordered = [self.segments[i] for i in new_order]
        for i, seg in enumerate(reordered):
            seg.order = i
        self.segments = reordered
    
    def total_duration(self) -> float:
        return sum(seg.duration for seg in self.segments)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "segments": [s.to_dict() for s in self.segments],
            "output_path": self.output_path,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EditProject":
        proj = cls(name=data["name"], created_at=data.get("created_at", ""))
        proj.output_path = data.get("output_path")
        proj.segments = [ClipSegment.from_dict(s) for s in data.get("segments", [])]
        return proj


class FFmpegEditor:
    """FFmpeg 视频编辑器"""
    
    def __init__(self):
        self.ffmpeg_path = self._find_ffmpeg()
        self.ffprobe_path = self._find_ffprobe()
    
    def _find_ffmpeg(self) -> str:
        """查找 FFmpeg 路径 - 优先使用项目内置版本"""
        # 优先使用项目内置版本
        project_ffmpeg = get_ffmpeg_path()
        if project_ffmpeg and Path(project_ffmpeg).exists():
            return project_ffmpeg
        
        # 尝试系统路径
        paths = ["ffmpeg", "ffmpeg.exe"]
        for p in paths:
            if shutil.which(p):
                return p
        
        # Windows 常见安装路径
        win_paths = [
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        ]
        for p in win_paths:
            if Path(p).exists():
                return p
        
        return project_ffmpeg or "ffmpeg"
    
    def _find_ffprobe(self) -> str:
        """查找 FFprobe 路径 - 优先使用项目内置版本"""
        # 优先使用项目内置版本
        project_ffprobe = get_ffprobe_path()
        if project_ffprobe and Path(project_ffprobe).exists():
            return project_ffprobe
        
        # 尝试系统路径
        paths = ["ffprobe", "ffprobe.exe"]
        for p in paths:
            if shutil.which(p):
                return p
        
        return project_ffprobe or "ffprobe"
    
    def check_available(self) -> bool:
        """检查 FFmpeg 是否可用"""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """获取视频信息"""
        try:
            cmd = [
                self.ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                # 提取关键信息
                duration = float(data.get("format", {}).get("duration", 0))
                streams = data.get("streams", [])
                video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
                
                return {
                    "duration": duration,
                    "width": video_stream.get("width", 0),
                    "height": video_stream.get("height", 0),
                    "fps": eval(video_stream.get("r_frame_rate", "0/1")) if "/" in video_stream.get("r_frame_rate", "") else 0,
                    "codec": video_stream.get("codec_name", "unknown"),
                }
        except Exception as e:
            logger.error(f"获取视频信息失败: {e}")
        return {"duration": 0, "width": 0, "height": 0, "fps": 0, "codec": "unknown"}
    
    def trim_video(
        self,
        input_path: str,
        output_path: str,
        start_time: float,
        end_time: float,
        reencode: bool = False
    ) -> bool:
        """裁剪视频片段"""
        try:
            if reencode:
                # 重新编码 (更精确但更慢)
                cmd = [
                    self.ffmpeg_path,
                    "-y",
                    "-i", input_path,
                    "-ss", str(start_time),
                    "-to", str(end_time),
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-preset", "fast",
                    output_path
                ]
            else:
                # 快速裁剪 (可能不精确到帧)
                cmd = [
                    self.ffmpeg_path,
                    "-y",
                    "-ss", str(start_time),
                    "-i", input_path,
                    "-to", str(end_time - start_time),
                    "-c", "copy",
                    output_path
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"裁剪视频失败: {e}")
            return False
    
    def concat_videos(
        self,
        input_paths: List[str],
        output_path: str,
        transition: Optional[str] = None
    ) -> bool:
        """拼接多个视频"""
        if not input_paths:
            return False
        
        try:
            # 创建临时文件列表
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                for path in input_paths:
                    # 转义路径中的特殊字符
                    escaped_path = path.replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")
                list_file = f.name
            
            if transition:
                # 带转场效果 (需要重新编码)
                # 这里实现简单的淡入淡出
                cmd = self._build_transition_cmd(input_paths, output_path, transition)
            else:
                # 简单拼接
                cmd = [
                    self.ffmpeg_path,
                    "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", list_file,
                    "-c", "copy",
                    output_path
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            # 清理临时文件
            Path(list_file).unlink(missing_ok=True)
            
            return result.returncode == 0
        except Exception as e:
            logger.error(f"拼接视频失败: {e}")
            return False
    
    def _build_transition_cmd(
        self,
        input_paths: List[str],
        output_path: str,
        transition: str
    ) -> List[str]:
        """构建带转场的拼接命令"""
        # 简化实现: 使用 xfade 滤镜
        cmd = [self.ffmpeg_path, "-y"]
        
        # 添加所有输入
        for path in input_paths:
            cmd.extend(["-i", path])
        
        if len(input_paths) == 1:
            cmd.extend(["-c", "copy", output_path])
            return cmd
        
        # 构建滤镜图
        filter_parts = []
        transition_duration = 0.5  # 转场时长
        
        # 对于多个视频，逐个应用转场
        for i in range(len(input_paths) - 1):
            if i == 0:
                filter_parts.append(f"[0:v][1:v]xfade=transition={transition}:duration={transition_duration}:offset=4[v{i}]")
            else:
                filter_parts.append(f"[v{i-1}][{i+1}:v]xfade=transition={transition}:duration={transition_duration}:offset=4[v{i}]")
        
        filter_complex = ";".join(filter_parts)
        last_output = f"[v{len(input_paths)-2}]" if len(input_paths) > 2 else "[v0]"
        
        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", last_output,
            "-c:v", "libx264",
            "-preset", "fast",
            output_path
        ])
        
        return cmd
    
    def adjust_speed(
        self,
        input_path: str,
        output_path: str,
        speed: float
    ) -> bool:
        """调整视频速度"""
        if speed <= 0:
            return False
        
        try:
            # 视频和音频都需要调整
            video_filter = f"setpts={1/speed}*PTS"
            audio_filter = f"atempo={speed}" if 0.5 <= speed <= 2.0 else f"atempo={min(2.0, max(0.5, speed))}"
            
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-i", input_path,
                "-filter:v", video_filter,
                "-filter:a", audio_filter,
                "-c:v", "libx264",
                "-c:a", "aac",
                "-preset", "fast",
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"调整速度失败: {e}")
            return False
    
    def adjust_volume(
        self,
        input_path: str,
        output_path: str,
        volume: float
    ) -> bool:
        """调整音量 (volume: 1.0 = 原始, 2.0 = 两倍)"""
        try:
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-i", input_path,
                "-filter:a", f"volume={volume}",
                "-c:v", "copy",
                "-c:a", "aac",
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"调整音量失败: {e}")
            return False


class VideoEditorTab:
    """视频剪辑标签页"""
    
    def __init__(self, app):
        self.app = app
        self.editor = FFmpegEditor()
        self.current_project: Optional[EditProject] = None
        self.temp_dir = Path(tempfile.gettempdir()) / "video_editor_temp"
        self.temp_dir.mkdir(exist_ok=True)
    
    def create(self):
        """创建视频剪辑界面"""
        # FFmpeg 状态提示
        ffmpeg_available = self.editor.check_available()
        ffmpeg_text = "✅ FFmpeg: 可用" if ffmpeg_available else "❌ FFmpeg: 不可用"
        gr.Markdown(f"**{ffmpeg_text}**", elem_classes=["status-badge"])
        
        with gr.Row():
            # 左侧: 素材和片段列表
            with gr.Column(scale=1, min_width=280):
                with gr.Group():
                    gr.Markdown("### 📁 素材库")
                    video_input = gr.File(
                        label="上传视频",
                        file_types=["video"],
                        file_count="multiple"
                    )
                    load_project_videos_btn = gr.Button(
                        "📂 从当前项目加载", 
                        size="sm",
                        variant="secondary"
                    )
                    material_list = gr.Dataframe(
                        headers=["文件名", "时长", "分辨率"],
                        label="素材列表",
                        interactive=False,
                        max_height=180
                    )
                
                with gr.Group():
                    gr.Markdown("### 🎬 剪辑片段")
                    segment_list = gr.Dataframe(
                        headers=["#", "来源", "开始", "结束", "时长"],
                        label="片段列表",
                        interactive=False,
                        max_height=200
                    )
                    with gr.Row():
                        move_up_btn = gr.Button("⬆️ 上移", size="sm")
                        move_down_btn = gr.Button("⬇️ 下移", size="sm")
                        delete_segment_btn = gr.Button("🗑️ 删除", size="sm", variant="stop")
            
            # 中间: 预览和裁剪
            with gr.Column(scale=2, min_width=400):
                with gr.Group():
                    gr.Markdown("### 🎥 视频预览")
                    video_preview = gr.Video(
                        label="预览",
                        interactive=False,
                        height=280
                    )
                
                with gr.Group():
                    gr.Markdown("### ✂️ 裁剪控制")
                    with gr.Row():
                        start_time = gr.Number(label="开始 (秒)", value=0, minimum=0, scale=1)
                        end_time = gr.Number(label="结束 (秒)", value=0, minimum=0, scale=1)
                        video_duration = gr.Number(label="总时长", interactive=False, scale=1)
                    
                    with gr.Row():
                        start_slider = gr.Slider(
                            label="开始位置",
                            minimum=0, maximum=100, value=0, step=0.1,
                            interactive=True
                        )
                        end_slider = gr.Slider(
                            label="结束位置",
                            minimum=0, maximum=100, value=100, step=0.1,
                            interactive=True
                        )
                    
                    with gr.Row():
                        preview_clip_btn = gr.Button("👁️ 预览片段", variant="secondary")
                        add_clip_btn = gr.Button("➕ 添加到列表", variant="primary")
                
                selected_material = gr.Textbox(
                    label="当前素材",
                    interactive=False,
                    visible=False
                )
            
            # 右侧: 导出设置
            with gr.Column(scale=1, min_width=260):
                with gr.Group():
                    gr.Markdown("### 📤 导出设置")
                    output_name = gr.Textbox(
                        label="输出文件名",
                        value="edited_video",
                        placeholder="不含扩展名"
                    )
                    output_format = gr.Dropdown(
                        label="格式",
                        choices=["mp4", "mkv", "avi", "mov"],
                        value="mp4"
                    )
                    transition_type = gr.Dropdown(
                        label="转场效果",
                        choices=["无", "fade", "wipeleft", "wiperight", "slideup", "slidedown"],
                        value="无"
                    )
                    
                    with gr.Accordion("⚙️ 高级选项", open=False):
                        output_resolution = gr.Dropdown(
                            label="分辨率",
                            choices=["原始", "1920x1080", "1280x720", "720x480"],
                            value="原始"
                        )
                        output_fps = gr.Dropdown(
                            label="帧率",
                            choices=["原始", "60", "30", "24"],
                            value="原始"
                        )
                        video_quality = gr.Slider(
                            label="质量 (CRF)",
                            minimum=18, maximum=28, value=23, step=1,
                            info="越小质量越高"
                        )
                    
                    export_btn = gr.Button("🚀 导出视频", variant="primary")
                    export_status = gr.Textbox(label="状态", interactive=False, max_lines=2)
                    exported_video = gr.Video(label="导出结果", visible=False)
                
                with gr.Group():
                    gr.Markdown("### 🎛️ 快捷调整")
                    speed_value = gr.Slider(
                        label="播放速度",
                        minimum=0.5, maximum=2.0, value=1.0, step=0.1
                    )
                    apply_speed_btn = gr.Button("应用速度", size="sm")
                    
                    volume_value = gr.Slider(
                        label="音量",
                        minimum=0, maximum=3.0, value=1.0, step=0.1
                    )
                    apply_volume_btn = gr.Button("应用音量", size="sm")
        
        # 事件绑定
        video_input.change(
            fn=self._on_video_upload,
            inputs=[video_input],
            outputs=[material_list, video_preview, selected_material, video_duration, end_time, start_slider, end_slider]
        )
        
        load_project_videos_btn.click(
            fn=self._load_project_videos,
            outputs=[material_list]
        )
        
        material_list.select(
            fn=self._on_material_select,
            inputs=[material_list],
            outputs=[video_preview, selected_material, video_duration, end_time, start_slider, end_slider]
        )
        
        # 滑块同步到数字输入
        start_slider.change(
            fn=lambda x: x,
            inputs=[start_slider],
            outputs=[start_time]
        )
        end_slider.change(
            fn=lambda x: x,
            inputs=[end_slider],
            outputs=[end_time]
        )
        
        add_clip_btn.click(
            fn=self._add_clip,
            inputs=[selected_material, start_time, end_time],
            outputs=[segment_list]
        )
        
        # 需要存储选中的片段索引
        selected_segment_idx = gr.State(value=-1)
        
        segment_list.select(
            fn=self._on_segment_select,
            outputs=[selected_segment_idx]
        )
        
        delete_segment_btn.click(
            fn=self._delete_segment,
            inputs=[selected_segment_idx],
            outputs=[segment_list, selected_segment_idx]
        )
        
        move_up_btn.click(
            fn=self._move_segment_up,
            inputs=[selected_segment_idx],
            outputs=[segment_list, selected_segment_idx]
        )
        
        move_down_btn.click(
            fn=self._move_segment_down,
            inputs=[selected_segment_idx],
            outputs=[segment_list, selected_segment_idx]
        )
        
        export_btn.click(
            fn=self._export_video,
            inputs=[output_name, output_format, transition_type, output_resolution, video_quality],
            outputs=[export_status, exported_video]
        )
        
        preview_clip_btn.click(
            fn=self._preview_clip,
            inputs=[selected_material, start_time, end_time],
            outputs=[video_preview]
        )
    
    # ============ 回调方法 ============
    
    def _on_video_upload(self, files) -> Tuple:
        """处理视频上传"""
        if not files:
            return [], None, "", 0, 0, gr.update(maximum=100, value=0), gr.update(maximum=100, value=100)
        
        materials = []
        first_video = None
        first_duration = 0
        
        for f in files if isinstance(files, list) else [files]:
            file_path = f.name if hasattr(f, 'name') else str(f)
            info = self.editor.get_video_info(file_path)
            materials.append([
                Path(file_path).name,
                f"{info['duration']:.1f}s",
                f"{info['width']}x{info['height']}"
            ])
            
            if first_video is None:
                first_video = file_path
                first_duration = info['duration']
        
        return (
            materials,
            first_video,
            first_video or "",
            first_duration,
            first_duration,
            gr.update(maximum=first_duration, value=0),
            gr.update(maximum=first_duration, value=first_duration)
        )
    
    def _load_project_videos(self) -> List[List[str]]:
        """从当前项目加载视频"""
        if not self.app.current_project:
            return []
        
        videos_dir = self.app.current_project / "videos"
        if not videos_dir.exists():
            return []
        
        materials = []
        for video_file in videos_dir.glob("*.mp4"):
            info = self.editor.get_video_info(str(video_file))
            materials.append([
                video_file.name,
                f"{info['duration']:.1f}s",
                f"{info['width']}x{info['height']}"
            ])
        
        return materials
    
    def _on_material_select(self, evt: gr.SelectData, material_data) -> Tuple:
        """选择素材"""
        if not material_data or evt.index[0] >= len(material_data):
            return None, "", 0, 0, gr.update(), gr.update()
        
        row = material_data[evt.index[0]]
        filename = row[0]
        
        # 查找完整路径
        video_path = None
        if self.app.current_project:
            project_video = self.app.current_project / "videos" / filename
            if project_video.exists():
                video_path = str(project_video)
        
        if not video_path:
            # 尝试从临时目录查找
            temp_video = self.temp_dir / filename
            if temp_video.exists():
                video_path = str(temp_video)
        
        if not video_path:
            return None, "", 0, 0, gr.update(), gr.update()
        
        info = self.editor.get_video_info(video_path)
        duration = info['duration']
        
        return (
            video_path,
            video_path,
            duration,
            duration,
            gr.update(maximum=duration, value=0),
            gr.update(maximum=duration, value=duration)
        )
    
    def _on_time_range_change(self, time_range, duration) -> Tuple[float, float]:
        """时间范围滑块变化 - 已废弃，保留兼容"""
        if not time_range or not duration:
            return 0, 0
        start = time_range[0] if isinstance(time_range, list) else 0
        end = time_range[1] if isinstance(time_range, list) else duration
        return start, end
    
    def _on_segment_select(self, evt: gr.SelectData) -> int:
        """选择片段时记录索引"""
        if evt and hasattr(evt, 'index'):
            return evt.index[0]
        return -1
    
    def _add_clip(self, source_path: str, start: float, end: float) -> List[List[str]]:
        """添加片段到列表"""
        if not source_path or end <= start:
            return self._get_segment_list()
        
        if not self.current_project:
            self.current_project = EditProject(name="untitled")
        
        segment = ClipSegment(
            source_path=source_path,
            start_time=start,
            end_time=end
        )
        self.current_project.add_segment(segment)
        
        return self._get_segment_list()
    
    def _get_segment_list(self) -> List[List[str]]:
        """获取片段列表数据"""
        if not self.current_project:
            return []
        
        return [
            [
                str(i + 1),
                Path(seg.source_path).name[:20],
                f"{seg.start_time:.1f}s",
                f"{seg.end_time:.1f}s",
                f"{seg.duration:.1f}s"
            ]
            for i, seg in enumerate(self.current_project.segments)
        ]
    
    def _delete_segment(self, idx: int) -> Tuple[List[List[str]], int]:
        """删除选中的片段"""
        if not self.current_project or idx < 0:
            return self._get_segment_list(), -1
        
        self.current_project.remove_segment(idx)
        return self._get_segment_list(), -1
    
    def _move_segment_up(self, idx: int) -> Tuple[List[List[str]], int]:
        """上移片段"""
        if not self.current_project or idx < 0:
            return self._get_segment_list(), idx
        
        if idx > 0:
            segments = self.current_project.segments
            segments[idx], segments[idx-1] = segments[idx-1], segments[idx]
            for i, seg in enumerate(segments):
                seg.order = i
            return self._get_segment_list(), idx - 1
        
        return self._get_segment_list(), idx
    
    def _move_segment_down(self, idx: int) -> Tuple[List[List[str]], int]:
        """下移片段"""
        if not self.current_project or idx < 0:
            return self._get_segment_list(), idx
        
        segments = self.current_project.segments
        if idx < len(segments) - 1:
            segments[idx], segments[idx+1] = segments[idx+1], segments[idx]
            for i, seg in enumerate(segments):
                seg.order = i
            return self._get_segment_list(), idx + 1
        
        return self._get_segment_list(), idx
    
    def _preview_clip(self, source: str, start: float, end: float) -> Optional[str]:
        """预览裁剪片段"""
        if not source or end <= start:
            return None
        
        # 生成临时预览文件
        preview_path = self.temp_dir / f"preview_{int(start)}_{int(end)}.mp4"
        
        if self.editor.trim_video(source, str(preview_path), start, end):
            return str(preview_path)
        return None
    
    def _export_video(
        self,
        output_name: str,
        output_format: str,
        transition: str,
        resolution: str,
        quality: int
    ) -> Tuple[str, Optional[str]]:
        """导出视频"""
        if not self.current_project or not self.current_project.segments:
            return "错误: 没有片段可导出", None
        
        if not output_name:
            output_name = "edited_video"
        
        try:
            # 1. 先裁剪每个片段
            temp_clips = []
            for i, seg in enumerate(self.current_project.segments):
                clip_path = self.temp_dir / f"clip_{i}.mp4"
                if not self.editor.trim_video(
                    seg.source_path,
                    str(clip_path),
                    seg.start_time,
                    seg.end_time,
                    reencode=True
                ):
                    return f"错误: 裁剪片段 {i+1} 失败", None
                temp_clips.append(str(clip_path))
            
            # 2. 拼接所有片段
            output_dir = self.app.current_project / "output" if self.app.current_project else self.temp_dir
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / f"{output_name}.{output_format}"
            
            transition_type = None if transition == "无" else transition
            
            if not self.editor.concat_videos(temp_clips, str(output_path), transition_type):
                return "错误: 拼接视频失败", None
            
            # 3. 清理临时文件
            for clip in temp_clips:
                Path(clip).unlink(missing_ok=True)
            
            self.current_project.output_path = str(output_path)
            
            return f"导出成功: {output_path}", str(output_path)
        
        except Exception as e:
            logger.error(f"导出视频失败: {e}")
            return f"错误: {e}", None
