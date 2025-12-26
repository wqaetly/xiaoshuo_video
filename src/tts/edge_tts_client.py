"""Edge TTS 客户端 - 微软Edge浏览器TTS API"""
import asyncio
import subprocess
import shutil
import tempfile
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from ..utils.logger import get_logger

logger = get_logger(__name__)


def get_ffmpeg_path() -> str:
    """获取 FFmpeg 路径，优先使用项目内置版本"""
    project_root = Path(__file__).parent.parent.parent
    if sys.platform == "win32":
        project_ffmpeg = project_root / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe"
    else:
        project_ffmpeg = project_root / "tools" / "ffmpeg" / "ffmpeg"
    
    if project_ffmpeg.exists():
        return str(project_ffmpeg)
    
    system_ffmpeg = shutil.which("ffmpeg")
    return system_ffmpeg or "ffmpeg"


EDGE_VOICES = {
    # 中文
    "zh_male_yunxi": "zh-CN-YunxiNeural",
    "zh_male_yunyang": "zh-CN-YunyangNeural",
    "zh_female_xiaoxiao": "zh-CN-XiaoxiaoNeural",
    "zh_female_xiaoyi": "zh-CN-XiaoyiNeural",
    "zh_male_narrator": "zh-CN-YunjianNeural",
    "zh_female_narrator": "zh-CN-XiaoshuangNeural",
    # 英文
    "en_male_guy": "en-US-GuyNeural",
    "en_female_jenny": "en-US-JennyNeural",
    "en_male_narrator": "en-US-ChristopherNeural",
    # 日语
    "ja_male": "ja-JP-KeitaNeural",
    "ja_female": "ja-JP-NanamiNeural",
}

DEFAULT_VOICE = "zh-CN-YunxiNeural"


class AudioData:
    """音频数据封装"""

    def __init__(self, data: bytes, sample_rate: int = 24000, duration: float = 0.0):
        self.data = data
        self.sample_rate = sample_rate
        self.duration = duration

    def save(self, path: Union[str, Path]) -> None:
        """保存音频文件"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(self.data)

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "AudioData":
        """从文件加载"""
        path = Path(path)
        with open(path, "rb") as f:
            data = f.read()
        return cls(data=data)


class EdgeTTSClient:
    """Edge TTS客户端 - 使用edge-tts库"""

    def __init__(self, default_voice: str = DEFAULT_VOICE):
        self.default_voice = default_voice
        self._check_edge_tts()
        
        self.voice_presets = {
            "male_heroic": EDGE_VOICES.get("zh_male_yunyang", DEFAULT_VOICE),
            "male_gentle": EDGE_VOICES.get("zh_male_yunxi", DEFAULT_VOICE),
            "female_gentle": EDGE_VOICES.get("zh_female_xiaoxiao", DEFAULT_VOICE),
            "female_sweet": EDGE_VOICES.get("zh_female_xiaoyi", DEFAULT_VOICE),
            "narrator_epic": EDGE_VOICES.get("zh_male_narrator", DEFAULT_VOICE),
            "narrator_calm": EDGE_VOICES.get("zh_female_narrator", DEFAULT_VOICE),
        }

    def _check_edge_tts(self) -> bool:
        """检查edge-tts是否可用"""
        try:
            import edge_tts
            return True
        except ImportError:
            logger.warning("edge-tts未安装，请运行: pip install edge-tts")
            return False

    def check_health(self) -> bool:
        """检查服务是否可用"""
        return self._check_edge_tts()

    async def list_voices(self) -> List[Dict[str, str]]:
        """获取可用音色列表"""
        try:
            import edge_tts
            voices = await edge_tts.list_voices()
            return [
                {
                    "name": v["Name"],
                    "short_name": v["ShortName"],
                    "gender": v["Gender"],
                    "locale": v["Locale"],
                }
                for v in voices
            ]
        except Exception as e:
            logger.error(f"获取音色列表失败: {e}")
            return []

    def list_voices_sync(self) -> List[Dict[str, str]]:
        """同步获取音色列表"""
        return asyncio.run(self.list_voices())

    async def synthesize_async(
        self,
        text: str,
        voice_id: str = None,
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz"
    ) -> AudioData:
        """异步合成语音"""
        try:
            import edge_tts
        except ImportError:
            raise RuntimeError("edge-tts未安装")

        voice = self.voice_presets.get(voice_id, voice_id) or self.default_voice
        
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate,
            volume=volume,
            pitch=pitch
        )

        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]

        duration = len(audio_data) / (24000 * 2)

        return AudioData(
            data=audio_data,
            sample_rate=24000,
            duration=duration
        )

    def synthesize(
        self,
        text: str,
        voice_id: str = None,
        speed: float = 1.0,
        pitch: int = 0,
        emotion: Optional[str] = None
    ) -> AudioData:
        """同步合成语音"""
        rate = f"{int((speed - 1) * 100):+d}%"
        pitch_str = f"{pitch:+d}Hz"
        
        return asyncio.run(self.synthesize_async(
            text=text,
            voice_id=voice_id,
            rate=rate,
            pitch=pitch_str
        ))

    async def synthesize_to_file_async(
        self,
        text: str,
        output_path: Path,
        voice_id: str = None,
        rate: str = "+0%"
    ) -> Path:
        """异步合成并保存到文件"""
        try:
            import edge_tts
        except ImportError:
            raise RuntimeError("edge-tts未安装")

        voice = self.voice_presets.get(voice_id, voice_id) or self.default_voice
        
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate
        )

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        await communicate.save(str(output_path))
        
        return output_path

    def synthesize_to_file(
        self,
        text: str,
        output_path: Path,
        voice_id: str = None,
        speed: float = 1.0
    ) -> Path:
        """同步合成并保存到文件"""
        rate = f"{int((speed - 1) * 100):+d}%"
        return asyncio.run(self.synthesize_to_file_async(
            text=text,
            output_path=output_path,
            voice_id=voice_id,
            rate=rate
        ))

    def generate_scene_audio(
        self,
        audio_config: Dict[str, Any],
        characters: Dict[str, Any]
    ) -> AudioData:
        """为场景生成完整音频 (兼容CosyVoice接口)
        
        使用临时文件和FFmpeg正确合并多段音频，避免直接拼接字节导致的音频损坏
        """
        temp_files = []
        total_duration = 0.0

        try:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp(prefix="edge_tts_")
            
            # 处理旁白
            narration = audio_config.get("narration")
            if narration and narration.get("text"):
                narrator_voice = characters.get("narrator", {}).get("voice", {})
                voice_id = narrator_voice.get("voice_id", "narrator_epic")
                
                temp_path = Path(temp_dir) / f"narration.mp3"
                self.synthesize_to_file(
                    text=narration["text"],
                    output_path=temp_path,
                    voice_id=voice_id,
                    speed=narrator_voice.get("speed", 0.95),
                )
                if temp_path.exists():
                    temp_files.append(temp_path)

            # 处理对话
            dialogues = audio_config.get("dialogues", [])
            char_map = {c["id"]: c for c in characters.get("characters", [])}

            for i, dialogue in enumerate(dialogues):
                char_id = dialogue.get("character_id")
                text = dialogue.get("text", "")

                if not text:
                    continue

                char = char_map.get(char_id, {})
                voice_config = char.get("voice", {})

                temp_path = Path(temp_dir) / f"dialogue_{i:03d}.mp3"
                self.synthesize_to_file(
                    text=text,
                    output_path=temp_path,
                    voice_id=voice_config.get("voice_id", "male_heroic"),
                    speed=voice_config.get("speed", 1.0),
                )
                if temp_path.exists():
                    temp_files.append(temp_path)

            if temp_files:
                # 使用FFmpeg合并音频文件
                output_path = Path(temp_dir) / "combined.mp3"
                combined_data = self._merge_audio_files(temp_files, output_path)
                
                if combined_data:
                    return combined_data
                else:
                    # FFmpeg失败时的回退方案：返回第一个音频
                    logger.warning("FFmpeg合并失败，使用第一个音频片段")
                    return AudioData.from_file(temp_files[0])
            else:
                # 没有音频内容，生成静音
                silence_duration = 3.0
                silence_samples = int(24000 * silence_duration * 2)
                return AudioData(
                    data=b"\x00" * silence_samples,
                    sample_rate=24000,
                    duration=silence_duration
                )
        finally:
            # 清理临时文件
            try:
                import shutil
                if 'temp_dir' in locals():
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")

    def _merge_audio_files(
        self,
        audio_files: List[Path],
        output_path: Path
    ) -> Optional[AudioData]:
        """使用FFmpeg合并多个音频文件"""
        if not audio_files:
            return None
        
        if len(audio_files) == 1:
            # 只有一个文件，直接读取
            return AudioData.from_file(audio_files[0])
        
        try:
            # 创建concat列表文件
            concat_file = output_path.parent / "concat.txt"
            with open(concat_file, "w", encoding="utf-8") as f:
                for audio_file in audio_files:
                    f.write(f"file '{audio_file.as_posix()}'\n")
            
            # 使用FFmpeg concat demuxer合并
            ffmpeg_path = get_ffmpeg_path()
            cmd = [
                ffmpeg_path, "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c:a", "libmp3lame",
                "-q:a", "2",
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and output_path.exists():
                return AudioData.from_file(output_path)
            else:
                logger.error(f"FFmpeg合并音频失败: {result.stderr}")
                return None
                
        except FileNotFoundError:
            logger.warning("FFmpeg未安装，无法合并音频")
            return None
        except Exception as e:
            logger.error(f"合并音频时出错: {e}")
            return None


def create_tts_client(
    provider: str = "edge",
    **kwargs
):
    """
    创建TTS客户端工厂方法
    
    Args:
        provider: 提供商 ("edge" / "cosyvoice")
        **kwargs: 传递给客户端的参数
    """
    if provider == "edge":
        return EdgeTTSClient(**kwargs)
    elif provider == "cosyvoice":
        from .cosyvoice_client import CosyVoiceClient
        return CosyVoiceClient(**kwargs)
    else:
        logger.warning(f"未知TTS提供商: {provider}, 使用Edge TTS")
        return EdgeTTSClient(**kwargs)
