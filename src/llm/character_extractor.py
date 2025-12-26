"""角色提取器"""
import json
import re
from typing import List, Dict, Any
from .client import OllamaClient
from .json_parser import parse_json_safe, parse_json_array
from .prompt_manager import get_prompt_with_fallback
from ..utils.logger import get_logger

logger = get_logger(__name__)


class CharacterExtractor:
    """角色信息提取器"""

    def __init__(self, llm_client: OllamaClient):
        self.llm = llm_client

    def extract(self, novel_text: str, max_chars: int = 15000) -> Dict[str, Any]:
        """从小说文本中提取角色信息"""
        text_to_analyze = novel_text[:max_chars] if len(novel_text) > max_chars else novel_text

        prompt = get_prompt_with_fallback("extract_characters", novel_text=text_to_analyze)

        logger.info("开始提取角色信息...")
        response = self.llm.chat(
            prompt=prompt,
            temperature=0.3,
            max_tokens=4096
        )

        characters = self._parse_response(response)
        logger.info(f"成功提取 {len(characters)} 个角色")

        for char in characters:
            char["voice"] = self._get_default_voice(char)

        return {
            "characters": characters,
            "narrator": {
                "voice": {
                    "provider": "cosyvoice",
                    "voice_id": "narrator_epic",
                    "speed": 0.95,
                    "pitch": -2
                }
            }
        }

    def _parse_response(self, response: str) -> List[Dict[str, Any]]:
        """解析LLM响应中的JSON (使用增强的JSON解析器)"""
        characters = parse_json_safe(response, default=[])
        
        if not characters:
            logger.warning("角色JSON解析返回空列表")
            return []
        
        if not isinstance(characters, list):
            logger.error(f"角色解析结果不是列表: {type(characters)}")
            return []
        
        return self._validate_characters(characters)

    def _validate_characters(self, characters: List[Dict]) -> List[Dict]:
        """验证并修复角色数据"""
        validated = []
        for i, char in enumerate(characters):
            # 确保必要字段存在
            if "id" not in char:
                char["id"] = f"char_{i+1:03d}"
            if "name" not in char:
                continue  # 没有名字的角色跳过
            if "aliases" not in char:
                char["aliases"] = []
            if "appearance" not in char:
                char["appearance"] = {}
            if "sd_prompt" not in char:
                char["sd_prompt"] = self._generate_sd_prompt(char)
            if "sd_negative" not in char:
                char["sd_negative"] = "ugly, deformed, bad anatomy, bad hands, missing fingers"

            validated.append(char)

        return validated

    def _generate_sd_prompt(self, char: Dict) -> str:
        """根据角色信息生成SD提示词"""
        appearance = char.get("appearance", {})
        parts = []

        # 性别
        gender = appearance.get("gender", "").lower()
        if gender == "male":
            parts.append("1boy")
        elif gender == "female":
            parts.append("1girl")

        # 头发
        if hair := appearance.get("hair"):
            parts.append(hair)

        # 眼睛
        if eyes := appearance.get("eyes"):
            parts.append(eyes)

        # 服装
        if clothing := appearance.get("clothing"):
            parts.append(f"wearing {clothing}")

        # 特征
        if features := appearance.get("features"):
            parts.append(features)

        return ", ".join(parts) if parts else "character portrait"

    def _get_default_voice(self, char: Dict) -> Dict:
        """根据角色特征分配默认语音"""
        gender = char.get("appearance", {}).get("gender", "").lower()

        if gender == "female":
            voice_id = "female_gentle"
        else:
            voice_id = "male_heroic"

        return {
            "provider": "cosyvoice",
            "voice_id": voice_id,
            "speed": 1.0,
            "pitch": 0
        }
