"""角色提取器"""
import json
import re
from typing import List, Dict, Any
from .client import OllamaClient
from ..utils.logger import get_logger

logger = get_logger(__name__)

# 角色提取提示词
CHARACTER_EXTRACTION_PROMPT = """你是一个专业的小说分析师。请分析以下小说片段，提取所有主要角色信息。

小说内容:
{novel_text}

请以JSON数组格式输出，每个角色包含:
- id: 唯一标识 (格式: char_001, char_002, ...)
- name: 角色姓名
- aliases: 别名/称呼列表 (如 "他", "主角", "少年" 等)
- appearance: 外貌描述对象
  - gender: 性别 (male/female)
  - age: 大致年龄
  - hair: 发型发色描述
  - eyes: 眼睛特征
  - clothing: 典型服装描述
  - features: 其他显著特征
- personality: 性格特点描述
- sd_prompt: 用于Stable Diffusion的英文外貌提示词
- sd_negative: Stable Diffusion负面提示词

注意:
1. 只提取有明确描述的主要角色
2. 如果某些信息不明确，可以根据上下文合理推断
3. sd_prompt应该是高质量的英文提示词，包含外貌、服装等细节
4. 确保JSON格式正确，可以被解析

输出格式:
```json
[
  {{
    "id": "char_001",
    "name": "角色名",
    "aliases": ["别名1", "别名2"],
    "appearance": {{
      "gender": "male",
      "age": "25",
      "hair": "黑色短发",
      "eyes": "剑眉星目",
      "clothing": "白色长袍",
      "features": "身材修长"
    }},
    "personality": "正直勇敢",
    "sd_prompt": "1boy, black short hair, sharp eyebrows, wearing white hanfu robe, handsome",
    "sd_negative": "ugly, deformed, bad anatomy, bad hands"
  }}
]
```"""


class CharacterExtractor:
    """角色信息提取器"""

    def __init__(self, llm_client: OllamaClient):
        self.llm = llm_client

    def extract(self, novel_text: str, max_chars: int = 15000) -> Dict[str, Any]:
        """从小说文本中提取角色信息"""
        # 截取合适长度的文本
        text_to_analyze = novel_text[:max_chars] if len(novel_text) > max_chars else novel_text

        prompt = CHARACTER_EXTRACTION_PROMPT.format(novel_text=text_to_analyze)

        logger.info("开始提取角色信息...")
        response = self.llm.chat(
            prompt=prompt,
            temperature=0.3,  # 降低温度以获得更稳定的输出
            max_tokens=4096
        )

        # 解析响应
        characters = self._parse_response(response)
        logger.info(f"成功提取 {len(characters)} 个角色")

        # 为每个角色添加默认语音配置
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
        """解析LLM响应中的JSON"""
        # 尝试找到JSON代码块
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接找到数组
            start = response.find('[')
            end = response.rfind(']') + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
            else:
                logger.error(f"无法从响应中提取JSON: {response[:500]}")
                return []

        try:
            characters = json.loads(json_str)
            return self._validate_characters(characters)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return []

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
