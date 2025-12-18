"""音色管理器"""
from pathlib import Path
from typing import Dict, Any, List, Optional
from .cosyvoice_client import CosyVoiceClient
from ..utils.logger import get_logger

logger = get_logger(__name__)


class VoiceManager:
    """音色管理器 - 管理角色音色映射"""

    def __init__(self, tts_client: CosyVoiceClient):
        self.tts = tts_client
        self.character_voices: Dict[str, Dict[str, Any]] = {}
        self.reference_audios: Dict[str, Path] = {}

    def assign_voice(
        self,
        character_id: str,
        voice_id: str,
        speed: float = 1.0,
        pitch: int = 0
    ) -> None:
        """为角色分配音色"""
        self.character_voices[character_id] = {
            "voice_id": voice_id,
            "speed": speed,
            "pitch": pitch
        }
        logger.info(f"角色 {character_id} 分配音色: {voice_id}")

    def set_reference_audio(
        self,
        character_id: str,
        audio_path: Path
    ) -> None:
        """设置角色的参考音频（用于音色克隆）"""
        if audio_path.exists():
            self.reference_audios[character_id] = audio_path
            logger.info(f"角色 {character_id} 设置参考音频: {audio_path}")
        else:
            logger.warning(f"参考音频不存在: {audio_path}")

    def get_voice_config(self, character_id: str) -> Dict[str, Any]:
        """获取角色音色配置"""
        return self.character_voices.get(character_id, {
            "voice_id": "male_heroic",
            "speed": 1.0,
            "pitch": 0
        })

    def auto_assign_voices(self, characters: Dict[str, Any]) -> None:
        """根据角色特征自动分配音色"""
        char_list = characters.get("characters", [])

        for char in char_list:
            char_id = char.get("id")
            if char_id in self.character_voices:
                continue

            # 根据性别分配
            gender = char.get("appearance", {}).get("gender", "").lower()
            personality = char.get("personality", "").lower()

            if gender == "female":
                if "温柔" in personality or "gentle" in personality:
                    voice_id = "female_gentle"
                else:
                    voice_id = "female_sweet"
            else:
                if "英勇" in personality or "hero" in personality:
                    voice_id = "male_heroic"
                else:
                    voice_id = "male_gentle"

            self.assign_voice(char_id, voice_id)

    def preview_voice(self, character_id: str, text: str = "你好，这是一段测试语音。") -> bytes:
        """预览角色音色"""
        voice_config = self.get_voice_config(character_id)
        audio = self.tts.synthesize(
            text=text,
            voice_id=voice_config.get("voice_id", "male_heroic"),
            speed=voice_config.get("speed", 1.0)
        )
        return audio.data
