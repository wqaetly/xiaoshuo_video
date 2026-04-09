"""角色设计生成器"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from PIL import Image
from .comfyui_client import ComfyUIClient
from ..utils.logger import get_logger

logger = get_logger(__name__)


class CharacterReferenceManager:
    """角色参考图管理器 - 管理角色的参考图像用于 IP-Adapter 一致性"""

    def __init__(self, comfyui_client: ComfyUIClient, project_dir: Optional[Path] = None):
        self.client = comfyui_client
        self.project_dir = project_dir
        # 角色参考图缓存: {character_id: {"comfyui_path": str, "local_path": Path}}
        self._reference_cache: Dict[str, Dict[str, Any]] = {}

    def set_project_dir(self, project_dir: Path) -> None:
        """设置项目目录"""
        self.project_dir = project_dir
        self._reference_cache.clear()

    def get_reference_dir(self) -> Path:
        """获取角色参考图存储目录"""
        if not self.project_dir:
            raise ValueError("项目目录未设置")
        ref_dir = self.project_dir / "characters" / "references"
        ref_dir.mkdir(parents=True, exist_ok=True)
        return ref_dir

    def load_reference_image(
        self,
        character_id: str,
        image_source: Union[Path, Image.Image, str]
    ) -> Dict[str, Any]:
        """加载角色参考图并上传到 ComfyUI

        Args:
            character_id: 角色ID
            image_source: 图片来源 (本地路径/PIL图像/URL)

        Returns:
            包含 ComfyUI 路径信息的字典
        """
        # 处理不同的图片来源
        if isinstance(image_source, str):
            image_source = Path(image_source)

        if isinstance(image_source, Path):
            if not image_source.exists():
                raise FileNotFoundError(f"参考图不存在: {image_source}")
            image = Image.open(image_source)
            local_path = image_source
        elif isinstance(image_source, Image.Image):
            image = image_source
            # 保存到本地
            local_path = self.get_reference_dir() / f"{character_id}_ref.png"
            image.save(local_path)
        else:
            raise ValueError(f"不支持的图片来源类型: {type(image_source)}")

        # 上传到 ComfyUI
        filename = f"ref_{character_id}.png"
        upload_result = self.client.upload_image(
            image=image,
            filename=filename,
            subfolder="character_refs",
            overwrite=True
        )

        # 构建 ComfyUI 中的完整路径
        comfyui_path = upload_result.get("name", filename)
        subfolder = upload_result.get("subfolder", "character_refs")
        if subfolder:
            comfyui_path = f"{subfolder}/{comfyui_path}"

        # 缓存信息
        ref_info = {
            "comfyui_path": comfyui_path,
            "local_path": local_path,
            "filename": upload_result.get("name", filename),
            "subfolder": subfolder
        }
        self._reference_cache[character_id] = ref_info

        logger.info(f"角色 {character_id} 参考图已上传: {comfyui_path}")
        return ref_info

    def get_reference_info(self, character_id: str) -> Optional[Dict[str, Any]]:
        """获取角色的参考图信息"""
        return self._reference_cache.get(character_id)

    def has_reference(self, character_id: str) -> bool:
        """检查角色是否有参考图"""
        return character_id in self._reference_cache

    def create_composite_reference(
        self,
        character_ids: List[str],
        target_width: int = 1280,
        target_height: int = 720
    ) -> Optional[Dict[str, Any]]:
        """创建多角色合成参考图

        将多个角色的参考图水平拼接成一张合成图，用于多角色场景的一致性控制。
        单角色时直接返回其已有参考图信息。

        Args:
            character_ids: 要包含的角色 ID 列表
            target_width: 合成图目标宽度
            target_height: 合成图目标高度

        Returns:
            参考图信息字典（与 load_reference_image 返回格式一致），无参考图时返回 None
        """
        # 收集所有有参考图的角色
        ref_images = []
        ref_char_ids = []
        for char_id in character_ids:
            ref_info = self.get_reference_info(char_id)
            if ref_info:
                local_path = ref_info.get("local_path")
                if local_path and Path(local_path).exists():
                    try:
                        img = Image.open(local_path)
                        ref_images.append(img)
                        ref_char_ids.append(char_id)
                    except Exception as e:
                        logger.warning(f"打开角色 {char_id} 参考图失败: {e}")

        if not ref_images:
            return None

        if len(ref_images) == 1:
            return self.get_reference_info(ref_char_ids[0])

        # 多角色：水平拼接
        n = len(ref_images)
        cell_width = target_width // n
        cell_height = target_height

        composite = Image.new("RGB", (target_width, target_height), (255, 255, 255))

        for i, img in enumerate(ref_images):
            # 按比例缩放到单元格内
            img_ratio = img.width / img.height
            cell_ratio = cell_width / cell_height

            if img_ratio > cell_ratio:
                new_w = cell_width
                new_h = int(cell_width / img_ratio)
            else:
                new_h = cell_height
                new_w = int(cell_height * img_ratio)

            resized = img.resize((new_w, new_h), Image.LANCZOS)

            # 居中放置
            x_offset = i * cell_width + (cell_width - new_w) // 2
            y_offset = (cell_height - new_h) // 2
            composite.paste(resized, (x_offset, y_offset))

        # 缓存键
        composite_key = "composite_" + "_".join(sorted(ref_char_ids))

        # 上传到 ComfyUI
        filename = f"ref_{composite_key}.png"
        upload_result = self.client.upload_image(
            image=composite,
            filename=filename,
            subfolder="character_refs",
            overwrite=True
        )

        comfyui_path = upload_result.get("name", filename)
        subfolder = upload_result.get("subfolder", "character_refs")
        if subfolder:
            comfyui_path = f"{subfolder}/{comfyui_path}"

        # 本地保存
        local_path = self.get_reference_dir() / f"{composite_key}.png"
        composite.save(local_path)

        ref_info = {
            "comfyui_path": comfyui_path,
            "local_path": local_path,
            "filename": upload_result.get("name", filename),
            "subfolder": subfolder,
            "is_composite": True,
            "source_characters": ref_char_ids
        }

        self._reference_cache[composite_key] = ref_info
        logger.info(f"创建合成参考图: {ref_char_ids} -> {comfyui_path}")
        return ref_info

    def load_from_characters_json(
        self,
        characters: Dict[str, Any],
        base_dir: Optional[Path] = None
    ) -> Dict[str, Dict[str, Any]]:
        """从角色配置中批量加载参考图

        Args:
            characters: 角色配置字典 (包含 characters 列表)
            base_dir: 参考图基础目录

        Returns:
            已加载的角色参考图信息
        """
        base_dir = base_dir or self.get_reference_dir()
        loaded = {}
        logger.debug(f"参考图搜索基础目录: {base_dir}")

        for char in characters.get("characters", []):
            char_id = char.get("id")
            if not char_id:
                continue

            # 尝试多种参考图路径
            ref_paths = []

            # 1. 从 reference_images 字段获取
            if "reference_images" in char and char["reference_images"]:
                ref_paths.extend(char["reference_images"])

            # 2. 尝试默认路径: {base_dir}/{char_id}/front.png
            #    base_dir 通常为 project/characters，生成的参考图在 characters/{char_id}/front.png
            default_ref = base_dir / char_id / "front.png"
            if default_ref.exists():
                ref_paths.append(str(default_ref))

            # 3. 尝试 references 子目录
            ref_file = base_dir / "references" / f"{char_id}_ref.png"
            if ref_file.exists():
                ref_paths.append(str(ref_file))

            # 4. 尝试直接在 base_dir 下查找
            ref_file_flat = base_dir / f"{char_id}_ref.png"
            if ref_file_flat.exists():
                ref_paths.append(str(ref_file_flat))

            if not ref_paths:
                logger.warning(f"角色 {char_id} 未找到任何参考图，搜索路径: "
                             f"{base_dir / char_id / 'front.png'}, "
                             f"{base_dir / 'references' / f'{char_id}_ref.png'}, "
                             f"{base_dir / f'{char_id}_ref.png'}")
            else:
                logger.debug(f"角色 {char_id} 找到 {len(ref_paths)} 个候选参考图: {ref_paths}")

            # 加载第一个有效的参考图
            for ref_path in ref_paths:
                try:
                    path = Path(ref_path)
                    if path.exists():
                        ref_info = self.load_reference_image(char_id, path)
                        loaded[char_id] = ref_info
                        logger.info(f"角色 {char_id} 参考图加载成功: {path}")
                        break
                except Exception as e:
                    logger.warning(f"加载角色 {char_id} 参考图失败 ({ref_path}): {e}")

        logger.info(f"参考图加载完成: {len(loaded)}/{len(characters.get('characters', []))} 个角色")
        return loaded

    def clear_cache(self) -> None:
        """清空参考图缓存"""
        self._reference_cache.clear()


class CharacterDesigner:
    """角色设计生成器 - 生成角色立绘和参考图"""

    def __init__(
        self,
        comfyui_client: ComfyUIClient,
        workflow_path: Optional[Path] = None,
        default_checkpoint: str = "animagine-xl-4.0.safetensors"
    ):
        self.client = comfyui_client
        self.default_checkpoint = default_checkpoint
        # 添加参考图管理器
        self.reference_manager = CharacterReferenceManager(comfyui_client)

        # 加载工作流模板（优先使用传入的工作流，否则使用默认的 Z-Image-Turbo）
        self.workflow_template = None
        if workflow_path and workflow_path.exists():
            import json
            with open(workflow_path, "r", encoding="utf-8") as f:
                self.workflow_template = json.load(f)
            logger.info(f"加载角色设计工作流: {workflow_path}")
        else:
            # 尝试加载默认的 Z-Image-Turbo 工作流
            default_workflow = Path("config/comfyui_workflows/z_image_turbo_scene.json")
            if default_workflow.exists():
                import json
                with open(default_workflow, "r", encoding="utf-8") as f:
                    self.workflow_template = json.load(f)
                logger.info(f"加载默认角色设计工作流: {default_workflow}")

    def generate_character(
        self,
        character: Dict[str, Any],
        output_dir: Path,
        views: List[str] = None,
        register_reference: bool = True
    ) -> Dict[str, Path]:
        """为角色生成多角度参考图

        Args:
            character: 角色配置字典
            output_dir: 输出目录
            views: 要生成的视图列表
            register_reference: 是否自动将 front 视图注册为 IP-Adapter 参考图

        Returns:
            生成的图像路径字典 {view: path}
        """
        views = views or ["front", "side", "expression_happy", "expression_angry"]
        char_id = character.get("id", "char_unknown")
        char_name = character.get("name", "未知角色")

        logger.info(f"开始生成角色 {char_name} 的参考图...")

        results = {}
        seeds_used = {}
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
                image, seed_used = self._generate_single(view_prompt, negative_prompt)

                output_path = char_dir / f"{view}.png"
                image.save(output_path)
                results[view] = output_path
                seeds_used[view] = seed_used

                logger.info(f"  生成 {view} 视图完成 (seed: {seed_used})")
            except Exception as e:
                logger.error(f"  生成 {view} 视图失败: {e}")
                results[view] = None

        # 保存种子信息用于复现
        if seeds_used:
            import json as _json
            seeds_file = char_dir / "seeds.json"
            with open(seeds_file, "w", encoding="utf-8") as f:
                _json.dump(seeds_used, f, indent=2)

        # 自动注册 front 视图作为 IP-Adapter 参考图
        if register_reference and "front" in results and results["front"]:
            try:
                self.reference_manager.load_reference_image(char_id, results["front"])
                logger.info(f"角色 {char_name} 的参考图已注册到 IP-Adapter")
            except Exception as e:
                logger.warning(f"注册角色参考图失败: {e}")

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
        height: int = 1024,
        seed: Optional[int] = None
    ) -> tuple:
        """生成单张图像

        如果有工作流模板，使用 Z-Image-Turbo 工作流；
        否则回退到传统的 CheckpointLoaderSimple 方式（需要对应模型）

        Returns:
            (PIL.Image, int) - 生成的图像和使用的种子
        """
        import random
        import copy

        actual_seed = seed if seed is not None else random.randint(0, 2**32 - 1)

        # 优先使用 Z-Image-Turbo 工作流模板
        if self.workflow_template:
            workflow = copy.deepcopy(self.workflow_template)

            # 设置提示词（Z-Image-Turbo 工作流只使用正向提示词，负向通过 ConditioningZeroOut 处理）
            if "6" in workflow:
                workflow["6"]["inputs"]["text"] = positive_prompt

            # 设置尺寸（角色立绘使用竖版）
            if "5" in workflow:
                workflow["5"]["inputs"]["width"] = width
                workflow["5"]["inputs"]["height"] = height

            # 设置种子
            if "3" in workflow:
                workflow["3"]["inputs"]["seed"] = actual_seed

            # 修改文件名前缀
            if "9" in workflow:
                workflow["9"]["inputs"]["filename_prefix"] = "character"
        else:
            # 回退到传统工作流（需要 CheckpointLoaderSimple 支持的模型）
            logger.warning("未找到 Z-Image-Turbo 工作流，使用传统工作流（可能不可用）")
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
                        "seed": actual_seed,
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
            return images[0], actual_seed
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
