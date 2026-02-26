"""Wan 2.2 本地视频生成器 - 基于 ComfyUI"""
import copy
import random
from pathlib import Path
from typing import Optional, Dict, Any

from ..image.comfyui_client import ComfyUIClient
from ..utils.logger import get_logger
from ..utils.file_utils import load_json

logger = get_logger(__name__)


class WanLocalVideoGenerator:
    """Wan 2.2 本地视频生成器
    
    使用 ComfyUI + Wan 2.2 模型进行图生视频 (I2V)，
    支持 GGUF 量化以适应 16GB 显存。
    
    工作流节点说明:
    - 节点 10: LoadImage - 输入图像
    - 节点 11: CLIP Text Encode (positive)
    - 节点 12: CLIP Text Encode (negative)
    - 节点 20: WanImageToVideo / EmptyHunyuanLatentVideo - 视频设置
    - 节点 30: KSampler - 采样器
    - 节点 40: VAE Decode
    - 节点 50: VHS Video Combine / SaveImage - 输出
    """
    
    def __init__(
        self,
        comfyui_client: ComfyUIClient,
        workflow_path: Optional[Path] = None,
        default_video_length: int = 81,  # 帧数 (约5秒 @ 16fps)
        default_fps: int = 16
    ):
        """初始化 Wan 本地视频生成器
        
        Args:
            comfyui_client: ComfyUI 客户端
            workflow_path: I2V 工作流 JSON 路径
            default_video_length: 默认视频帧数
            default_fps: 默认帧率
        """
        self.client = comfyui_client
        self.default_video_length = default_video_length
        self.default_fps = default_fps
        
        # 加载工作流
        self.workflow = None
        if workflow_path and workflow_path.exists():
            self.workflow = self.client.load_workflow(workflow_path)
            logger.info(f"已加载 Wan I2V 工作流: {workflow_path}")
        else:
            logger.warning("Wan I2V 工作流未找到，需要手动配置")
    
    def generate_video(
        self,
        image_path: Path,
        motion_prompt: str,
        negative_prompt: str = "",
        width: int = 832,
        height: int = 480,
        video_length: Optional[int] = None,
        seed: Optional[int] = None,
        output_prefix: str = "wan_video"
    ) -> Optional[Path]:
        """从图像生成视频
        
        Args:
            image_path: 输入图像路径
            motion_prompt: 运动描述提示词
            negative_prompt: 负向提示词
            width: 视频宽度
            height: 视频高度
            video_length: 视频帧数 (None=使用默认值)
            seed: 随机种子
            output_prefix: 输出文件前缀
            
        Returns:
            生成的视频路径，失败返回 None
        """
        if not self.workflow:
            raise RuntimeError("Wan I2V 工作流未加载")
        
        workflow = copy.deepcopy(self.workflow)
        actual_seed = seed if seed is not None else random.randint(0, 2**32 - 1)
        actual_length = video_length or self.default_video_length
        
        # 上传输入图像到 ComfyUI
        upload_result = self.client.upload_image(image_path)
        if not upload_result:
            logger.error(f"上传图像失败: {image_path}")
            return None
        
        uploaded_filename = upload_result.get("name", image_path.name)
        logger.info(f"图像已上传: {uploaded_filename}")
        
        # 配置工作流参数
        workflow = self._configure_workflow(
            workflow=workflow,
            image_filename=uploaded_filename,
            positive_prompt=motion_prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            video_length=actual_length,
            seed=actual_seed,
            output_prefix=output_prefix
        )
        
        # 执行工作流
        logger.info(f"开始生成视频: {motion_prompt[:50]}...")
        result = self.client.execute_workflow(workflow, wait_for_completion=True)
        
        if result:
            logger.info(f"视频生成完成")
            return result
        else:
            logger.error("视频生成失败")
            return None
    
    def _configure_workflow(
        self,
        workflow: Dict[str, Any],
        image_filename: str,
        positive_prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        video_length: int,
        seed: int,
        output_prefix: str
    ) -> Dict[str, Any]:
        """配置工作流参数"""
        # LoadImage 节点 (节点 10)
        if "10" in workflow:
            workflow["10"]["inputs"]["image"] = image_filename
        
        # CLIP Text Encode positive (节点 11)
        if "11" in workflow:
            workflow["11"]["inputs"]["text"] = positive_prompt
        
        # CLIP Text Encode negative (节点 12)
        if "12" in workflow:
            workflow["12"]["inputs"]["text"] = negative_prompt or "低质量, 模糊, 失真"
        
        # WanImageToVideo / EmptyHunyuanLatentVideo (节点 20)
        if "20" in workflow:
            inputs = workflow["20"]["inputs"]
            if "width" in inputs:
                inputs["width"] = width
            if "height" in inputs:
                inputs["height"] = height
            if "length" in inputs:
                inputs["length"] = video_length
            if "video_frames" in inputs:
                inputs["video_frames"] = video_length
        
        # KSampler (节点 30)
        if "30" in workflow:
            workflow["30"]["inputs"]["seed"] = seed
        
        # 输出节点 (节点 50)
        if "50" in workflow:
            inputs = workflow["50"]["inputs"]
            if "filename_prefix" in inputs:
                inputs["filename_prefix"] = output_prefix
        
        return workflow

