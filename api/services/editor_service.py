"""
视频编辑服务 - 封装 FFmpeg 视频处理功能
"""
import subprocess
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any

from src.utils.config import get_config, Config
from src.utils.file_utils import load_json, save_json, ensure_dir
from src.utils.logger import get_logger

logger = get_logger("api.editor_service")


class EditorService:
    """视频编辑服务"""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.projects_dir = Path(self.config.paths.projects_dir)
        self.ffmpeg_path = self.config.local.ffmpeg_path or "ffmpeg"
        self.ffprobe_path = self.config.local.ffprobe_path or "ffprobe"

    def get_media_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """获取媒体文件信息"""
        try:
            cmd = [
                self.ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return None

            import json
            data = json.loads(result.stdout)
            
            video_stream = next(
                (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
                None
            )
            
            info = {
                "path": file_path,
                "duration": float(data.get("format", {}).get("duration", 0)),
                "width": video_stream.get("width") if video_stream else None,
                "height": video_stream.get("height") if video_stream else None,
                "fps": self._parse_fps(video_stream.get("r_frame_rate")) if video_stream else None,
                "codec": video_stream.get("codec_name") if video_stream else None,
            }
            return info
        except Exception as e:
            logger.error(f"获取媒体信息失败: {e}")
            return None

    def _parse_fps(self, fps_str: Optional[str]) -> Optional[float]:
        """解析帧率字符串"""
        if not fps_str:
            return None
        try:
            if "/" in fps_str:
                num, den = fps_str.split("/")
                return float(num) / float(den)
            return float(fps_str)
        except (ValueError, ZeroDivisionError):
            return None

    def list_materials(self, project_name: str) -> Dict[str, Any]:
        """列出项目素材"""
        project_path = self.projects_dir / project_name
        if not project_path.exists():
            return {"videos": [], "audios": [], "images": []}

        videos = []
        audios = []
        images = []

        # 扫描视频
        video_dir = project_path / "videos"
        if video_dir.exists():
            for f in video_dir.glob("*.mp4"):
                info = self.get_media_info(str(f))
                if info:
                    videos.append(info)

        # 扫描音频
        audio_dir = project_path / "audio"
        if audio_dir.exists():
            for f in audio_dir.glob("*.wav"):
                info = self.get_media_info(str(f))
                if info:
                    audios.append(info)

        # 扫描图像
        images_dir = project_path / "images"
        if images_dir.exists():
            images = [str(f) for f in images_dir.glob("*.png")]

        return {"videos": videos, "audios": audios, "images": images}

    def get_timeline(self, project_name: str) -> Dict[str, Any]:
        """获取时间轴数据"""
        timeline_path = self.projects_dir / project_name / "timeline.json"
        if timeline_path.exists():
            return load_json(timeline_path)
        return {
            "video_clips": [],
            "audio_clips": [],
            "subtitle_clips": [],
            "total_duration": 0.0,
        }

    def save_timeline(self, project_name: str, timeline: Dict[str, Any]) -> Dict[str, Any]:
        """保存时间轴数据"""
        timeline_path = self.projects_dir / project_name / "timeline.json"
        ensure_dir(timeline_path.parent)
        save_json(timeline_path, timeline)
        return timeline

    def trim_video(
        self,
        project_name: str,
        source: str,
        start_time: float,
        end_time: float,
        output_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """裁剪视频"""
        output_dir = self.projects_dir / project_name / "edited"
        ensure_dir(output_dir)

        output_name = output_name or f"trim_{uuid.uuid4().hex[:8]}.mp4"
        output_path = output_dir / output_name

        try:
            cmd = [
                self.ffmpeg_path, "-y",
                "-i", source,
                "-ss", str(start_time),
                "-to", str(end_time),
                "-c:v", "libx264",
                "-c:a", "aac",
                "-preset", "fast",
                str(output_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                logger.error(f"裁剪失败: {result.stderr}")
                return None
            return self.get_media_info(str(output_path))
        except Exception as e:
            logger.error(f"裁剪视频失败: {e}")
            return None

    def concat_videos(
        self,
        project_name: str,
        clips: List[Dict[str, Any]],
        output_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """拼接视频"""
        import tempfile

        output_dir = self.projects_dir / project_name / "edited"
        ensure_dir(output_dir)

        output_name = output_name or f"concat_{uuid.uuid4().hex[:8]}.mp4"
        output_path = output_dir / output_name

        try:
            # 创建文件列表
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                for clip in clips:
                    source = clip.get("source", "")
                    escaped = source.replace("'", "'\\''")
                    f.write(f"file '{escaped}'\n")
                list_file = f.name

            cmd = [
                self.ffmpeg_path, "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", list_file,
                "-c", "copy",
                str(output_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            Path(list_file).unlink(missing_ok=True)

            if result.returncode != 0:
                logger.error(f"拼接失败: {result.stderr}")
                return None
            return self.get_media_info(str(output_path))
        except Exception as e:
            logger.error(f"拼接视频失败: {e}")
            return None

    def adjust_speed(
        self,
        project_name: str,
        source: str,
        speed: float,
        output_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """调整视频速度"""
        if speed <= 0:
            return None

        output_dir = self.projects_dir / project_name / "edited"
        ensure_dir(output_dir)

        output_name = output_name or f"speed_{uuid.uuid4().hex[:8]}.mp4"
        output_path = output_dir / output_name

        try:
            video_filter = f"setpts={1/speed}*PTS"
            audio_filter = f"atempo={min(2.0, max(0.5, speed))}"

            cmd = [
                self.ffmpeg_path, "-y",
                "-i", source,
                "-filter:v", video_filter,
                "-filter:a", audio_filter,
                "-c:v", "libx264",
                "-c:a", "aac",
                "-preset", "fast",
                str(output_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                logger.error(f"调速失败: {result.stderr}")
                return None
            return self.get_media_info(str(output_path))
        except Exception as e:
            logger.error(f"调整速度失败: {e}")
            return None

    def adjust_volume(
        self,
        project_name: str,
        source: str,
        volume: float,
        output_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """调整音量"""
        output_dir = self.projects_dir / project_name / "edited"
        ensure_dir(output_dir)

        output_name = output_name or f"volume_{uuid.uuid4().hex[:8]}.mp4"
        output_path = output_dir / output_name

        try:
            cmd = [
                self.ffmpeg_path, "-y",
                "-i", source,
                "-af", f"volume={volume}",
                "-c:v", "copy",
                "-c:a", "aac",
                str(output_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                logger.error(f"调整音量失败: {result.stderr}")
                return None
            return self.get_media_info(str(output_path))
        except Exception as e:
            logger.error(f"调整音量失败: {e}")
            return None


# 单例模式
_editor_service: Optional[EditorService] = None


def get_editor_service() -> EditorService:
    """获取编辑服务实例"""
    global _editor_service
    if _editor_service is None:
        _editor_service = EditorService()
    return _editor_service

