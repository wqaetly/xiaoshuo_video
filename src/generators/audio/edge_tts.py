"""
Edge TTS 语音生成器适配器

使用微软 Edge TTS API 进行语音合成（免费云端）。
"""
import tempfile
from pathlib import Path
from typing import Optional, List, Dict

from ..base import (
    AudioGenerator,
    AudioGenerateParams,
    GenerateResult,
    GenerateOptions,
    GeneratorError,
)
from ...tts.edge_tts_client import EdgeTTSClient
from ...utils.logger import get_logger

logger = get_logger(__name__)


class EdgeTTSAudioGenerator(AudioGenerator):
    """Edge TTS 云端语音生成器
    
    使用微软 Edge 浏览器 TTS API 进行语音合成。
    免费、无需配置、支持多语言和多音色。
    """
    
    def __init__(
        self,
        default_voice: Optional[str] = None,
    ):
        """初始化 Edge TTS 语音生成器
        
        Args:
            default_voice: 默认音色（如 zh-CN-YunxiNeural）
        """
        super().__init__(provider="edge_tts")
        
        # 初始化客户端
        self.client = EdgeTTSClient(
            default_voice=default_voice or "zh-CN-YunxiNeural"
        )
    
    async def _do_generate(self, params: AudioGenerateParams) -> GenerateResult:
        """执行语音合成"""
        # 检查 edge-tts 可用性
        if not self.client.check_health():
            raise GeneratorError(
                code="EDGE_TTS_UNAVAILABLE",
                message="edge-tts 未安装，请运行: pip install edge-tts"
            )
        
        # 解析选项
        options = params.options or GenerateOptions()
        speed = params.rate or 1.0
        voice_id = params.voice or params.speaker
        
        logger.info(f"[EdgeTTS] 开始合成语音: voice={voice_id}, speed={speed}")
        logger.debug(f"[EdgeTTS] 文本: {params.text[:100]}...")
        
        try:
            # 保存到临时文件
            temp_file = tempfile.NamedTemporaryFile(
                suffix=".mp3", delete=False
            )
            temp_file.close()
            
            # 使用 Edge TTS 合成
            output_path = self.client.synthesize_to_file(
                text=params.text,
                output_path=Path(temp_file.name),
                voice_id=voice_id,
                speed=speed,
            )
            
            # 读取音频数据计算时长（简单估算）
            file_size = output_path.stat().st_size
            # MP3 平均比特率约 128kbps
            estimated_duration = file_size / (128 * 1024 / 8)
            
            logger.info(f"[EdgeTTS] 语音合成成功: ~{estimated_duration:.2f}s")
            
            return GenerateResult(
                success=True,
                local_path=str(output_path),
                audio_url=None,
                metadata={
                    "provider": "edge_tts",
                    "estimated_duration": estimated_duration,
                    "voice": voice_id,
                }
            )
            
        except Exception as e:
            logger.error(f"[EdgeTTS] 语音合成失败: {e}")
            raise GeneratorError(
                code="EDGE_TTS_ERROR",
                message=str(e)
            )
    
    def check_health(self) -> bool:
        """检查服务是否可用"""
        return self.client.check_health()
    
    async def list_voices(self) -> List[Dict[str, str]]:
        """获取可用音色列表（异步）"""
        return await self.client.list_voices()
    
    def list_voices_sync(self) -> List[Dict[str, str]]:
        """获取可用音色列表（同步）"""
        return self.client.list_voices_sync()

