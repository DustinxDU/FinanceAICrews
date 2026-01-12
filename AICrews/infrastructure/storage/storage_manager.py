"""
Storage Manager - 配置存储管理

使用 JSON 文件持久化存储 LLM 配置、Crew 配置等
Production 阶段可升级为数据库存储
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

from AICrews.schemas.llm import LLMProviderConfig
from AICrews.schemas import (
    CrewConfig,
    AgentConfig,
    TaskConfig,
)
from AICrews.schemas.stats import TaskExecutionStats
from AICrews.observability.logging import get_logger

logger = get_logger(__name__)


class StorageManager:
    """JSON 文件存储管理器 - 支持用户隔离"""
    
    _instance: Optional['StorageManager'] = None
    _lock = Lock()
    
    def __new__(cls, storage_dir: Optional[str] = None) -> 'StorageManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, storage_dir: Optional[str] = None):
        if self._initialized:
            return
        
        # 默认存储目录
        storage_dir = storage_dir or os.getenv("FINANCEAI_STORAGE_DIR") or os.getenv("STORAGE_DIR")
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            project_root = Path(__file__).resolve().parents[3]
            self.storage_dir = project_root / ".data"
        
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 各类配置文件 (全局共享，用于向后兼容)
        self.llm_configs_file = self.storage_dir / "llm_configs.json"
        self.crew_configs_file = self.storage_dir / "crew_configs.json"
        self.task_stats_file = self.storage_dir / "task_stats.json"
        
        # 用户数据目录
        self.users_dir = self.storage_dir / "users"
        self.users_dir.mkdir(parents=True, exist_ok=True)
        
        # 内存缓存 (全局配置)
        self._llm_configs: Dict[str, LLMProviderConfig] = {}
        self._crew_configs: Dict[str, CrewConfig] = {}
        self._task_stats: Dict[str, TaskExecutionStats] = {}
        
        # 用户级别缓存: user_id -> {config_type -> configs}
        self._user_llm_configs: Dict[int, Dict[str, LLMProviderConfig]] = {}
        self._user_crew_configs: Dict[int, Dict[str, CrewConfig]] = {}
        
        # 加载已有数据
        self._load_all()
        
        self._initialized = True
    
    def _load_all(self) -> None:
        """加载所有配置"""
        self._load_llm_configs()
        self._load_crew_configs()
        self._load_task_stats()
    
    # ============================================
    # LLM 配置 CRUD
    # ============================================
    
    def _load_llm_configs(self) -> None:
        """加载 LLM 配置"""
        if self.llm_configs_file.exists():
            try:
                with open(self.llm_configs_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        config = LLMProviderConfig(**item)
                        self._llm_configs[config.id] = config
            except Exception as e:
                logger.warning(f"Failed to load LLM configs: {e}")
    
    def _save_llm_configs(self) -> None:
        """保存 LLM 配置"""
        data = [config.model_dump() for config in self._llm_configs.values()]
        # 序列化 datetime
        for item in data:
            for key, value in item.items():
                if isinstance(value, datetime):
                    item[key] = value.isoformat()
        with open(self.llm_configs_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def create_llm_config(self, config: LLMProviderConfig) -> LLMProviderConfig:
        """创建 LLM 配置"""
        if not config.id:
            config.id = f"llm_{config.provider}_{uuid.uuid4().hex[:8]}"
        config.created_at = datetime.now()
        config.updated_at = datetime.now()
        self._llm_configs[config.id] = config
        self._save_llm_configs()
        return config
    
    def get_llm_config(self, config_id: str) -> Optional[LLMProviderConfig]:
        """获取 LLM 配置"""
        return self._llm_configs.get(config_id)
    
    def list_llm_configs(self, provider: Optional[str] = None, user_id: Optional[int] = None) -> List[LLMProviderConfig]:
        """列出 LLM 配置 (支持用户隔离)"""
        # 合并全局配置和用户配置
        configs = list(self._llm_configs.values())
        
        # 如果指定了用户，加载用户专属配置
        if user_id is not None:
            user_configs = self._get_user_llm_configs(user_id)
            configs.extend(user_configs.values())
        
        if provider:
            configs = [c for c in configs if c.provider == provider]
        return sorted(configs, key=lambda x: x.created_at, reverse=True)
    
    def update_llm_config(self, config_id: str, updates: Dict[str, Any]) -> Optional[LLMProviderConfig]:
        """更新 LLM 配置"""
        config = self._llm_configs.get(config_id)
        if not config:
            return None
        
        for key, value in updates.items():
            if hasattr(config, key) and key not in ('id', 'created_at'):
                setattr(config, key, value)
        
        config.updated_at = datetime.now()
        self._llm_configs[config_id] = config
        self._save_llm_configs()
        return config
    
    def delete_llm_config(self, config_id: str) -> bool:
        """删除 LLM 配置"""
        if config_id in self._llm_configs:
            del self._llm_configs[config_id]
            self._save_llm_configs()
            return True
        return False
    
    # ============================================
    # Crew 配置 CRUD
    # ============================================
    
    def _load_crew_configs(self) -> None:
        """加载 Crew 配置"""
        if self.crew_configs_file.exists():
            try:
                with open(self.crew_configs_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        config = CrewConfig(**item)
                        self._crew_configs[config.id] = config
            except Exception as e:
                logger.warning(f"Failed to load Crew configs: {e}")
    
    def _save_crew_configs(self) -> None:
        """保存 Crew 配置"""
        data = [config.model_dump() for config in self._crew_configs.values()]
        for item in data:
            for key, value in item.items():
                if isinstance(value, datetime):
                    item[key] = value.isoformat()
        with open(self.crew_configs_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def create_crew_config(self, config: CrewConfig) -> CrewConfig:
        """创建 Crew 配置"""
        if not config.id:
            config.id = f"crew_{uuid.uuid4().hex[:8]}"
        config.created_at = datetime.now()
        config.updated_at = datetime.now()
        self._crew_configs[config.id] = config
        self._save_crew_configs()
        return config
    
    def get_crew_config(self, config_id: str) -> Optional[CrewConfig]:
        """获取 Crew 配置"""
        return self._crew_configs.get(config_id)
    
    def list_crew_configs(self, is_template: Optional[bool] = None, user_id: Optional[int] = None) -> List[CrewConfig]:
        """列出 Crew 配置 (支持用户隔离)"""
        # 合并全局配置和用户配置
        configs = list(self._crew_configs.values())
        
        # 如果指定了用户，加载用户专属配置
        if user_id is not None:
            user_configs = self._get_user_crew_configs(user_id)
            configs.extend(user_configs.values())
        
        if is_template is not None:
            configs = [c for c in configs if c.is_template == is_template]
        return sorted(configs, key=lambda x: x.created_at, reverse=True)
    
    def update_crew_config(self, config_id: str, updates: Dict[str, Any]) -> Optional[CrewConfig]:
        """更新 Crew 配置"""
        config = self._crew_configs.get(config_id)
        if not config:
            return None
        
        for key, value in updates.items():
            if hasattr(config, key) and key not in ('id', 'created_at'):
                setattr(config, key, value)
        
        config.updated_at = datetime.now()
        self._crew_configs[config_id] = config
        self._save_crew_configs()
        return config
    
    def delete_crew_config(self, config_id: str) -> bool:
        """删除 Crew 配置"""
        if config_id in self._crew_configs:
            del self._crew_configs[config_id]
            self._save_crew_configs()
            return True
        return False
    
    # ============================================
    # 任务执行统计
    # ============================================
    
    def _load_task_stats(self) -> None:
        """加载任务统计"""
        if self.task_stats_file.exists():
            try:
                with open(self.task_stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data[-100:]:  # 只保留最近100条
                        stats = TaskExecutionStats(**item)
                        self._task_stats[stats.job_id] = stats
            except Exception as e:
                logger.warning(f"Failed to load task stats: {e}")
    
    def _save_task_stats(self) -> None:
        """保存任务统计"""
        data = [stats.model_dump() for stats in list(self._task_stats.values())[-100:]]
        for item in data:
            self._serialize_datetime_recursive(item)
        with open(self.task_stats_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _serialize_datetime_recursive(self, obj: Any) -> None:
        """递归序列化 datetime"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, datetime):
                    obj[key] = value.isoformat()
                elif isinstance(value, (dict, list)):
                    self._serialize_datetime_recursive(value)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, datetime):
                    obj[i] = item.isoformat()
                elif isinstance(item, (dict, list)):
                    self._serialize_datetime_recursive(item)
    
    def create_task_stats(self, stats: TaskExecutionStats) -> TaskExecutionStats:
        """创建任务统计"""
        self._task_stats[stats.job_id] = stats
        self._save_task_stats()
        return stats
    
    def get_task_stats(self, job_id: str) -> Optional[TaskExecutionStats]:
        """获取任务统计"""
        return self._task_stats.get(job_id)
    
    def update_task_stats(self, job_id: str, updates: Dict[str, Any]) -> Optional[TaskExecutionStats]:
        """更新任务统计"""
        stats = self._task_stats.get(job_id)
        if not stats:
            return None
        
        for key, value in updates.items():
            if hasattr(stats, key):
                setattr(stats, key, value)
        
        self._task_stats[job_id] = stats
        self._save_task_stats()
        return stats
    
    def list_task_stats(self, limit: int = 50) -> List[TaskExecutionStats]:
        """列出任务统计"""
        stats = list(self._task_stats.values())
        stats.sort(key=lambda x: x.started_at or datetime.min, reverse=True)
        return stats[:limit]


    # ============================================
    # 用户级别配置管理
    # ============================================
    
    def _get_user_storage_dir(self, user_id: int) -> Path:
        """获取用户专属存储目录"""
        user_dir = self.users_dir / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir
    
    def _get_user_llm_configs(self, user_id: int) -> Dict[str, LLMProviderConfig]:
        """获取用户专属 LLM 配置"""
        if user_id in self._user_llm_configs:
            return self._user_llm_configs[user_id]
        
        # 从文件加载
        user_dir = self._get_user_storage_dir(user_id)
        config_file = user_dir / "llm_configs.json"
        
        configs = {}
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        config = LLMProviderConfig(**item)
                        configs[config.id] = config
            except Exception as e:
                logger.warning(f"Failed to load user {user_id} LLM configs: {e}")
        
        self._user_llm_configs[user_id] = configs
        return configs
    
    def _save_user_llm_configs(self, user_id: int) -> None:
        """保存用户专属 LLM 配置"""
        configs = self._user_llm_configs.get(user_id, {})
        user_dir = self._get_user_storage_dir(user_id)
        config_file = user_dir / "llm_configs.json"
        
        data = [config.model_dump() for config in configs.values()]
        for item in data:
            for key, value in item.items():
                if isinstance(value, datetime):
                    item[key] = value.isoformat()
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def create_user_llm_config(self, user_id: int, config: LLMProviderConfig) -> LLMProviderConfig:
        """创建用户专属 LLM 配置"""
        if not config.id:
            config.id = f"llm_{config.provider}_{uuid.uuid4().hex[:8]}"
        config.created_at = datetime.now()
        config.updated_at = datetime.now()
        
        user_configs = self._get_user_llm_configs(user_id)
        user_configs[config.id] = config
        self._user_llm_configs[user_id] = user_configs
        self._save_user_llm_configs(user_id)
        return config
    
    def delete_user_llm_config(self, user_id: int, config_id: str) -> bool:
        """删除用户专属 LLM 配置"""
        user_configs = self._get_user_llm_configs(user_id)
        if config_id in user_configs:
            del user_configs[config_id]
            self._save_user_llm_configs(user_id)
            return True
        return False
    
    def _get_user_crew_configs(self, user_id: int) -> Dict[str, CrewConfig]:
        """获取用户专属 Crew 配置"""
        if user_id in self._user_crew_configs:
            return self._user_crew_configs[user_id]
        
        # 从文件加载
        user_dir = self._get_user_storage_dir(user_id)
        config_file = user_dir / "crew_configs.json"
        
        configs = {}
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        config = CrewConfig(**item)
                        configs[config.id] = config
            except Exception as e:
                logger.warning(f"Failed to load user {user_id} Crew configs: {e}")
        
        self._user_crew_configs[user_id] = configs
        return configs
    
    def _save_user_crew_configs(self, user_id: int) -> None:
        """保存用户专属 Crew 配置"""
        configs = self._user_crew_configs.get(user_id, {})
        user_dir = self._get_user_storage_dir(user_id)
        config_file = user_dir / "crew_configs.json"
        
        data = [config.model_dump() for config in configs.values()]
        for item in data:
            self._serialize_datetime_recursive(item)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def create_user_crew_config(self, user_id: int, config: CrewConfig) -> CrewConfig:
        """创建用户专属 Crew 配置"""
        if not config.id:
            config.id = f"crew_{uuid.uuid4().hex[:8]}"
        config.created_at = datetime.now()
        config.updated_at = datetime.now()
        
        user_configs = self._get_user_crew_configs(user_id)
        user_configs[config.id] = config
        self._user_crew_configs[user_id] = user_configs
        self._save_user_crew_configs(user_id)
        return config
    
    def delete_user_crew_config(self, user_id: int, config_id: str) -> bool:
        """删除用户专属 Crew 配置"""
        user_configs = self._get_user_crew_configs(user_id)
        if config_id in user_configs:
            del user_configs[config_id]
            self._save_user_crew_configs(user_id)
            return True
        return False
    
    def get_user_env_config(self, user_id: int) -> Dict[str, str]:
        """获取用户环境变量配置"""
        user_dir = self._get_user_storage_dir(user_id)
        env_file = user_dir / "env_config.json"
        
        if env_file.exists():
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def save_user_env_config(self, user_id: int, env_config: Dict[str, str]) -> None:
        """保存用户环境变量配置"""
        user_dir = self._get_user_storage_dir(user_id)
        env_file = user_dir / "env_config.json"
        
        with open(env_file, 'w', encoding='utf-8') as f:
            json.dump(env_config, f, ensure_ascii=False, indent=2)


# 全局实例
_storage: Optional[StorageManager] = None


def get_storage() -> StorageManager:
    """获取存储管理器实例"""
    global _storage
    if _storage is None:
        _storage = StorageManager()
    return _storage
