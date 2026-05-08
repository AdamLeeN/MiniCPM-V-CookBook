"""
配置管理器 - 加载/保存用户配置
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


DEFAULT_CONFIG = {
    "ports": {
        "livekit": 7880,
        "backend": 8021,
        "frontend": 8088,
        "cpp_server": 9060,
    },
    "model": {
        "dir": "~/models/openbmb/MiniCPM-o-4_5-gguf",
        "quant": "Q4_K_M",
    },
    "cpp_mode": "simplex",  # simplex or duplex
    "frontend_mode": "prod",  # prod or dev
    "wsl": {
        "distro": "Ubuntu",
        "install_path": "/home/user/.minicpmo",
        "user": "user",
    },
    "livekit": {
        "api_key": "devkey",
        "api_secret": "secretsecretsecretsecretsecretsecret",
    },
    "auto_start": False,
    "first_run": True,
}


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            config_path = os.path.join(base_dir, 'user_data', 'config.yaml')
        
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config = self._load()
    
    def _load(self) -> Dict[str, Any]:
        """从文件加载配置"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded = yaml.safe_load(f) or {}
                # 合并默认配置（处理新增字段）
                return self._merge_dict(DEFAULT_CONFIG.copy(), loaded)
            except Exception as e:
                print(f"[Config] 加载配置失败: {e}, 使用默认配置")
                return DEFAULT_CONFIG.copy()
        return DEFAULT_CONFIG.copy()
    
    def save(self):
        """保存配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, allow_unicode=True, default_flow_style=False)
        except Exception as e:
            print(f"[Config] 保存配置失败: {e}")
    
    def get(self, key: str, default=None):
        """获取配置项，支持点号分隔的路径如 'ports.backend'"""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key: str, value: Any):
        """设置配置项，支持点号分隔的路径"""
        keys = key.split('.')
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self.save()
    
    @property
    def config(self) -> Dict[str, Any]:
        """获取完整配置字典"""
        return self._config
    
    @staticmethod
    def _merge_dict(base: Dict, override: Dict) -> Dict:
        """深度合并字典"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigManager._merge_dict(result[key], value)
            else:
                result[key] = value
        return result
