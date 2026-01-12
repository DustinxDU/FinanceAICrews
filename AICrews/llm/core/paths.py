"""路径工具模块

提供 repo_root 和 config_root 的定位，不依赖 os.getcwd()。
"""

import os
from pathlib import Path
from typing import Optional

# 缓存已解析的路径
_repo_root: Optional[Path] = None
_config_root: Optional[Path] = None


def get_repo_root() -> Path:
    """获取项目根目录。
    
    Returns:
        Path: 项目根目录路径
        
    Raises:
        RuntimeError: 无法确定项目根目录
    """
    global _repo_root
    
    if _repo_root is not None:
        return _repo_root
    
    # 尝试多种方式定位项目根目录
    candidates = [
        # 方式1: 当前文件向上查找 (AICrews/llm/core/paths.py)
        Path(__file__).parent.parent.parent.parent,
        # 方式2: 相对于 PYTHONPATH
        Path.cwd(),
        # 方式3: 尝试查找包含 pyproject.toml 或 setup.py 的目录
        Path(__file__).parent.parent.parent,
    ]
    
    for candidate in candidates:
        if _is_repo_root(candidate):
            _repo_root = candidate
            return _repo_root
    
    # 如果都找不到，使用 cwd 并标记
    _repo_root = Path.cwd()
    return _repo_root


def _is_repo_root(path: Path) -> bool:
    """检查路径是否为项目根目录。
    
    Args:
        path: 要检查的路径
        
    Returns:
        bool: 是否为项目根目录
    """
    if not path.exists() or not path.is_dir():
        return False
    
    # 检查关键文件/目录
    markers = [
        path / "pyproject.toml",
        path / "setup.py",
        path / "AICrews",
        path / "config",
    ]
    
    return any(marker.exists() for marker in markers)


def get_config_root() -> Path:
    """获取配置目录根路径。
    
    Returns:
        Path: 配置目录路径 (repo_root / "config")
    """
    global _config_root
    
    if _config_root is not None:
        return _config_root
    
    _config_root = get_repo_root() / "config"
    return _config_root


def get_llm_config_dir() -> Path:
    """获取 LLM 配置目录。
    
    Returns:
        Path: LLM 配置目录路径 (config_root / "llm")
    """
    return get_config_root() / "llm"



def get_providers_path() -> Path:
    """获取 providers.yaml 路径。
    
    Returns:
        Path: providers.yaml 文件路径
    """
    return get_llm_config_dir() / "providers.yaml"


def get_pricing_path() -> Path:
    """获取 pricing.yaml 路径。
    
    Returns:
        Path: pricing.yaml 文件路径
    """
    return get_llm_config_dir() / "pricing.yaml"


def get_model_tags_path() -> Path:
    """获取 model_tags.yaml 路径。
    
    Returns:
        Path: model_tags.yaml 文件路径
    """
    return get_llm_config_dir() / "model_tags.yaml"


def clear_path_cache() -> None:
    """清除路径缓存（主要用于测试）。"""
    global _repo_root, _config_root
    _repo_root = None
    _config_root = None
