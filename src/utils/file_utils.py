"""文件操作工具"""
import json
from pathlib import Path
from typing import Any, Dict, Union
import yaml


def ensure_dir(path: Union[str, Path]) -> Path:
    """确保目录存在"""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_json(path: Union[str, Path]) -> Dict[str, Any]:
    """加载JSON文件"""
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Union[str, Path], data: Any, indent: int = 2) -> None:
    """保存JSON文件"""
    path = Path(path)
    ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def load_yaml(path: Union[str, Path]) -> Dict[str, Any]:
    """加载YAML文件"""
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml(path: Union[str, Path], data: Any) -> None:
    """保存YAML文件"""
    path = Path(path)
    ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)


def read_text(path: Union[str, Path], encoding: str = "utf-8") -> str:
    """读取文本文件"""
    path = Path(path)
    return path.read_text(encoding=encoding)


def write_text(path: Union[str, Path], content: str, encoding: str = "utf-8") -> None:
    """写入文本文件"""
    path = Path(path)
    ensure_dir(path.parent)
    path.write_text(content, encoding=encoding)
