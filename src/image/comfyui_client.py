"""ComfyUI API客户端"""
import json
import time
import uuid
import io
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import requests
from PIL import Image
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ComfyUIClient:
    """ComfyUI WebSocket/HTTP API客户端"""

    def __init__(
        self,
        base_url: str = "http://localhost:8188",
        timeout: int = 300
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client_id = str(uuid.uuid4())
        self._session = requests.Session()

    def check_health(self) -> bool:
        """检查ComfyUI服务是否可用"""
        try:
            response = self._session.get(
                f"{self.base_url}/system_stats",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"ComfyUI服务检查失败: {e}")
            return False

    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            response = self._session.get(
                f"{self.base_url}/system_stats",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {}

    def upload_image(
        self,
        image: Union[Image.Image, Path, bytes],
        filename: Optional[str] = None,
        subfolder: str = "input",
        overwrite: bool = True
    ) -> Dict[str, str]:
        """上传图片到ComfyUI"""
        if isinstance(image, Path):
            with open(image, "rb") as f:
                image_data = f.read()
            filename = filename or image.name
        elif isinstance(image, Image.Image):
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            image_data = buffer.getvalue()
            filename = filename or f"{uuid.uuid4()}.png"
        else:
            image_data = image
            filename = filename or f"{uuid.uuid4()}.png"

        files = {
            "image": (filename, image_data, "image/png")
        }
        data = {
            "subfolder": subfolder,
            "overwrite": str(overwrite).lower()
        }

        try:
            response = self._session.post(
                f"{self.base_url}/upload/image",
                files=files,
                data=data,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"图片上传失败: {e}")
            raise

    def queue_prompt(self, workflow: Dict[str, Any]) -> str:
        """提交工作流到队列"""
        payload = {
            "prompt": workflow,
            "client_id": self.client_id
        }

        try:
            response = self._session.post(
                f"{self.base_url}/prompt",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            prompt_id = data.get("prompt_id")
            logger.info(f"工作流已提交, prompt_id: {prompt_id}")
            return prompt_id
        except Exception as e:
            logger.error(f"提交工作流失败: {e}")
            raise

    def get_history(self, prompt_id: str) -> Dict[str, Any]:
        """获取历史记录"""
        try:
            response = self._session.get(
                f"{self.base_url}/history/{prompt_id}",
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取历史记录失败: {e}")
            return {}

    def get_image(
        self,
        filename: str,
        subfolder: str = "",
        folder_type: str = "output"
    ) -> bytes:
        """获取生成的图片"""
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type
        }

        try:
            response = self._session.get(
                f"{self.base_url}/view",
                params=params,
                timeout=60
            )
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"获取图片失败: {e}")
            raise

    def wait_for_completion(
        self,
        prompt_id: str,
        timeout: Optional[int] = None,
        poll_interval: float = 1.0
    ) -> Dict[str, Any]:
        """等待工作流完成"""
        timeout = timeout or self.timeout
        start_time = time.time()

        while time.time() - start_time < timeout:
            history = self.get_history(prompt_id)

            if prompt_id in history:
                result = history[prompt_id]
                status = result.get("status", {})

                if status.get("completed", False):
                    logger.info(f"工作流完成: {prompt_id}")
                    return result

                if "error" in status:
                    error_msg = status.get("error", "未知错误")
                    logger.error(f"工作流执行失败: {error_msg}")
                    raise RuntimeError(f"ComfyUI工作流失败: {error_msg}")

            time.sleep(poll_interval)

        raise TimeoutError(f"工作流执行超时: {prompt_id}")

    def execute_workflow(
        self,
        workflow: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> List[Image.Image]:
        """执行工作流并返回生成的图片"""
        # 提交工作流
        prompt_id = self.queue_prompt(workflow)

        # 等待完成
        result = self.wait_for_completion(prompt_id, timeout)

        # 收集生成的图片
        images = []
        outputs = result.get("outputs", {})

        for node_id, node_output in outputs.items():
            if "images" in node_output:
                for img_info in node_output["images"]:
                    img_data = self.get_image(
                        filename=img_info["filename"],
                        subfolder=img_info.get("subfolder", ""),
                        folder_type=img_info.get("type", "output")
                    )
                    image = Image.open(io.BytesIO(img_data))
                    images.append(image)

        return images

    def load_workflow(self, workflow_path: Path) -> Dict[str, Any]:
        """加载工作流JSON文件"""
        with open(workflow_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def interrupt(self) -> bool:
        """中断当前执行"""
        try:
            response = self._session.post(
                f"{self.base_url}/interrupt",
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"中断执行失败: {e}")
            return False

    def clear_queue(self) -> bool:
        """清空队列"""
        try:
            response = self._session.post(
                f"{self.base_url}/queue",
                json={"clear": True},
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"清空队列失败: {e}")
            return False
