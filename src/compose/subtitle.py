"""字幕生成器"""
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..utils.logger import get_logger
from ..utils.file_utils import ensure_dir

logger = get_logger(__name__)


class SubtitleGenerator:
    """字幕生成器 - 支持SRT和ASS格式"""

    def __init__(self):
        self.default_style = {
            "font_name": "Microsoft YaHei",
            "font_size": 24,
            "primary_color": "&HFFFFFF",  # 白色
            "outline_color": "&H000000",  # 黑色描边
            "outline_width": 2,
            "shadow": 1
        }

    def generate_srt(
        self,
        scenes: List[Dict[str, Any]],
        output_path: Path
    ) -> Path:
        """生成SRT字幕文件"""
        ensure_dir(output_path.parent)

        srt_content = []
        current_time = 0.0
        index = 1

        for scene in scenes:
            subtitle = scene.get("subtitle", {})
            text = subtitle.get("text", "")
            duration = scene.get("duration", 5.0)

            if text:
                start_time = self._format_srt_time(current_time)
                end_time = self._format_srt_time(current_time + duration)

                srt_content.append(f"{index}")
                srt_content.append(f"{start_time} --> {end_time}")
                srt_content.append(text)
                srt_content.append("")

                index += 1

            current_time += duration

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_content))

        logger.info(f"SRT字幕已生成: {output_path}")
        return output_path

    def generate_ass(
        self,
        scenes: List[Dict[str, Any]],
        output_path: Path,
        resolution: str = "1280x720",
        style: Optional[Dict[str, Any]] = None
    ) -> Path:
        """生成ASS字幕文件"""
        ensure_dir(output_path.parent)

        style = style or self.default_style
        width, height = map(int, resolution.split("x"))

        # ASS头部
        ass_header = f"""[Script Info]
Title: Generated Subtitles
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Narration,{style['font_name']},{style['font_size']},{style['primary_color']},&H000000FF,{style['outline_color']},&H00000000,0,0,0,0,100,100,0,0,1,{style['outline_width']},{style['shadow']},2,10,10,30,1
Style: Dialogue,{style['font_name']},{style['font_size']},&H00FFFF00,&H000000FF,{style['outline_color']},&H00000000,0,0,0,0,100,100,0,0,1,{style['outline_width']},{style['shadow']},2,10,10,30,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        # 生成事件
        events = []
        current_time = 0.0

        for scene in scenes:
            subtitle = scene.get("subtitle", {})
            text = subtitle.get("text", "")
            duration = scene.get("duration", 5.0)
            style_name = "Dialogue" if subtitle.get("style") == "dialogue" else "Narration"
            character = subtitle.get("character", "")

            if text:
                start_time = self._format_ass_time(current_time)
                end_time = self._format_ass_time(current_time + duration)

                # 处理多行文本
                text = text.replace("\n", "\\N")

                # 添加角色名 (如果是对话)
                if character and style_name == "Dialogue":
                    text = f"【{character}】{text}"

                events.append(
                    f"Dialogue: 0,{start_time},{end_time},{style_name},,0,0,0,,{text}"
                )

            current_time += duration

        # 写入文件
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ass_header)
            f.write("\n".join(events))

        logger.info(f"ASS字幕已生成: {output_path}")
        return output_path

    def _format_srt_time(self, seconds: float) -> str:
        """格式化SRT时间 (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _format_ass_time(self, seconds: float) -> str:
        """格式化ASS时间 (H:MM:SS.cc)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centis = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"

    def create_timed_subtitles(
        self,
        audio_timestamps: List[Dict[str, Any]],
        output_path: Path,
        format: str = "srt"
    ) -> Path:
        """根据音频时间戳创建精确字幕"""
        ensure_dir(output_path.parent)

        if format == "srt":
            return self._create_timed_srt(audio_timestamps, output_path)
        else:
            return self._create_timed_ass(audio_timestamps, output_path)

    def _create_timed_srt(
        self,
        timestamps: List[Dict[str, Any]],
        output_path: Path
    ) -> Path:
        """创建带精确时间戳的SRT"""
        srt_content = []

        for i, ts in enumerate(timestamps, 1):
            start = ts.get("start", 0.0)
            end = ts.get("end", start + 3.0)
            text = ts.get("text", "")

            if text:
                start_time = self._format_srt_time(start)
                end_time = self._format_srt_time(end)

                srt_content.append(f"{i}")
                srt_content.append(f"{start_time} --> {end_time}")
                srt_content.append(text)
                srt_content.append("")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_content))

        return output_path

    def _create_timed_ass(
        self,
        timestamps: List[Dict[str, Any]],
        output_path: Path
    ) -> Path:
        """创建带精确时间戳的ASS"""
        # 简化实现，调用generate_ass
        scenes = []
        prev_end = 0.0

        for ts in timestamps:
            start = ts.get("start", prev_end)
            end = ts.get("end", start + 3.0)

            scenes.append({
                "duration": end - start,
                "subtitle": {
                    "text": ts.get("text", ""),
                    "style": ts.get("style", "narration"),
                    "character": ts.get("character")
                }
            })
            prev_end = end

        return self.generate_ass(scenes, output_path)
