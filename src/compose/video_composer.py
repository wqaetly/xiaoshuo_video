"""视频合成器"""
import subprocess
import shutil
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..utils.logger import get_logger
from ..utils.file_utils import ensure_dir

logger = get_logger(__name__)


def get_ffmpeg_path() -> str:
    """获取 FFmpeg 路径，优先使用项目内置版本"""
    # 项目内置路径
    project_root = Path(__file__).parent.parent.parent
    import sys
    if sys.platform == "win32":
        project_ffmpeg = project_root / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe"
    else:
        project_ffmpeg = project_root / "tools" / "ffmpeg" / "ffmpeg"
    
    if project_ffmpeg.exists():
        return str(project_ffmpeg)
    
    # 系统路径
    system_ffmpeg = shutil.which("ffmpeg")
    return system_ffmpeg or "ffmpeg"


def get_ffprobe_path() -> str:
    """获取 FFprobe 路径，优先使用项目内置版本"""
    project_root = Path(__file__).parent.parent.parent
    import sys
    if sys.platform == "win32":
        project_ffprobe = project_root / "tools" / "ffmpeg" / "bin" / "ffprobe.exe"
    else:
        project_ffprobe = project_root / "tools" / "ffmpeg" / "ffprobe"
    
    if project_ffprobe.exists():
        return str(project_ffprobe)
    
    system_ffprobe = shutil.which("ffprobe")
    return system_ffprobe or "ffprobe"


class TransitionType(Enum):
    """转场类型"""
    NONE = "none"
    FADE = "fade"
    DISSOLVE = "dissolve"
    WIPE_LEFT = "wipeleft"
    WIPE_RIGHT = "wiperight"
    SLIDE_LEFT = "slideleft"
    SLIDE_RIGHT = "slideright"
    CIRCLE_OPEN = "circleopen"
    CIRCLE_CLOSE = "circleclose"


class VideoComposer:
    """视频合成器 - 使用FFmpeg合成最终视频"""

    def __init__(self, ffmpeg_path: str = None):
        self.ffmpeg_path = ffmpeg_path or get_ffmpeg_path()
        self.ffprobe_path = get_ffprobe_path()
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
        transition_type: TransitionType = TransitionType.FADE,
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
            transition_type: 转场类型
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

        # 4. 合并视频 (带转场效果)
        merged_path = temp_dir / "merged.mp4"
        if transition_type == TransitionType.NONE or len(processed_clips) < 2:
            self._concat_videos(concat_file, merged_path)
        else:
            self._concat_with_transitions(
                processed_clips, 
                merged_path,
                transition_type,
                transition_duration
            )

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
        """处理单个片段 - 支持视频或图像输入，合并音频"""
        source_path = clip.get("video")
        audio_path = clip.get("audio")
        duration = clip.get("duration", 5.0)

        if not source_path or not Path(source_path).exists():
            raise FileNotFoundError(f"源文件不存在: {source_path}")

        source_path = Path(source_path)
        is_image = source_path.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]

        if is_image:
            # 图像转视频
            self._image_to_video_with_audio(source_path, audio_path, output_path, duration)
        else:
            # 视频处理
            self._video_with_audio(source_path, audio_path, output_path)

    def _image_to_video_with_audio(
        self,
        image_path: Path,
        audio_path: Optional[Path],
        output_path: Path,
        duration: float
    ) -> None:
        """将图像转换为视频并添加音频"""
        cmd = [self.ffmpeg_path, "-y"]

        # 循环输入图像
        cmd.extend(["-loop", "1", "-i", str(image_path)])

        if audio_path and Path(audio_path).exists():
            # 有音频时，使用音频时长
            cmd.extend(["-i", str(audio_path)])
            cmd.extend([
                "-c:v", "libx264",
                "-tune", "stillimage",
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-shortest",
                "-t", str(duration + 1),  # 最大时长限制
            ])
        else:
            # 无音频时，使用指定时长并添加静音
            cmd.extend([
                "-f", "lavfi",
                "-i", "anullsrc=r=44100:cl=stereo",
                "-c:v", "libx264",
                "-tune", "stillimage",
                "-c:a", "aac",
                "-pix_fmt", "yuv420p",
                "-t", str(duration),
            ])

        cmd.append(str(output_path))

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"图像转视频失败: {result.stderr}")
            raise RuntimeError(f"图像转视频失败: {result.stderr[:200]}")

    def _video_with_audio(
        self,
        video_path: Path,
        audio_path: Optional[Path],
        output_path: Path
    ) -> None:
        """处理视频并合并音频"""
        cmd = [self.ffmpeg_path, "-y"]

        cmd.extend(["-i", str(video_path)])

        if audio_path and Path(audio_path).exists():
            cmd.extend(["-i", str(audio_path)])
            cmd.extend([
                "-c:v", "copy",
                "-c:a", "aac",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest"
            ])
        else:
            cmd.extend([
                "-f", "lavfi",
                "-i", "anullsrc=r=44100:cl=stereo",
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest"
            ])

        cmd.append(str(output_path))

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"处理视频片段失败: {result.stderr}")

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

    def _concat_with_transitions(
        self,
        clips: List[Path],
        output_path: Path,
        transition_type: TransitionType,
        transition_duration: float
    ) -> None:
        """使用xfade滤镜合并视频 (带转场效果)"""
        if len(clips) < 2:
            return
        
        inputs = []
        for clip in clips:
            inputs.extend(["-i", str(clip)])
        
        filter_parts = []
        n = len(clips)
        
        if transition_type == TransitionType.FADE:
            for i in range(n - 1):
                if i == 0:
                    filter_parts.append(
                        f"[0:v][1:v]xfade=transition=fade:duration={transition_duration}:offset=auto[v01]"
                    )
                else:
                    prev_out = f"v{str(i-1).zfill(2)}{str(i).zfill(2)}"
                    curr_out = f"v{str(i).zfill(2)}{str(i+1).zfill(2)}"
                    filter_parts.append(
                        f"[{prev_out}][{i+1}:v]xfade=transition=fade:duration={transition_duration}:offset=auto[{curr_out}]"
                    )
            
            for i in range(n - 1):
                if i == 0:
                    filter_parts.append(
                        f"[0:a][1:a]acrossfade=d={transition_duration}[a01]"
                    )
                else:
                    prev_out = f"a{str(i-1).zfill(2)}{str(i).zfill(2)}"
                    curr_out = f"a{str(i).zfill(2)}{str(i+1).zfill(2)}"
                    filter_parts.append(
                        f"[{prev_out}][{i+1}:a]acrossfade=d={transition_duration}[{curr_out}]"
                    )
            
            final_v = f"v{str(n-2).zfill(2)}{str(n-1).zfill(2)}" if n > 2 else "v01"
            final_a = f"a{str(n-2).zfill(2)}{str(n-1).zfill(2)}" if n > 2 else "a01"
            
            filter_complex = ";".join(filter_parts)
            
            cmd = [
                self.ffmpeg_path, "-y",
                *inputs,
                "-filter_complex", filter_complex,
                "-map", f"[{final_v}]",
                "-map", f"[{final_a}]",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning(f"转场合并失败，尝试简单淡入淡出: {result.stderr}")
                self._concat_with_simple_fade(clips, output_path, transition_duration)
        else:
            self._concat_with_simple_fade(clips, output_path, transition_duration)

    def _concat_with_simple_fade(
        self,
        clips: List[Path],
        output_path: Path,
        fade_duration: float
    ) -> None:
        """使用简单的淡入淡出效果"""
        temp_dir = output_path.parent / "fade_temp"
        ensure_dir(temp_dir)
        
        faded_clips = []
        for i, clip in enumerate(clips):
            faded_path = temp_dir / f"faded_{i:04d}.mp4"
            
            duration = self._get_video_duration(clip)
            if duration <= 0:
                duration = 5.0
            
            fade_in_filter = f"fade=t=in:st=0:d={fade_duration}"
            fade_out_filter = f"fade=t=out:st={max(0, duration - fade_duration)}:d={fade_duration}"
            afade_in = f"afade=t=in:st=0:d={fade_duration}"
            afade_out = f"afade=t=out:st={max(0, duration - fade_duration)}:d={fade_duration}"
            
            cmd = [
                self.ffmpeg_path, "-y",
                "-i", str(clip),
                "-vf", f"{fade_in_filter},{fade_out_filter}",
                "-af", f"{afade_in},{afade_out}",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                str(faded_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                faded_clips.append(faded_path)
            else:
                logger.warning(f"淡入淡出失败，使用原片: {result.stderr}")
                faded_clips.append(clip)
        
        concat_file = temp_dir / "concat.txt"
        with open(concat_file, "w", encoding="utf-8") as f:
            for clip_path in faded_clips:
                f.write(f"file '{clip_path.as_posix()}'\n")
        
        self._concat_videos(concat_file, output_path)
        
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except:
            pass

    def _get_video_duration(self, video_path: Path) -> float:
        """获取视频时长"""
        cmd = [
            self.ffprobe_path,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except:
            pass
        
        return -1

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
