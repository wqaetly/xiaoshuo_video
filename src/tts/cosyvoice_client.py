"""CosyVoice TTS客户端"""
import io
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import requests
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AudioData:
    """音频数据封装"""

    def __init__(self, data: bytes, sample_rate: int = 22050, duration: float = 0.0):
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


class CosyVoiceClient:
    """CosyVoice TTS API客户端"""

    def __init__(
        self,
        base_url: str = "http://localhost:9880",
        timeout: int = 120
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()

        # 预设音色映射
        self.voice_presets = {
            "male_heroic": {"speaker": "中文男", "emotion": "hero"},
            "male_gentle": {"speaker": "中文男", "emotion": "gentle"},
            "female_gentle": {"speaker": "中文女", "emotion": "gentle"},
            "female_sweet": {"speaker": "中文女", "emotion": "sweet"},
            "narrator_epic": {"speaker": "中文男", "emotion": "narrative"},
            "narrator_calm": {"speaker": "中文女", "emotion": "calm"},
        }

    def check_health(self) -> bool:
        """检查服务是否可用"""
        try:
            response = self._session.get(f"{self.base_url}/", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"CosyVoice服务检查失败: {e}")
            return False

    def list_speakers(self) -> List[str]:
        """获取可用音色列表"""
        try:
            response = self._session.get(
                f"{self.base_url}/speakers",
                timeout=10
            )
            response.raise_for_status()
            return response.json().get("speakers", [])
        except Exception as e:
            logger.error(f"获取音色列表失败: {e}")
            return []

    def synthesize(
        self,
        text: str,
        voice_id: str = "narrator_epic",
        speed: float = 1.0,
        pitch: int = 0,
        emotion: Optional[str] = None
    ) -> AudioData:
        """合成语音"""
        # 获取音色配置
        voice_config = self.voice_presets.get(voice_id, {})
        speaker = voice_config.get("speaker", "中文男")

        payload = {
            "text": text,
            "speaker": speaker,
            "speed": speed,
        }

        # 添加可选参数
        if emotion:
            payload["emotion"] = emotion
        elif voice_config.get("emotion"):
            payload["emotion"] = voice_config["emotion"]

        try:
            logger.debug(f"TTS请求: {text[:50]}...")

            response = self._session.post(
                f"{self.base_url}/tts",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            # 计算时长 (假设22050采样率)
            audio_data = response.content
            duration = len(audio_data) / (22050 * 2)  # 16bit = 2 bytes per sample

            return AudioData(
                data=audio_data,
                sample_rate=22050,
                duration=duration
            )
        except Exception as e:
            logger.error(f"TTS合成失败: {e}")
            raise

    def synthesize_with_reference(
        self,
        text: str,
        reference_audio: Union[str, Path, bytes],
        speed: float = 1.0
    ) -> AudioData:
        """使用参考音频进行音色克隆合成"""
        # 准备参考音频
        if isinstance(reference_audio, (str, Path)):
            with open(reference_audio, "rb") as f:
                ref_data = f.read()
        else:
            ref_data = reference_audio

        files = {
            "reference_audio": ("reference.wav", ref_data, "audio/wav")
        }
        data = {
            "text": text,
            "speed": speed
        }

        try:
            response = self._session.post(
                f"{self.base_url}/tts_clone",
                files=files,
                data=data,
                timeout=self.timeout
            )
            response.raise_for_status()

            audio_data = response.content
            duration = len(audio_data) / (22050 * 2)

            return AudioData(
                data=audio_data,
                sample_rate=22050,
                duration=duration
            )
        except Exception as e:
            logger.error(f"音色克隆TTS失败: {e}")
            raise

    def generate_scene_audio(
        self,
        audio_config: Dict[str, Any],
        characters: Dict[str, Any]
    ) -> AudioData:
        """为场景生成完整音频"""
        audio_segments = []
        total_duration = 0.0

        # 处理旁白
        narration = audio_config.get("narration")
        if narration and narration.get("text"):
            narrator_voice = characters.get("narrator", {}).get("voice", {})
            narration_audio = self.synthesize(
                text=narration["text"],
                voice_id=narrator_voice.get("voice_id", "narrator_epic"),
                speed=narrator_voice.get("speed", 0.95),
                emotion=narration.get("emotion")
            )
            audio_segments.append(narration_audio.data)
            total_duration += narration_audio.duration

        # 处理对话
        dialogues = audio_config.get("dialogues", [])
        char_map = {c["id"]: c for c in characters.get("characters", [])}

        for dialogue in dialogues:
            char_id = dialogue.get("character_id")
            text = dialogue.get("text", "")
            emotion = dialogue.get("emotion")

            if not text:
                continue

            # 获取角色音色配置
            char = char_map.get(char_id, {})
            voice_config = char.get("voice", {})

            dialogue_audio = self.synthesize(
                text=text,
                voice_id=voice_config.get("voice_id", "male_heroic"),
                speed=voice_config.get("speed", 1.0),
                emotion=emotion
            )
            audio_segments.append(dialogue_audio.data)
            total_duration += dialogue_audio.duration

        # 合并音频段
        if audio_segments:
            combined_data = b"".join(audio_segments)
            return AudioData(
                data=combined_data,
                sample_rate=22050,
                duration=total_duration
            )
        else:
            # 返回静音
            silence_duration = 3.0
            silence_samples = int(22050 * silence_duration * 2)
            return AudioData(
                data=b"\x00" * silence_samples,
                sample_rate=22050,
                duration=silence_duration
            )
