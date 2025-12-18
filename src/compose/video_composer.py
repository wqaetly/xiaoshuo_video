"""视频合成器"""
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..utils.logger import get_logger
from ..utils.file_utils import ensure_dir

logger = get_logger(__name__)


class VideoComposer:
    """视频合成器 - 使用FFmpeg合成最终视频"""

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path
        self._check_ffmpeg()

    def _check_ffmpeg(self) -> bool:
        """检查FFmpeg是否可用"""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                logger.info("FFmpeg 可用")
                return True
            return False
        except FileNotFoundError:
            logger.error("FFmpeg 未找到，请确保已安装")
            return False

    def compose(
        self,
        clips: List[Dict[str, Any]],
        output_path: Path,
        bgm_path: Optional[Path] = None,
        bgm_volume: float = 0.3,
        transition_duration: float = 0.5
    ) -> Path:
        """
        合成最终视频

        Args:
            clips: 视频片段列表，每个包含:
                - video: 视频文件路径
                - audio: 音频文件路径
                - subtitle: 字幕信息
            output_path: 输出文件路径
            bgm_path: 背景音乐路径
            bgm_volume: 背景音乐音量 (0-1)
            transition_duration: 转场时长
        """
        ensure_dir(output_path.parent)

        # 1. 创建临时文件列表
        temp_dir = output_path.parent / "temp"
        ensure_dir(temp_dir)

        # 2. 预处理每个片段 (添加音频)
        processed_clips = []
        for i, clip in enumerate(clips):
            processed_path = temp_dir / f"clip_{i:04d}.mp4"
            self._process_clip(clip, processed_path)
            processed_clips.append(processed_path)

        # 3. 创建concat文件
        concat_file = temp_dir / "concat.txt"
        with open(concat_file, "w", encoding="utf-8") as f:
            for clip_path in processed_clips:
                f.write(f"file '{clip_path.as_posix()}'\n")

        # 4. 合并视频
        merged_path = temp_dir / "merged.mp4"
        self._concat_videos(concat_file, merged_path)

        # 5. 添加背景音乐 (如果有)
        if bgm_path and bgm_path.exists():
            self._add_bgm(merged_path, bgm_path, output_path, bgm_volume)
        else:
            # 直接复制
            subprocess.run([
                self.ffmpeg_path, "-y",
                "-i", str(merged_path),
                "-c", "copy",
                str(output_path)
            ], capture_output=True)

        # 6. 清理临时文件
        self._cleanup_temp(temp_dir)

        logger.info(f"视频合成完成: {output_path}")
        return output_path

    def _process_clip(self, clip: Dict[str, Any], output_path: Path) -> None:
        """处理单个视频片段 - 合并视频和音频"""
        video_path = clip.get("video")
        audio_path = clip.get("audio")

        if not video_path or not Path(video_path).exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        cmd = [self.ffmpeg_path, "-y"]

        # 输入视频
        cmd.extend(["-i", str(video_path)])

        # 输入音频 (如果有)
        if audio_path and Path(audio_path).exists():
            cmd.extend(["-i", str(audio_path)])
            # 合并音视频，使用视频时长
            cmd.extend([
                "-c:v", "copy",
                "-c:a", "aac",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest"
            ])
        else:
            # 仅复制视频，添加静音音轨
            cmd.extend([
                "-c:v", "copy",
                "-f", "lavfi",
                "-i", "anullsrc=r=44100:cl=stereo",
                "-c:a", "aac",
                "-shortest"
            ])

        cmd.append(str(output_path))

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"处理片段失败: {result.stderr}")

    def _concat_videos(self, concat_file: Path, output_path: Path) -> None:
        """使用concat demuxer合并视频"""
        cmd = [
            self.ffmpeg_path, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"合并视频失败: {result.stderr}")
            raise RuntimeError("视频合并失败")

    def _add_bgm(
        self,
        video_path: Path,
        bgm_path: Path,
        output_path: Path,
        volume: float
    ) -> None:
        """添加背景音乐"""
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", str(video_path),
            "-i", str(bgm_path),
            "-filter_complex",
            f"[1:a]volume={volume}[bgm];[0:a][bgm]amix=inputs=2:duration=first[aout]",
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"添加BGM失败: {result.stderr}")
            # 回退：不添加BGM
            subprocess.run([
                self.ffmpeg_path, "-y",
                "-i", str(video_path),
                "-c", "copy",
                str(output_path)
            ])

    def _cleanup_temp(self, temp_dir: Path) -> None:
        """清理临时文件"""
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")

    def add_subtitles(
        self,
        video_path: Path,
        subtitle_path: Path,
        output_path: Path,
        style: str = "FontSize=24,PrimaryColour=&HFFFFFF&"
    ) -> Path:
        """为视频添加字幕"""
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", str(video_path),
            "-vf", f"subtitles={subtitle_path}:force_style='{style}'",
            "-c:a", "copy",
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"添加字幕失败: {result.stderr}")
            raise RuntimeError("字幕添加失败")

        return output_path

    def create_preview(
        self,
        video_path: Path,
        output_path: Path,
        max_duration: float = 30.0,
        scale: str = "640:-1"
    ) -> Path:
        """创建预览视频"""
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", str(video_path),
            "-t", str(max_duration),
            "-vf", f"scale={scale}",
            "-c:v", "libx264",
            "-crf", "28",
            "-c:a", "aac",
            "-b:a", "128k",
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"创建预览失败: {result.stderr}")

        return output_path
