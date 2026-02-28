"""
CosyVoice 语音生成器适配器

使用本地 CosyVoice 服务进行语音合成。
"""
import base64
import tempfile
from pathlib import Path
from typing import Optional

from ..base import (
    AudioGenerator,
    AudioGenerateParams,
    GenerateResult,
    GenerateOptions,
    GeneratorError,
)
from ...tts.cosyvoice_client import CosyVoiceClient
from ...utils.logger import get_logger
from ...utils.config import get_config

logger = get_logger(__name__)


class CosyVoiceAudioGenerator(AudioGenerator):
    """CosyVoice 本地语音生成器
    
    使用本地 CosyVoice 服务进行高质量语音合成。
    支持多种预设音色和自定义参数。
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 120,
    ):
        """初始化 CosyVoice 语音生成器
        
        Args:
            base_url: CosyVoice 服务地址，默认从配置读取
            timeout: 超时时间（秒）
        """
        super().__init__(provider="cosyvoice")
        
        # 从配置读取默认值
        config = get_config()
        self.base_url = base_url or config.local.cosyvoice_url
        self.timeout = timeout
        
        # 初始化客户端
        self.client = CosyVoiceClient(
            base_url=self.base_url,
            timeout=timeout
        )
    
    async def _do_generate(self, params: AudioGenerateParams) -> GenerateResult:
        """执行语音合成"""
        # 检查服务可用性
        if not self.client.check_health():
            raise GeneratorError(
                code="COSYVOICE_UNAVAILABLE",
                message=f"CosyVoice 服务不可用: {self.base_url}"
            )
        
        # 解析选项
        options = params.options or GenerateOptions()
        speed = params.rate or 1.0
        voice_id = params.voice or params.speaker or "narrator_epic"
        
        logger.info(f"[CosyVoice] 开始合成语音: voice={voice_id}, speed={speed}")
        logger.debug(f"[CosyVoice] 文本: {params.text[:100]}...")
        
        try:
            # 调用 CosyVoice 合成
            audio_data = self.client.synthesize(
                text=params.text,
                voice_id=voice_id,
                speed=speed,
                emotion=params.emotion,
            )
            
            # 保存到临时文件
            temp_file = tempfile.NamedTemporaryFile(
                suffix=".wav", delete=False
            )
            temp_file.close()
            audio_data.save(temp_file.name)
            
            logger.info(f"[CosyVoice] 语音合成成功: duration={audio_data.duration:.2f}s")
            
            return GenerateResult(
                success=True,
                local_path=temp_file.name,
                audio_url=None,
                metadata={
                    "provider": "cosyvoice",
                    "duration": audio_data.duration,
                    "sample_rate": audio_data.sample_rate,
                    "voice": voice_id,
                }
            )
            
        except Exception as e:
            logger.error(f"[CosyVoice] 语音合成失败: {e}")
            raise GeneratorError(
                code="COSYVOICE_ERROR",
                message=str(e)
            )
    
    def check_health(self) -> bool:
        """检查服务是否可用"""
        return self.client.check_health()
    
    def list_speakers(self) -> list:
        """获取可用音色列表"""
        return self.client.list_speakers()

