"""场景图像生成器"""
import json
import copy
import random
from pathlib import Path
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from PIL import Image
from .comfyui_client import ComfyUIClient
from ..utils.logger import get_logger

if TYPE_CHECKING:
    from .character_designer import CharacterReferenceManager

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
    """场景图像生成器

    支持两种模式:
    1. 基础模式: 仅使用文本提示词生成场景图像
    2. IP-Adapter 模式: 结合角色参考图实现角色一致性
    """

    def __init__(
        self,
        comfyui_client: ComfyUIClient,
        workflow_path: Optional[Path] = None,
        ipadapter_workflow_path: Optional[Path] = None,
        default_checkpoint: str = "z_image_turbo_bf16.safetensors",
        reference_manager: Optional["CharacterReferenceManager"] = None
    ):
        """初始化场景生成器

        Args:
            comfyui_client: ComfyUI 客户端
            workflow_path: 基础工作流路径
            ipadapter_workflow_path: IP-Adapter 工作流路径
            default_checkpoint: 默认模型检查点
            reference_manager: 角色参考图管理器 (启用角色一致性功能)
        """
        self.client = comfyui_client
        self.default_checkpoint = default_checkpoint
        self.reference_manager = reference_manager

        # IP-Adapter 配置
        self.ipadapter_config = {
            "enabled": reference_manager is not None,
            "weight": 0.8,           # IP-Adapter 权重 (0.0-1.0)
            "noise": 0.0,            # 噪声级别
            "weight_type": "standard",
            "start_at": 0.0,
            "end_at": 1.0
        }

        # 加载基础工作流
        if workflow_path and workflow_path.exists():
            self.base_workflow = self.client.load_workflow(workflow_path)
        else:
            self.base_workflow = copy.deepcopy(DEFAULT_SCENE_WORKFLOW)

        # 加载 IP-Adapter 工作流 (如果存在)
        self.ipadapter_workflow = None
        if ipadapter_workflow_path and ipadapter_workflow_path.exists():
            self.ipadapter_workflow = self.client.load_workflow(ipadapter_workflow_path)

    def set_reference_manager(self, manager: "CharacterReferenceManager") -> None:
        """设置角色参考图管理器"""
        self.reference_manager = manager
        self.ipadapter_config["enabled"] = True

    def configure_ipadapter(
        self,
        weight: float = 0.8,
        noise: float = 0.0,
        weight_type: str = "standard",
        start_at: float = 0.0,
        end_at: float = 1.0
    ) -> None:
        """配置 IP-Adapter 参数

        Args:
            weight: IP-Adapter 权重，控制参考图对结果的影响程度 (0.0-1.0)
            noise: 添加到参考图的噪声级别
            weight_type: 权重类型 (standard/linear/ease in/ease out)
            start_at: 开始应用 IP-Adapter 的采样步骤比例
            end_at: 停止应用 IP-Adapter 的采样步骤比例
        """
        self.ipadapter_config.update({
            "weight": weight,
            "noise": noise,
            "weight_type": weight_type,
            "start_at": start_at,
            "end_at": end_at
        })

    def generate_scene(
        self,
        scene: Dict[str, Any],
        characters: Dict[str, Any],
        style_preset: str = "anime",
        width: int = 1280,
        height: int = 720,
        seed: Optional[int] = None,
        use_ipadapter: Optional[bool] = None
    ) -> Image.Image:
        """根据场景信息生成图像

        Args:
            scene: 场景配置
            characters: 角色配置
            style_preset: 风格预设
            width: 图像宽度
            height: 图像高度
            seed: 随机种子
            use_ipadapter: 是否使用 IP-Adapter (None=自动判断)

        Returns:
            生成的 PIL 图像
        """
        scene_id = scene.get("id", "unknown")

        # 构建提示词
        positive_prompt = self._build_positive_prompt(scene, characters, style_preset)
        negative_prompt = self._build_negative_prompt(style_preset)

        logger.info(f"生成场景图像: {scene_id}")
        logger.debug(f"正向提示词: {positive_prompt}")

        # 获取场景中的角色
        visual = scene.get("visual", {})
        character_ids = visual.get("characters_in_scene", [])

        # 决定是否使用 IP-Adapter
        should_use_ipadapter = self._should_use_ipadapter(character_ids, use_ipadapter)

        if should_use_ipadapter:
            logger.info(f"场景 {scene_id} 启用 IP-Adapter 角色一致性")
            workflow = self._build_ipadapter_workflow(
                positive_prompt=positive_prompt,
                width=width,
                height=height,
                seed=seed,
                scene_id=scene_id,
                character_ids=character_ids
            )
        else:
            # 使用基础工作流
            workflow = self._build_workflow(
                positive_prompt=positive_prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                seed=seed,
                scene_id=scene_id
            )

        # 执行生成
        images = self.client.execute_workflow(workflow)

        if images:
            return images[0]
        else:
            raise RuntimeError("图像生成失败，未返回图像")

    def _should_use_ipadapter(
        self,
        character_ids: List[str],
        use_ipadapter: Optional[bool]
    ) -> bool:
        """判断是否应该使用 IP-Adapter

        Args:
            character_ids: 场景中的角色 ID 列表
            use_ipadapter: 用户指定的选项 (None=自动)

        Returns:
            是否使用 IP-Adapter
        """
        # 如果明确指定，直接返回
        if use_ipadapter is not None:
            return use_ipadapter

        # 自动判断条件:
        # 1. IP-Adapter 功能已启用
        # 2. 有 IP-Adapter 工作流
        # 3. 场景中有角色
        # 4. 至少有一个角色有参考图
        if not self.ipadapter_config.get("enabled", False):
            return False

        if not self.ipadapter_workflow:
            return False

        if not character_ids:
            return False

        if not self.reference_manager:
            return False

        # 检查是否有任何角色有参考图
        for char_id in character_ids:
            if self.reference_manager.has_reference(char_id):
                return True

        return False

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

    def _build_ipadapter_workflow(
        self,
        positive_prompt: str,
        width: int,
        height: int,
        seed: Optional[int],
        scene_id: str,
        character_ids: List[str]
    ) -> Dict[str, Any]:
        """构建带 IP-Adapter 的工作流

        Args:
            positive_prompt: 正向提示词
            width: 图像宽度
            height: 图像高度
            seed: 随机种子
            scene_id: 场景 ID
            character_ids: 场景中的角色 ID 列表

        Returns:
            配置好的工作流字典
        """
        if not self.ipadapter_workflow:
            raise RuntimeError("IP-Adapter 工作流未加载")

        workflow = copy.deepcopy(self.ipadapter_workflow)

        # 设置正向提示词
        if "6" in workflow:
            workflow["6"]["inputs"]["text"] = positive_prompt

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

        # 配置 IP-Adapter 参数
        if "103" in workflow:
            workflow["103"]["inputs"]["weight"] = self.ipadapter_config["weight"]
            workflow["103"]["inputs"]["noise"] = self.ipadapter_config["noise"]
            workflow["103"]["inputs"]["weight_type"] = self.ipadapter_config["weight_type"]
            workflow["103"]["inputs"]["start_at"] = self.ipadapter_config["start_at"]
            workflow["103"]["inputs"]["end_at"] = self.ipadapter_config["end_at"]

        # 注入角色参考图
        self._inject_character_references(workflow, character_ids)

        return workflow

    def _inject_character_references(
        self,
        workflow: Dict[str, Any],
        character_ids: List[str]
    ) -> None:
        """注入角色参考图到工作流

        目前实现: 使用第一个有参考图的角色
        TODO: 支持多角色参考图 (需要多个 IP-Adapter 节点或图像拼接)

        Args:
            workflow: 工作流字典 (会被就地修改)
            character_ids: 角色 ID 列表
        """
        if not self.reference_manager:
            logger.warning("参考图管理器未设置，跳过参考图注入")
            return

        # 找到第一个有参考图的角色
        ref_info = None
        used_char_id = None

        for char_id in character_ids:
            ref = self.reference_manager.get_reference_info(char_id)
            if ref:
                ref_info = ref
                used_char_id = char_id
                break

        if not ref_info:
            logger.warning(f"场景角色 {character_ids} 均无参考图，使用默认值")
            return

        # 更新 LoadImage 节点
        if "102" in workflow:
            # 使用 ComfyUI 中的文件路径
            comfyui_path = ref_info.get("comfyui_path", "")
            # LoadImage 节点只需要文件名（不含路径前缀）
            # 如果有 subfolder，需要在 LoadImage 的特殊格式中处理
            filename = ref_info.get("filename", comfyui_path)

            workflow["102"]["inputs"]["image"] = filename
            logger.info(f"注入角色 {used_char_id} 的参考图: {filename}")

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
