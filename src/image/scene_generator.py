"""场景图像生成器"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image
from .comfyui_client import ComfyUIClient
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Z-Image-Turbo 工作流模板 (6B参数高效模型，8步生成)
DEFAULT_SCENE_WORKFLOW = {
    "28": {
        "class_type": "UNETLoader",
        "inputs": {
            "unet_name": "z_image_turbo_bf16.safetensors",
            "weight_dtype": "default"
        }
    },
    "29": {
        "class_type": "VAELoader",
        "inputs": {
            "vae_name": "ae.safetensors"
        }
    },
    "30": {
        "class_type": "CLIPLoader",
        "inputs": {
            "clip_name": "qwen_3_4b.safetensors",
            "type": "lumina2",
            "device": "default"
        }
    },
    "11": {
        "class_type": "ModelSamplingAuraFlow",
        "inputs": {
            "model": ["28", 0],
            "shift": 3
        }
    },
    "6": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "clip": ["30", 0],
            "text": "positive prompt"
        }
    },
    "33": {
        "class_type": "ConditioningZeroOut",
        "inputs": {
            "conditioning": ["6", 0]
        }
    },
    "5": {
        "class_type": "EmptySD3LatentImage",
        "inputs": {
            "width": 1280,
            "height": 720,
            "batch_size": 1
        }
    },
    "3": {
        "class_type": "KSampler",
        "inputs": {
            "model": ["11", 0],
            "positive": ["6", 0],
            "negative": ["33", 0],
            "latent_image": ["5", 0],
            "seed": 0,
            "control_after_generate": "randomize",
            "steps": 4,
            "cfg": 1,
            "sampler_name": "res_multistep",
            "scheduler": "simple",
            "denoise": 1
        }
    },
    "8": {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": ["3", 0],
            "vae": ["29", 0]
        }
    },
    "9": {
        "class_type": "SaveImage",
        "inputs": {
            "images": ["8", 0],
            "filename_prefix": "scene"
        }
    }
}


class SceneGenerator:
    """场景图像生成器"""

    def __init__(
        self,
        comfyui_client: ComfyUIClient,
        workflow_path: Optional[Path] = None,
        default_checkpoint: str = "z_image_turbo_bf16.safetensors"
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
        """构建正向提示词
        
        Z-Image-Turbo 使用 Qwen 词法分析器，对中文（尤其是成语和古诗词）
        做了专门优化，直接使用中文自然语言描述即可。
        """
        visual = scene.get("visual", {})
        
        # 直接使用场景的中文描述（Z-Image-Turbo 对中文优化更好）
        description = visual.get("description", "")
        if description:
            return description
        
        # 最后回退
        return "一幅精美的场景画面"

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
        elif style_preset == "realistic_gufeng":
            base_negative.extend([
                "anime", "cartoon", "drawing", "illustration", "comic",
                "3d render", "cgi", "modern clothing", "western style",
                "oversaturated", "neon colors", "chibi", "manga"
            ])
        elif style_preset in ["chinese_fantasy", "xianxia"]:
            base_negative.extend([
                "western fantasy", "medieval armor", "european castle",
                "modern clothing", "realistic photograph", "3d render",
                "chibi", "cute style", "frame", "border", "painting frame",
                "scroll frame", "decorative border", "picture frame",
                "canvas texture", "paper texture", "traditional painting look"
            ])

        return ", ".join(base_negative)

    def _get_style_prefix(self, style_preset: str) -> str:
        """获取风格前缀"""
        presets = {
            "anime": "anime style, illustration, vibrant colors",
            "realistic": "photorealistic, cinematic lighting, detailed",
            "illustration": "digital illustration, concept art, artistic",
            "chinese_fantasy": "chinese xianxia cultivation novel style, wuxia martial arts, immortal cultivator, ancient chinese fantasy world, flowing robes and hanfu, mystical qi energy aura, sword immortal aesthetic, celestial palace background, ink wash painting influence, dramatic lighting, epic scene composition, detailed character design, fantasy landscape with floating mountains, spiritual energy effects, cultivation realm atmosphere",
            "realistic_gufeng": "realistic chinese ancient style, photorealistic, cinematic lighting, traditional chinese aesthetics, hanfu, ancient china, detailed fabric texture, soft natural lighting, elegant composition, oriental beauty, historical accuracy",
            "xianxia": "chinese xianxia style, cultivation immortal world, sword cultivator, flying sword, mystical clouds and mist, ancient chinese architecture, flowing white robes, spiritual qi aura, celestial realm, immortal mountain peaks, dramatic pose, epic fantasy scene, detailed face and clothing, cinematic composition"
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
        """构建完整的工作流 (适配 Z-Image-Turbo)"""
        import copy
        import random

        workflow = copy.deepcopy(self.base_workflow)

        # 设置正向提示词 (Z-Image-Turbo 只需要正向提示词，负向通过 ConditioningZeroOut 处理)
        if "6" in workflow:
            workflow["6"]["inputs"]["text"] = positive_prompt

        # 设置图像尺寸 (使用 EmptySD3LatentImage)
        if "5" in workflow:
            workflow["5"]["inputs"]["width"] = width
            workflow["5"]["inputs"]["height"] = height

        # 设置种子
        if "3" in workflow:
            workflow["3"]["inputs"]["seed"] = seed if seed is not None else random.randint(0, 2**32 - 1)

        # 设置输出文件名
        if "9" in workflow:
            workflow["9"]["inputs"]["filename_prefix"] = scene_id

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
