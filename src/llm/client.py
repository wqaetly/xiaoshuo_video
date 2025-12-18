"""Ollama LLM客户端"""
import json
from typing import Optional, List, Dict, Any, Generator
import requests
from ..utils.logger import get_logger

logger = get_logger(__name__)


class OllamaClient:
    """Ollama API客户端"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:14b",
        timeout: int = 300
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._session = requests.Session()

    def check_health(self) -> bool:
        """检查服务是否可用"""
        try:
            response = self._session.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama服务检查失败: {e}")
            return False

    def list_models(self) -> List[str]:
        """列出可用模型"""
        try:
            response = self._session.get(f"{self.base_url}/api/tags", timeout=10)
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.error(f"获取模型列表失败: {e}")
            return []

    def chat(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False
    ) -> str:
        """发送聊天请求"""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        return self.chat_messages(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream
        )

    def chat_messages(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False
    ) -> str:
        """使用消息列表进行聊天"""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }

        try:
            if stream:
                return self._chat_stream(payload)
            else:
                return self._chat_sync(payload)
        except Exception as e:
            logger.error(f"LLM请求失败: {e}")
            raise

    def _chat_sync(self, payload: Dict[str, Any]) -> str:
        """同步聊天"""
        response = self._session.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "")

    def _chat_stream(self, payload: Dict[str, Any]) -> Generator[str, None, None]:
        """流式聊天"""
        response = self._session.post(
            f"{self.base_url}/api/chat",
            json=payload,
            stream=True,
            timeout=self.timeout
        )
        response.raise_for_status()

        full_response = ""
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                content = data.get("message", {}).get("content", "")
                full_response += content
                yield content

        return full_response

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> str:
        """生成文本 (使用generate API)"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system or "",
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }

        try:
            response = self._session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
        except Exception as e:
            logger.error(f"LLM生成失败: {e}")
            raise

    def embed(self, text: str) -> List[float]:
        """生成文本嵌入"""
        payload = {
            "model": self.model,
            "prompt": text,
        }

        try:
            response = self._session.post(
                f"{self.base_url}/api/embeddings",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            return data.get("embedding", [])
        except Exception as e:
            logger.error(f"嵌入生成失败: {e}")
            raise
