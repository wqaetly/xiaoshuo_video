"""场景图像生成器"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image
from .comfyui_client import ComfyUIClient
from ..utils.logger import get_logger

logger = get_logger(__name__)

# 默认SDXL工作流模板
DEFAULT_SCENE_WORKFLOW = {
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
            "seed": 0,
            "steps": 25
        }
    },
    "4": {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {
            "ckpt_name": "sd_xl_base_1.0.safetensors"
        }
    },
    "5": {
        "class_type": "EmptyLatentImage",
        "inputs": {
            "batch_size": 1,
            "height": 720,
            "width": 1280
        }
    },
    "6": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "clip": ["4", 1],
            "text": "positive prompt"
        }
    },
    "7": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "clip": ["4", 1],
            "text": "negative prompt"
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
            "filename_prefix": "scene",
            "images": ["8", 0]
        }
    }
}


class SceneGenerator:
    """场景图像生成器"""

    def __init__(
        self,
        comfyui_client: ComfyUIClient,
        workflow_path: Optional[Path] = None,
        default_checkpoint: str = "sd_xl_base_1.0.safetensors"
    ):
        self.client = comfyui_client
        self.default_checkpoint = default_checkpoint

        # 加载自定义工作流或使用默认
        if workflow_path and workflow_path.exists():
            self.base_workflow = self.client.load_workflow(workflow_path)
        else:
            self.base_workflow = DEFAULT_SCENE_WORKFLOW.copy()

    def generate_scene(
        self,
        scene: Dict[str, Any],
        characters: Dict[str, Any],
        style_preset: str = "anime",
        width: int = 1280,
        height: int = 720,
        seed: Optional[int] = None
    ) -> Image.Image:
        """根据场景信息生成图像"""
        # 构建提示词
        positive_prompt = self._build_positive_prompt(scene, characters, style_preset)
        negative_prompt = self._build_negative_prompt(style_preset)

        logger.info(f"生成场景图像: {scene.get('id', 'unknown')}")
        logger.debug(f"正向提示词: {positive_prompt}")

        # 构建工作流
        workflow = self._build_workflow(
            positive_prompt=positive_prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            seed=seed,
            scene_id=scene.get("id", "scene")
        )

        # 执行生成
        images = self.client.execute_workflow(workflow)

        if images:
            return images[0]
        else:
            raise RuntimeError("图像生成失败，未返回图像")

    def _build_positive_prompt(
        self,
        scene: Dict[str, Any],
        characters: Dict[str, Any],
        style_preset: str
    ) -> str:
        """构建正向提示词"""
        parts = []

        # 风格前缀
        style_prefix = self._get_style_prefix(style_preset)
        parts.append(style_prefix)

        # 场景描述
        visual = scene.get("visual", {})
        description = visual.get("description", "")
        if description:
            parts.append(description)

        # 风格标签
        style_tags = visual.get("style_tags", [])
        if style_tags:
            parts.extend(style_tags)

        # 角色提示词
        char_prompts = self._get_character_prompts(
            visual.get("characters_in_scene", []),
            characters
        )
        if char_prompts:
            parts.append(char_prompts)

        # 镜头信息
        camera = visual.get("camera", {})
        camera_prompt = self._get_camera_prompt(camera)
        if camera_prompt:
            parts.append(camera_prompt)

        # 质量标签
        quality_tags = "masterpiece, best quality, highly detailed, 8k"
        parts.append(quality_tags)

        return ", ".join(parts)

    def _build_negative_prompt(self, style_preset: str) -> str:
        """构建负向提示词"""
        base_negative = [
            "ugly", "deformed", "noisy", "blurry", "distorted",
            "low quality", "bad anatomy", "bad proportions",
            "extra limbs", "clone face", "disfigured",
            "gross proportions", "malformed limbs", "missing arms",
            "missing legs", "extra arms", "extra legs", "fused fingers",
            "too many fingers", "long neck", "watermark", "signature"
        ]

        if style_preset == "anime":
            base_negative.extend(["realistic", "3d render", "photograph"])
        elif style_preset == "realistic":
            base_negative.extend(["anime", "cartoon", "drawing", "illustration"])

        return ", ".join(base_negative)

    def _get_style_prefix(self, style_preset: str) -> str:
        """获取风格前缀"""
        presets = {
            "anime": "anime style, illustration, vibrant colors",
            "realistic": "photorealistic, cinematic lighting, detailed",
            "illustration": "digital illustration, concept art, artistic",
            "chinese_fantasy": "chinese fantasy, xianxia, oriental style, ethereal"
        }
        return presets.get(style_preset, presets["anime"])

    def _get_character_prompts(
        self,
        character_ids: List[str],
        characters: Dict[str, Any]
    ) -> str:
        """获取场景中角色的提示词"""
        char_list = characters.get("characters", [])
        char_map = {c["id"]: c for c in char_list}

        prompts = []
        for char_id in character_ids:
            if char_id in char_map:
                char = char_map[char_id]
                sd_prompt = char.get("sd_prompt", "")
                if sd_prompt:
                    prompts.append(sd_prompt)

        return ", ".join(prompts)

    def _get_camera_prompt(self, camera: Dict[str, Any]) -> str:
        """获取镜头相关提示词"""
        frame_map = {
            "wide_shot": "wide shot, establishing shot",
            "medium_shot": "medium shot",
            "close_up": "close up shot, portrait",
            "extreme_close_up": "extreme close up, detailed"
        }

        start_frame = camera.get("start_frame", "medium_shot")
        return frame_map.get(start_frame, "")

    def _build_workflow(
        self,
        positive_prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        seed: Optional[int],
        scene_id: str
    ) -> Dict[str, Any]:
        """构建完整的工作流"""
        import copy
        import random

        workflow = copy.deepcopy(self.base_workflow)

        # 设置提示词
        if "6" in workflow:
            workflow["6"]["inputs"]["text"] = positive_prompt
        if "7" in workflow:
            workflow["7"]["inputs"]["text"] = negative_prompt

        # 设置图像尺寸
        if "5" in workflow:
            workflow["5"]["inputs"]["width"] = width
            workflow["5"]["inputs"]["height"] = height

        # 设置种子
        if "3" in workflow:
            workflow["3"]["inputs"]["seed"] = seed if seed is not None else random.randint(0, 2**32 - 1)

        # 设置输出文件名
        if "9" in workflow:
            workflow["9"]["inputs"]["filename_prefix"] = scene_id

        # 设置检查点
        if "4" in workflow:
            workflow["4"]["inputs"]["ckpt_name"] = self.default_checkpoint

        return workflow

    def generate_batch(
        self,
        scenes: List[Dict[str, Any]],
        characters: Dict[str, Any],
        output_dir: Path,
        **kwargs
    ) -> Dict[str, Path]:
        """批量生成场景图像"""
        results = {}

        for scene in scenes:
            scene_id = scene.get("id", f"scene_{len(results)}")

            try:
                image = self.generate_scene(scene, characters, **kwargs)
                output_path = output_dir / f"{scene_id}.png"
                image.save(output_path)
                results[scene_id] = output_path
                logger.info(f"场景 {scene_id} 图像已保存: {output_path}")
            except Exception as e:
                logger.error(f"场景 {scene_id} 生成失败: {e}")
                results[scene_id] = None

        return results
