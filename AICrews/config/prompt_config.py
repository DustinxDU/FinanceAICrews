import os
import yaml
from AICrews.observability.logging import get_logger
from typing import Dict, Any, Optional
from functools import lru_cache

logger = get_logger(__name__)

class PromptConfigLoader:
    """加载和管理提示词及业务参数配置"""
    
    def __init__(self, config_dir: str = "config/prompts"):
        self.config_dir = config_dir
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get_config(self, name: str) -> Dict[str, Any]:
        """获取指定名称的配置 (如 'copilot', 'quick_scan')"""
        if name in self._cache:
            return self._cache[name]
        
        file_path = os.path.join(self.config_dir, f"{name}.yaml")
        if not os.path.exists(file_path):
            logger.error(f"Config file not found: {file_path}")
            return {}
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                self._cache[name] = config
                return config
        except Exception as e:
            logger.error(f"Error loading config {name}: {e}")
            return {}

    def reload(self):
        """清除缓存以重新加载配置"""
        self._cache.clear()

# 全局单例
_loader = None

def get_prompt_config_loader() -> PromptConfigLoader:
    global _loader
    if _loader is None:
        # 获取项目根目录
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        config_dir = os.path.join(project_root, "config/prompts")
        _loader = PromptConfigLoader(config_dir)
    return _loader
