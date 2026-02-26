"""
角色管理服务 - 封装角色相关业务逻辑
"""
from pathlib import Path
from typing import List, Optional, Dict, Any

from src.utils.config import get_config, Config
from src.utils.file_utils import load_json, save_json, ensure_dir


class CharacterService:
    """角色管理服务"""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.projects_dir = Path(self.config.paths.projects_dir)

    def _get_characters_path(self, project_name: str) -> Path:
        """获取角色文件路径"""
        return self.projects_dir / project_name / "characters.json"

    def _load_characters(self, project_name: str) -> Optional[Dict[str, Any]]:
        """加载角色数据"""
        path = self._get_characters_path(project_name)
        if not path.exists():
            return None
        return load_json(path)

    def _save_characters(self, project_name: str, characters: Dict[str, Any]) -> None:
        """保存角色数据"""
        save_json(self._get_characters_path(project_name), characters)

    def list_characters(self, project_name: str) -> Dict[str, Any]:
        """获取角色列表"""
        data = self._load_characters(project_name)
        if data is None:
            return {"characters": [], "total": 0, "narrator": None}

        chars = data.get("characters", [])
        
        # 添加图像路径
        project_path = self.projects_dir / project_name
        for char in chars:
            char_id = char.get("id", "")
            char_dir = project_path / "characters" / char_id
            if char_dir.exists():
                images = list(char_dir.glob("*.png"))
                char["images"] = [str(img) for img in images]
            else:
                char["images"] = []

        return {
            "characters": chars,
            "total": len(chars),
            "narrator": data.get("narrator"),
        }

    def get_character(self, project_name: str, character_id: str) -> Optional[Dict[str, Any]]:
        """获取角色详情"""
        data = self._load_characters(project_name)
        if data is None:
            return None

        for char in data.get("characters", []):
            if char.get("id") == character_id:
                # 添加图像路径
                project_path = self.projects_dir / project_name
                char_dir = project_path / "characters" / character_id
                if char_dir.exists():
                    char["images"] = [str(img) for img in char_dir.glob("*.png")]
                else:
                    char["images"] = []
                return char

        return None

    def create_character(self, project_name: str, char_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建角色"""
        data = self._load_characters(project_name)
        if data is None:
            data = {"characters": [], "narrator": None}

        chars = data.get("characters", [])
        
        # 生成角色ID
        max_num = 0
        for c in chars:
            cid = c.get("id", "")
            if cid.startswith("char_"):
                try:
                    num = int(cid.split("_")[1])
                    max_num = max(max_num, num)
                except (IndexError, ValueError):
                    pass
        
        new_id = f"char_{max_num + 1:03d}"
        
        character = {
            "id": new_id,
            "name": char_data.get("name", "未命名"),
            "aliases": char_data.get("aliases", []),
            "appearance": char_data.get("appearance", {}),
            "sd_prompt": char_data.get("sd_prompt", ""),
            "sd_negative": char_data.get("sd_negative", ""),
            "voice": char_data.get("voice", {
                "provider": "edge",
                "voice_id": "male_heroic",
                "speed": 1.0,
                "pitch": 0
            }),
            "images": [],
        }

        chars.append(character)
        data["characters"] = chars
        self._save_characters(project_name, data)

        return character

    def update_character(
        self, project_name: str, character_id: str, updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """更新角色"""
        data = self._load_characters(project_name)
        if data is None:
            return None

        chars = data.get("characters", [])
        for i, char in enumerate(chars):
            if char.get("id") == character_id:
                # 更新字段
                for key, value in updates.items():
                    if key != "id":  # 保护ID字段
                        if isinstance(value, dict) and isinstance(char.get(key), dict):
                            char[key].update(value)
                        else:
                            char[key] = value
                chars[i] = char
                data["characters"] = chars
                self._save_characters(project_name, data)
                return char

        return None

    def delete_character(self, project_name: str, character_id: str) -> bool:
        """删除角色"""
        data = self._load_characters(project_name)
        if data is None:
            return False

        chars = data.get("characters", [])
        new_chars = [c for c in chars if c.get("id") != character_id]

        if len(new_chars) == len(chars):
            return False

        data["characters"] = new_chars
        self._save_characters(project_name, data)
        return True

    def get_voice_list(self) -> List[Dict[str, Any]]:
        """获取可用语音列表"""
        # 内置语音预设
        voices = [
            {"id": "male_heroic", "name": "男声-英雄", "gender": "male", "provider": "edge"},
            {"id": "male_gentle", "name": "男声-温柔", "gender": "male", "provider": "edge"},
            {"id": "female_gentle", "name": "女声-温柔", "gender": "female", "provider": "edge"},
            {"id": "female_sweet", "name": "女声-甜美", "gender": "female", "provider": "edge"},
            {"id": "narrator_epic", "name": "旁白-史诗", "gender": "neutral", "provider": "edge"},
            {"id": "narrator_calm", "name": "旁白-平静", "gender": "neutral", "provider": "edge"},
        ]
        return voices

    def preview_voice(self, text: str, voice_id: str) -> Optional[bytes]:
        """预览语音合成"""
        try:
            from src.tts import create_tts_client
            tts = create_tts_client("edge")
            audio = tts.synthesize(text, voice_id=voice_id)
            return audio.data
        except Exception as e:
            return None

    def regenerate_character_image(
        self, project_name: str, character_id: str
    ) -> Optional[Dict[str, Any]]:
        """重新生成角色立绘"""
        char = self.get_character(project_name, character_id)
        if char is None:
            return None

        try:
            from src.image import ComfyUIClient, CharacterDesigner
            comfyui = ComfyUIClient(base_url=self.config.local.comfyui_url)
            designer = CharacterDesigner(comfyui)

            output_dir = self.projects_dir / project_name / "characters"
            results = designer.generate_character(char, output_dir)

            return {
                "character_id": character_id,
                "images": {view: str(path) for view, path in results.items() if path},
            }
        except Exception as e:
            raise RuntimeError(f"生成角色立绘失败: {e}")


# 单例模式
_character_service: Optional[CharacterService] = None


def get_character_service() -> CharacterService:
    """获取角色服务实例"""
    global _character_service
    if _character_service is None:
        _character_service = CharacterService()
    return _character_service

