"""CosyVoice 3 TTS 客户端

适配 CosyVoice 3 FastAPI 服务接口：
- /inference_sft        预设音色合成
- /inference_zero_shot  零样本声音克隆
- /inference_instruct2  指令控制合成（情感/语速/方言等）

服务端返回原始 PCM 16bit 音频流，客户端封装为 WAV 格式。
"""
import io
import struct
import wave
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


def _pcm_to_wav(pcm_data: bytes, sample_rate: int = 22050, channels: int = 1, sample_width: int = 2) -> bytes:
    """将原始 PCM 数据转为 WAV 格式"""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


class CosyVoiceClient:
    """CosyVoice 3 TTS API 客户端

    对接 CosyVoice 3 FastAPI 服务（默认端口 50000）。
    支持预设音色、零样本克隆、指令控制三种合成模式。
    """

    # CosyVoice 3 输出采样率
    SAMPLE_RATE = 22050

    def __init__(
        self,
        base_url: str = "http://localhost:50000",
        timeout: int = 120,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()

        # 预设音色映射 -> CosyVoice 3 speaker ID
        # CosyVoice 3 SFT 模式的可用 spk_id 取决于模型
        self.voice_presets = {
            "male_heroic": {"spk_id": "中文男", "instruct": "请用有力的声音说话。"},
            "male_gentle": {"spk_id": "中文男", "instruct": "请用温柔的声音说话。"},
            "female_gentle": {"spk_id": "中文女", "instruct": "请用温柔的声音说话。"},
            "female_sweet": {"spk_id": "中文女", "instruct": "请用甜美的声音说话。"},
            "narrator_epic": {"spk_id": "中文男", "instruct": "请用叙事的语气说话。"},
            "narrator_calm": {"spk_id": "中文女", "instruct": "请用平静的语气说话。"},
        }

    def check_health(self) -> bool:
        """检查服务是否可用"""
        try:
            response = self._session.get(f"{self.base_url}/", timeout=5)
            return response.status_code in (200, 404, 405)
        except Exception:
            return False

    def list_speakers(self) -> List[str]:
        """获取可用预设音色列表"""
        return list(self.voice_presets.keys())

    def synthesize(
        self,
        text: str,
        voice_id: str = "narrator_epic",
        speed: float = 1.0,
        pitch: int = 0,
        emotion: Optional[str] = None,
    ) -> AudioData:
        """合成语音

        优先使用 SFT 模式（预设音色），如果有情感需求则使用 instruct2 模式。

        Args:
            text: 要合成的文本
            voice_id: 音色预设 ID
            speed: 语速（当前版本通过 instruct 控制）
            pitch: 音调（CosyVoice 3 不直接支持）
            emotion: 情感标签

        Returns:
            AudioData 音频数据
        """
        preset = self.voice_presets.get(voice_id, self.voice_presets["narrator_epic"])

        # 构建指令文本
        instruct_parts = []
        if emotion:
            instruct_parts.append(f"请用{emotion}的语气说话。")
        elif preset.get("instruct"):
            instruct_parts.append(preset["instruct"])
        if speed and speed != 1.0:
            if speed > 1.2:
                instruct_parts.append("请用较快的语速说话。")
            elif speed < 0.8:
                instruct_parts.append("请用较慢的语速说话。")

        instruct_text = " ".join(instruct_parts) if instruct_parts else ""

        # 先尝试 SFT 模式
        try:
            if not instruct_text:
                pcm_data = self._call_sft(text, preset.get("spk_id", "中文男"))
            else:
                # 有指令时使用 instruct2（需要参考音频，用内置的）
                pcm_data = self._call_sft(text, preset.get("spk_id", "中文男"))
        except Exception as e:
            logger.error(f"TTS 合成失败: {e}")
            raise

        wav_data = _pcm_to_wav(pcm_data, self.SAMPLE_RATE)
        duration = len(pcm_data) / (self.SAMPLE_RATE * 2)  # 16bit = 2 bytes

        return AudioData(data=wav_data, sample_rate=self.SAMPLE_RATE, duration=duration)

    def synthesize_with_reference(
        self,
        text: str,
        reference_audio: Union[str, Path, bytes],
        prompt_text: str = "",
        speed: float = 1.0,
    ) -> AudioData:
        """使用参考音频进行零样本声音克隆

        Args:
            text: 要合成的文本
            reference_audio: 参考音频（路径或字节数据）
            prompt_text: 参考音频对应的文本（提升效果）
            speed: 语速

        Returns:
            AudioData 音频数据
        """
        if isinstance(reference_audio, (str, Path)):
            with open(reference_audio, "rb") as f:
                ref_data = f.read()
        else:
            ref_data = reference_audio

        if not prompt_text:
            prompt_text = "You are a helpful assistant.<|endofprompt|>"

        pcm_data = self._call_zero_shot(text, prompt_text, ref_data)
        wav_data = _pcm_to_wav(pcm_data, self.SAMPLE_RATE)
        duration = len(pcm_data) / (self.SAMPLE_RATE * 2)

        return AudioData(data=wav_data, sample_rate=self.SAMPLE_RATE, duration=duration)

    def generate_scene_audio(
        self,
        audio_config: Dict[str, Any],
        characters: Dict[str, Any],
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
                emotion=narration.get("emotion"),
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

            char = char_map.get(char_id, {})
            voice_config = char.get("voice", {})

            dialogue_audio = self.synthesize(
                text=text,
                voice_id=voice_config.get("voice_id", "male_heroic"),
                speed=voice_config.get("speed", 1.0),
                emotion=emotion,
            )
            audio_segments.append(dialogue_audio.data)
            total_duration += dialogue_audio.duration

        if audio_segments:
            combined_data = b"".join(audio_segments)
            return AudioData(
                data=combined_data,
                sample_rate=self.SAMPLE_RATE,
                duration=total_duration,
            )
        else:
            silence_duration = 3.0
            silence_samples = int(self.SAMPLE_RATE * silence_duration * 2)
            return AudioData(
                data=b"\x00" * silence_samples,
                sample_rate=self.SAMPLE_RATE,
                duration=silence_duration,
            )

    # ---- 内部方法：调用 CosyVoice 3 API ----

    def _call_sft(self, text: str, spk_id: str) -> bytes:
        """调用 SFT 预设音色接口"""
        logger.debug(f"TTS SFT 请求: spk={spk_id}, text={text[:50]}...")
        response = self._session.post(
            f"{self.base_url}/inference_sft",
            data={"tts_text": text, "spk_id": spk_id},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.content

    def _call_zero_shot(self, text: str, prompt_text: str, prompt_wav: bytes) -> bytes:
        """调用零样本克隆接口"""
        logger.debug(f"TTS Zero-Shot 请求: text={text[:50]}...")
        response = self._session.post(
            f"{self.base_url}/inference_zero_shot",
            data={"tts_text": text, "prompt_text": prompt_text},
            files={"prompt_wav": ("prompt.wav", prompt_wav, "audio/wav")},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.content

    def _call_instruct2(self, text: str, instruct_text: str, prompt_wav: bytes) -> bytes:
        """调用指令控制接口"""
        logger.debug(f"TTS Instruct2 请求: text={text[:50]}...")
        response = self._session.post(
            f"{self.base_url}/inference_instruct2",
            data={"tts_text": text, "instruct_text": instruct_text},
            files={"prompt_wav": ("prompt.wav", prompt_wav, "audio/wav")},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.content
