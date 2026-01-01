"""角色设计生成器"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image
from .comfyui_client import ComfyUIClient
from ..utils.logger import get_logger

logger = get_logger(__name__)


class CharacterDesigner:
    """角色设计生成器 - 生成角色立绘和参考图"""

    def __init__(
        self,
        comfyui_client: ComfyUIClient,
        default_checkpoint: str = "animagine-xl-4.0.safetensors"
    ):
        self.client = comfyui_client
        self.default_checkpoint = default_checkpoint

    def generate_character(
        self,
        character: Dict[str, Any],
        output_dir: Path,
        views: List[str] = None
    ) -> Dict[str, Path]:
        """为角色生成多角度参考图"""
        views = views or ["front", "side", "expression_happy", "expression_angry"]
        char_id = character.get("id", "char_unknown")
        char_name = character.get("name", "未知角色")

        logger.info(f"开始生成角色 {char_name} 的参考图...")

        results = {}
        char_dir = output_dir / char_id
        char_dir.mkdir(parents=True, exist_ok=True)

        base_prompt = character.get("sd_prompt", "character portrait")
        negative_prompt = character.get(
            "sd_negative",
            "ugly, deformed, bad anatomy, bad hands, missing fingers"
        )

        for view in views:
            try:
                view_prompt = self._get_view_prompt(base_prompt, view)
                image = self._generate_single(view_prompt, negative_prompt)

                output_path = char_dir / f"{view}.png"
                image.save(output_path)
                results[view] = output_path

                logger.info(f"  生成 {view} 视图完成")
            except Exception as e:
                logger.error(f"  生成 {view} 视图失败: {e}")
                results[view] = None

        return results

    def _get_view_prompt(self, base_prompt: str, view: str) -> str:
        """根据视图类型调整提示词"""
        view_modifiers = {
            "front": "front view, facing viewer, symmetrical",
            "side": "side view, profile, looking to the side",
            "back": "back view, from behind",
            "expression_happy": "happy expression, smiling, joyful",
            "expression_angry": "angry expression, fierce, determined",
            "expression_sad": "sad expression, melancholy, sorrowful",
            "expression_neutral": "neutral expression, calm, composed",
            "full_body": "full body shot, standing pose",
            "upper_body": "upper body, portrait, bust shot"
        }

        modifier = view_modifiers.get(view, "portrait")
        return f"{base_prompt}, {modifier}, masterpiece, best quality"

    def _generate_single(
        self,
        positive_prompt: str,
        negative_prompt: str,
        width: int = 768,
        height: int = 1024
    ) -> Image.Image:
        """生成单张图像"""
        import random

        workflow = {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "cfg": 7,
                    "denoise": 1,
                    "latent_image": ["5", 0],
                    "model": ["4", 0],
                    "negative": ["7", 0],
                    "positive": ["6", 0],
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "seed": random.randint(0, 2**32 - 1),
                    "steps": 30
                }
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": self.default_checkpoint
                }
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "batch_size": 1,
                    "height": height,
                    "width": width
                }
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": positive_prompt
                }
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": negative_prompt
                }
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                }
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "character",
                    "images": ["8", 0]
                }
            }
        }

        images = self.client.execute_workflow(workflow)
        if images:
            return images[0]
        else:
            raise RuntimeError("角色图像生成失败")

    def generate_all_characters(
        self,
        characters: Dict[str, Any],
        output_dir: Path
    ) -> Dict[str, Dict[str, Path]]:
        """批量生成所有角色的参考图"""
        results = {}
        char_list = characters.get("characters", [])

        for char in char_list:
            char_id = char.get("id")
            try:
                char_results = self.generate_character(char, output_dir)
                results[char_id] = char_results
            except Exception as e:
                logger.error(f"角色 {char_id} 生成失败: {e}")
                results[char_id] = {}

        return results
