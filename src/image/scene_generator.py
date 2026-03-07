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

    支持三种角色一致性模式:
    1. 基础模式 (none): 仅使用文本提示词生成场景图像
    2. Z-Image-i2L 模式 (i2l): 从参考图即时生成 LoRA 实现角色一致性 (推荐)
    3. IP-Adapter 模式 (ipadapter): 传统图像特征注入方式
    """

    def __init__(
        self,
        comfyui_client: ComfyUIClient,
        workflow_path: Optional[Path] = None,
        ipadapter_workflow_path: Optional[Path] = None,
        i2l_workflow_path: Optional[Path] = None,
        default_checkpoint: str = "z_image_turbo_bf16.safetensors",
        reference_manager: Optional["CharacterReferenceManager"] = None,
        consistency_method: str = "none"
    ):
        """初始化场景生成器

        Args:
            comfyui_client: ComfyUI 客户端
            workflow_path: 基础工作流路径
            ipadapter_workflow_path: IP-Adapter 工作流路径
            i2l_workflow_path: Z-Image-i2L 工作流路径
            default_checkpoint: 默认模型检查点
            reference_manager: 角色参考图管理器 (启用角色一致性功能)
            consistency_method: 角色一致性方法 ("i2l" / "ipadapter" / "none")
        """
        self.client = comfyui_client
        self.default_checkpoint = default_checkpoint
        self.reference_manager = reference_manager
        self.consistency_method = consistency_method  # i2l / ipadapter / none

        # IP-Adapter 配置
        self.ipadapter_config = {
            "enabled": consistency_method == "ipadapter" and reference_manager is not None,
            "weight": 0.8,
            "noise": 0.0,
            "weight_type": "standard",
            "start_at": 0.0,
            "end_at": 1.0
        }

        # Z-Image-i2L 配置
        self.i2l_config = {
            "enabled": consistency_method == "i2l" and reference_manager is not None,
            "lora_strength": 1.0,
            "apply_to_unet": True
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

        # 加载 Z-Image-i2L 工作流 (如果存在)
        self.i2l_workflow = None
        if i2l_workflow_path and i2l_workflow_path.exists():
            self.i2l_workflow = self.client.load_workflow(i2l_workflow_path)

    def set_reference_manager(self, manager: "CharacterReferenceManager") -> None:
        """设置角色参考图管理器"""
        self.reference_manager = manager
        # 根据当前一致性方法启用对应配置
        if self.consistency_method == "ipadapter":
            self.ipadapter_config["enabled"] = True
        elif self.consistency_method == "i2l":
            self.i2l_config["enabled"] = True

    def set_consistency_method(self, method: str) -> None:
        """设置角色一致性方法

        Args:
            method: "i2l" / "ipadapter" / "none"
        """
        self.consistency_method = method
        has_manager = self.reference_manager is not None
        self.ipadapter_config["enabled"] = (method == "ipadapter" and has_manager)
        self.i2l_config["enabled"] = (method == "i2l" and has_manager)

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

    def configure_i2l(
        self,
        lora_strength: float = 1.0,
        apply_to_unet: bool = True
    ) -> None:
        """配置 Z-Image-i2L 参数

        Args:
            lora_strength: LoRA 强度 (0.0-2.0), 值越大角色越一致
            apply_to_unet: 是否应用到 UNET
        """
        self.i2l_config.update({
            "lora_strength": lora_strength,
            "apply_to_unet": apply_to_unet
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
            use_ipadapter: 是否使用 IP-Adapter (None=自动判断, 兼容旧代码)

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

        # 决定使用哪种角色一致性方法
        method = self._get_consistency_method(character_ids, use_ipadapter)

        if method == "i2l":
            logger.info(f"场景 {scene_id} 启用 Z-Image-i2L 角色一致性")
            workflow = self._build_i2l_workflow(
                positive_prompt=positive_prompt,
                width=width,
                height=height,
                seed=seed,
                scene_id=scene_id,
                character_ids=character_ids
            )
        elif method == "ipadapter":
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
            # 使用基础工作流 (无角色一致性)
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

    def _get_consistency_method(
        self,
        character_ids: List[str],
        use_ipadapter: Optional[bool]
    ) -> str:
        """获取应该使用的角色一致性方法

        Args:
            character_ids: 场景中的角色 ID 列表
            use_ipadapter: 兼容旧接口 (True=ipadapter, False=none, None=自动)

        Returns:
            方法名: "i2l" / "ipadapter" / "none"
        """
        # 兼容旧接口: 如果明确指定了 use_ipadapter
        if use_ipadapter is not None:
            if use_ipadapter:
                return "ipadapter" if self.ipadapter_workflow else "none"
            return "none"

        # 场景中无角色，不需要一致性
        if not character_ids:
            return "none"

        # 无参考图管理器
        if not self.reference_manager:
            return "none"

        # 检查是否有任何角色有参考图
        has_reference = any(
            self.reference_manager.has_reference(char_id)
            for char_id in character_ids
        )
        if not has_reference:
            return "none"

        # 根据配置的一致性方法和可用的工作流决定
        if self.consistency_method == "i2l" and self.i2l_config.get("enabled") and self.i2l_workflow:
            return "i2l"
        elif self.consistency_method == "ipadapter" and self.ipadapter_config.get("enabled") and self.ipadapter_workflow:
            return "ipadapter"

        # 回退: 检查哪个方法可用
        if self.i2l_workflow and self.i2l_config.get("enabled"):
            return "i2l"
        if self.ipadapter_workflow and self.ipadapter_config.get("enabled"):
            return "ipadapter"

        return "none"

    def _should_use_ipadapter(
        self,
        character_ids: List[str],
        use_ipadapter: Optional[bool]
    ) -> bool:
        """判断是否应该使用 IP-Adapter (兼容旧代码)

        Args:
            character_ids: 场景中的角色 ID 列表
            use_ipadapter: 用户指定的选项 (None=自动)

        Returns:
            是否使用 IP-Adapter
        """
        return self._get_consistency_method(character_ids, use_ipadapter) == "ipadapter"
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
        同时添加风格前缀以控制整体画面风格。
        """
        visual = scene.get("visual", {})

        # 获取风格前缀（中文描述，适配 Z-Image-Turbo）
        style_prefix = self._get_style_prefix_chinese(style_preset)

        # 直接使用场景的中文描述（Z-Image-Turbo 对中文优化更好）
        description = visual.get("description", "")
        if not description:
            description = "一幅精美的场景画面"

        # 组合风格前缀和场景描述
        if style_prefix:
            return f"{style_prefix}，{description}"
        return description

    def _get_style_prefix_chinese(self, style_preset: str) -> str:
        """获取中文风格前缀（适配 Z-Image-Turbo 的 Qwen 词法分析器）"""
        presets = {
            "anime": "动漫风格，色彩鲜艳，精美插画",
            "realistic": "照片写实风格，电影级光影，细节丰富",
            "illustration": "数字插画风格，概念艺术，艺术感",
            "realistic_gufeng": "写实古风，照片级真实感，中国古代美学，汉服飘逸，古典东方韵味，柔和自然光，精致面容，皮肤质感真实，服饰纹理精细，电影级构图",
            "chinese_fantasy": "中国仙侠风格，修仙世界，剑仙飘逸，云雾缭绕，古典建筑，白衣飘飘，灵气光环，仙山云海，史诗场景",
            "xianxia": "仙侠风格，修真世界，御剑飞行，仙云缥缈，古风建筑，飘逸长袍，灵气环绕，仙境山峰，史诗画面"
        }
        return presets.get(style_preset, presets.get("realistic_gufeng", ""))

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

    def _build_i2l_workflow(
        self,
        positive_prompt: str,
        width: int,
        height: int,
        seed: Optional[int],
        scene_id: str,
        character_ids: List[str]
    ) -> Dict[str, Any]:
        """构建带 Z-Image-i2L 的工作流

        Z-Image-i2L 通过从参考图即时生成 LoRA 来实现角色一致性，
        比 IP-Adapter 更轻量且效果更稳定。

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
        if not self.i2l_workflow:
            raise RuntimeError("Z-Image-i2L 工作流未加载")

        workflow = copy.deepcopy(self.i2l_workflow)

        # 设置正向提示词 (节点 6: CLIP Text Encode)
        if "6" in workflow:
            workflow["6"]["inputs"]["text"] = positive_prompt

        # 设置图像尺寸 (节点 5: EmptySD3LatentImage)
        if "5" in workflow:
            workflow["5"]["inputs"]["width"] = width
            workflow["5"]["inputs"]["height"] = height

        # 设置种子 (节点 3: KSampler)
        if "3" in workflow:
            workflow["3"]["inputs"]["seed"] = seed if seed is not None else random.randint(0, 2**32 - 1)

        # 设置输出文件名 (节点 9: SaveImage)
        if "9" in workflow:
            workflow["9"]["inputs"]["filename_prefix"] = scene_id

        # 配置 Z-Image-i2L 参数 (节点 201: ZImageI2L)
        if "201" in workflow:
            workflow["201"]["inputs"]["lora_strength"] = self.i2l_config.get("lora_strength", 1.0)
            workflow["201"]["inputs"]["apply_to_unet"] = self.i2l_config.get("apply_to_unet", True)

        # 注入角色参考图到 LoadImage 节点 (节点 200)
        self._inject_i2l_reference(workflow, character_ids)

        return workflow

    def _inject_i2l_reference(
        self,
        workflow: Dict[str, Any],
        character_ids: List[str]
    ) -> None:
        """注入角色参考图到 i2L 工作流

        Args:
            workflow: 工作流字典 (会被就地修改)
            character_ids: 角色 ID 列表
        """
        if not self.reference_manager:
            logger.warning("参考图管理器未设置，跳过 i2L 参考图注入")
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
            logger.warning(f"场景角色 {character_ids} 均无参考图，i2L 将使用默认值")
            return

        # 更新 LoadImage 节点 (节点 200 用于 i2L)
        if "200" in workflow:
            filename = ref_info.get("filename", ref_info.get("comfyui_path", ""))
            workflow["200"]["inputs"]["image"] = filename
            logger.info(f"i2L 注入角色 {used_char_id} 的参考图: {filename}")

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
