"""音频混合器"""
import subprocess
from pathlib import Path
from typing import List, Optional
from ..utils.logger import get_logger
from ..utils.file_utils import ensure_dir

logger = get_logger(__name__)


class AudioMixer:
    """音频混合器"""

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path

    def mix_audio(
        self,
        audio_files: List[Path],
        output_path: Path,
        volumes: Optional[List[float]] = None
    ) -> Path:
        """混合多个音频文件"""
        ensure_dir(output_path.parent)

        if not audio_files:
            raise ValueError("音频文件列表为空")

        if len(audio_files) == 1:
            # 单个文件，直接复制
            subprocess.run([
                self.ffmpeg_path, "-y",
                "-i", str(audio_files[0]),
                "-c:a", "copy",
                str(output_path)
            ])
            return output_path

        # 多个文件，混合
        volumes = volumes or [1.0] * len(audio_files)

        cmd = [self.ffmpeg_path, "-y"]

        # 添加输入
        for audio_path in audio_files:
            cmd.extend(["-i", str(audio_path)])

        # 构建filter_complex
        filter_parts = []
        for i, vol in enumerate(volumes):
            filter_parts.append(f"[{i}:a]volume={vol}[a{i}]")

        inputs = "".join(f"[a{i}]" for i in range(len(audio_files)))
        filter_parts.append(f"{inputs}amix=inputs={len(audio_files)}:duration=longest[aout]")

        filter_complex = ";".join(filter_parts)

        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", "[aout]",
            "-c:a", "aac",
            str(output_path)
        ])

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"音频混合失败: {result.stderr}")
            raise RuntimeError("音频混合失败")

        return output_path

    def concat_audio(
        self,
        audio_files: List[Path],
        output_path: Path
    ) -> Path:
        """连接多个音频文件"""
        ensure_dir(output_path.parent)

        if not audio_files:
            raise ValueError("音频文件列表为空")

        # 创建临时concat文件
        concat_file = output_path.parent / "audio_concat.txt"
        with open(concat_file, "w", encoding="utf-8") as f:
            for audio_path in audio_files:
                f.write(f"file '{audio_path.as_posix()}'\n")

        cmd = [
            self.ffmpeg_path, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c:a", "aac",
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # 清理临时文件
        try:
            concat_file.unlink()
        except:
            pass

        if result.returncode != 0:
            logger.error(f"音频连接失败: {result.stderr}")
            raise RuntimeError("音频连接失败")

        return output_path

    def add_silence(
        self,
        duration: float,
        output_path: Path,
        sample_rate: int = 44100
    ) -> Path:
        """生成静音音频"""
        ensure_dir(output_path.parent)

        cmd = [
            self.ffmpeg_path, "-y",
            "-f", "lavfi",
            "-i", f"anullsrc=r={sample_rate}:cl=stereo",
            "-t", str(duration),
            "-c:a", "aac",
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"生成静音失败: {result.stderr}")

        return output_path

    def normalize_audio(
        self,
        input_path: Path,
        output_path: Path,
        target_loudness: float = -16.0
    ) -> Path:
        """音频响度标准化"""
        ensure_dir(output_path.parent)

        cmd = [
            self.ffmpeg_path, "-y",
            "-i", str(input_path),
            "-af", f"loudnorm=I={target_loudness}:LRA=11:TP=-1.5",
            "-c:a", "aac",
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"音频标准化失败: {result.stderr}")

        return output_path
