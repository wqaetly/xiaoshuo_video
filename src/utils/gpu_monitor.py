"""GPU 显存监控模块

提供显存使用监控和动态并发数调整功能。
使用 pynvml 库访问 NVIDIA GPU 的显存信息。
"""
from dataclasses import dataclass
from typing import Optional, Tuple
from .logger import get_logger

logger = get_logger(__name__)

# 尝试导入 pynvml，如果失败则禁用 GPU 监控
_PYNVML_AVAILABLE = False
try:
    import pynvml
    _PYNVML_AVAILABLE = True
except ImportError:
    logger.debug("pynvml 未安装，GPU 监控功能不可用")


@dataclass
class GPUMemoryInfo:
    """GPU 显存信息"""
    device_index: int = 0
    device_name: str = "未知"
    total_mb: float = 0.0
    used_mb: float = 0.0
    free_mb: float = 0.0
    utilization_percent: float = 0.0
    
    @property
    def available_percent(self) -> float:
        """可用显存百分比"""
        if self.total_mb == 0:
            return 0.0
        return (self.free_mb / self.total_mb) * 100


class GPUMonitor:
    """GPU 显存监控器
    
    监控 NVIDIA GPU 的显存使用情况，并根据显存占用动态调整并发任务数。
    """
    
    def __init__(self, device_index: int = 0):
        """初始化 GPU 监控器
        
        Args:
            device_index: GPU 设备索引，默认为 0
        """
        self.device_index = device_index
        self._initialized = False
        self._handle = None
        
        if _PYNVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                self._handle = pynvml.nvmlDeviceGetHandleByIndex(device_index)
                self._initialized = True
                logger.info(f"GPU 监控器初始化成功 (设备 {device_index})")
            except Exception as e:
                logger.warning(f"GPU 监控器初始化失败: {e}")
    
    def __del__(self):
        """清理 pynvml 资源"""
        if self._initialized and _PYNVML_AVAILABLE:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass
    
    @property
    def is_available(self) -> bool:
        """检查 GPU 监控是否可用"""
        return self._initialized
    
    def get_memory_info(self) -> GPUMemoryInfo:
        """获取当前 GPU 显存信息
        
        Returns:
            GPUMemoryInfo 包含显存使用详情
        """
        if not self._initialized:
            return GPUMemoryInfo()
        
        try:
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(self._handle)
            name = pynvml.nvmlDeviceGetName(self._handle)
            if isinstance(name, bytes):
                name = name.decode('utf-8')
            
            total_mb = mem_info.total / (1024 * 1024)
            used_mb = mem_info.used / (1024 * 1024)
            free_mb = mem_info.free / (1024 * 1024)
            utilization = (used_mb / total_mb) * 100 if total_mb > 0 else 0
            
            return GPUMemoryInfo(
                device_index=self.device_index,
                device_name=name,
                total_mb=total_mb,
                used_mb=used_mb,
                free_mb=free_mb,
                utilization_percent=utilization
            )
        except Exception as e:
            logger.error(f"获取 GPU 显存信息失败: {e}")
            return GPUMemoryInfo()
    
    def calculate_optimal_workers(
        self,
        min_workers: int = 1,
        max_workers: int = 4,
        memory_per_task_mb: float = 2000.0,
        safety_margin: float = 0.2
    ) -> int:
        """根据当前显存可用量计算最优并发数
        
        Args:
            min_workers: 最小并发数
            max_workers: 最大并发数
            memory_per_task_mb: 每个任务预估占用的显存 (MB)
            safety_margin: 安全边际比例 (预留部分显存)
        
        Returns:
            推荐的并发任务数
        """
        if not self._initialized:
            logger.debug("GPU 监控不可用，返回默认并发数")
            return max(min_workers, min(2, max_workers))
        
        mem = self.get_memory_info()
        available_mb = mem.free_mb * (1 - safety_margin)
        
        optimal = int(available_mb / memory_per_task_mb)
        optimal = max(min_workers, min(optimal, max_workers))
        
        logger.debug(
            f"显存状态: {mem.used_mb:.0f}/{mem.total_mb:.0f}MB "
            f"({mem.utilization_percent:.1f}%) | 推荐并发数: {optimal}"
        )
        
        return optimal
    
    def should_reduce_concurrency(self, threshold_percent: float = 85.0) -> bool:
        """检查是否应该降低并发数（显存占用过高）"""
        if not self._initialized:
            return False
        mem = self.get_memory_info()
        return mem.utilization_percent >= threshold_percent


# 全局单例
_gpu_monitor: Optional[GPUMonitor] = None


def get_gpu_monitor(device_index: int = 0) -> GPUMonitor:
    """获取 GPU 监控器单例"""
    global _gpu_monitor
    if _gpu_monitor is None:
        _gpu_monitor = GPUMonitor(device_index)
    return _gpu_monitor

