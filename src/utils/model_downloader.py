"""
通用模型检测与下载工具

在 pipeline 初始化时自动检测所需模型文件是否存在，
缺失则自动从 HuggingFace 下载。支持断点续传。
"""
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import requests
from .logger import get_logger

logger = get_logger(__name__)

# HuggingFace 基础 URL
HF_BASE = "https://huggingface.co"
# 镜像源（国内加速）
HF_MIRROR = os.environ.get("HF_MIRROR", "https://hf-mirror.com")

# Wan 2.2 I2V 14B MoE 模型配置
# MoE 架构：高噪声专家 + 低噪声专家，27B 总参数但每步仅激活 14B
# 使用 fp8 量化版以适配 16GB 显存
WAN21_MODELS: Dict[str, Dict[str, str]] = {
    "diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors": {
        "repo": "Comfy-Org/Wan_2.2_ComfyUI_repackaged",
        "path": "split_files/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors",
        "desc": "Wan 2.2 I2V 高噪声专家模型 (FP8, ~14GB)",
    },
    "diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors": {
        "repo": "Comfy-Org/Wan_2.2_ComfyUI_repackaged",
        "path": "split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors",
        "desc": "Wan 2.2 I2V 低噪声专家模型 (FP8, ~14GB)",
    },
    "text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors": {
        "repo": "Comfy-Org/Wan_2.2_ComfyUI_repackaged",
        "path": "split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors",
        "desc": "UMT5-XXL 文本编码器 (FP8, ~5GB)",
    },
    "vae/wan_2.1_vae.safetensors": {
        "repo": "Comfy-Org/Wan_2.2_ComfyUI_repackaged",
        "path": "split_files/vae/wan_2.1_vae.safetensors",
        "desc": "Wan VAE 解码器 (~300MB)",
    },
    "clip_vision/clip_vision_h.safetensors": {
        "repo": "Comfy-Org/Wan_2.1_ComfyUI_repackaged",
        "path": "split_files/clip_vision/clip_vision_h.safetensors",
        "desc": "CLIP Vision 模型 (I2V 所需, ~3.9GB)",
    },
}


def _get_download_url(repo: str, file_path: str) -> str:
    """构造 HuggingFace 下载 URL（优先使用镜像源）"""
    base = HF_MIRROR if HF_MIRROR else HF_BASE
    return f"{base}/{repo}/resolve/main/{file_path}"


def check_models_exist(
    models_dir: Path, required: Dict[str, Dict[str, str]]
) -> List[str]:
    """检查模型文件是否存在

    Args:
        models_dir: ComfyUI models 根目录
        required: 所需模型的配置字典

    Returns:
        缺失的模型相对路径列表
    """
    missing = []
    for rel_path in required:
        full_path = models_dir / rel_path
        if not full_path.exists():
            missing.append(rel_path)
    return missing


def download_model(
    url: str,
    dest_path: Path,
    desc: str = "",
    chunk_size: int = 1024 * 1024,  # 1MB chunks
    timeout: int = 30,
) -> bool:
    """下载单个模型文件，支持断点续传

    Args:
        url: 下载地址
        dest_path: 目标文件路径
        desc: 描述信息
        chunk_size: 块大小
        timeout: 连接超时

    Returns:
        是否下载成功
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    if dest_path.exists():
        logger.info(f"模型已存在，跳过: {dest_path.name}")
        return True

    temp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")

    # 断点续传
    downloaded_size = 0
    if temp_path.exists():
        downloaded_size = temp_path.stat().st_size

    headers = {"User-Agent": "xiaoshuo-video/1.0"}
    if downloaded_size > 0:
        headers["Range"] = f"bytes={downloaded_size}-"
        logger.info(f"断点续传: 已下载 {downloaded_size / 1024 / 1024:.1f} MB")

    display_name = desc or dest_path.name

    try:
        logger.info(f"开始下载: {display_name}")
        logger.info(f"  URL: {url}")
        response = requests.get(url, headers=headers, stream=True, timeout=timeout)

        if response.status_code == 416:
            # 文件已完整
            temp_path.rename(dest_path)
            logger.info(f"下载完成: {display_name}")
            return True

        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        if downloaded_size > 0:
            total_size += downloaded_size

        total_mb = total_size / 1024 / 1024 if total_size else 0
        mode = "ab" if downloaded_size > 0 else "wb"

        with open(temp_path, mode) as f:
            current = downloaded_size
            last_log_pct = -10  # 每 10% 记录一次

            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    current += len(chunk)

                    if total_size > 0:
                        pct = int(current / total_size * 100)
                        if pct >= last_log_pct + 10:
                            last_log_pct = pct
                            logger.info(
                                f"  下载进度: {pct}% "
                                f"({current / 1024 / 1024:.0f}/{total_mb:.0f} MB)"
                            )

        temp_path.rename(dest_path)
        logger.info(f"下载完成: {display_name}")
        return True

    except requests.exceptions.ConnectionError as e:
        logger.error(f"网络连接失败: {display_name} - {e}")
        logger.info("提示: 如需使用镜像源，请设置环境变量 HF_MIRROR=https://hf-mirror.com")
        return False
    except Exception as e:
        logger.error(f"下载失败: {display_name} - {e}")
        return False


def ensure_wan21_models(models_dir: Path) -> bool:
    """确保 Wan 2.1 I2V 所需模型全部就位

    检测缺失的模型并自动下载。如果全部存在则快速返回。

    Args:
        models_dir: ComfyUI models 根目录

    Returns:
        True 如果所有模型就绪, False 如果有下载失败
    """
    missing = check_models_exist(models_dir, WAN21_MODELS)

    if not missing:
        logger.info("Wan 2.1 模型文件已就绪")
        return True

    logger.info(f"检测到 {len(missing)} 个 Wan 2.1 模型缺失，开始自动下载...")
    for rel_path in missing:
        info = WAN21_MODELS[rel_path]
        logger.info(f"  缺失: {info['desc']}")

    success = 0
    for rel_path in missing:
        info = WAN21_MODELS[rel_path]
        url = _get_download_url(info["repo"], info["path"])
        dest = models_dir / rel_path

        if download_model(url, dest, desc=info["desc"]):
            success += 1

    if success == len(missing):
        logger.info(f"所有 Wan 2.1 模型下载完成 ({success}/{len(missing)})")
        return True
    else:
        logger.error(
            f"部分模型下载失败 ({success}/{len(missing)})，"
            f"视频生成可能无法正常工作。"
            f"可手动运行: python scripts/download_wan21_model.py"
        )
        return False
