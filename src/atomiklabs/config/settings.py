import os
import tomli
from pathlib import Path
from functools import lru_cache
from typing import Dict, Any, Optional

from .models import AppConfig

CONFIG_PATHS = [
    "/etc/arxiv-fetcher/config.toml",
    "~/.config/arxiv-fetcher/config.toml",
    "config.toml",
]

ENV_PREFIX = "ARXIV_FETCHER_"

@lru_cache()
def get_config() -> AppConfig:
    """
    Load and validate configuration from files and environment variables.
    Implements configuration layering with clear precedence rules.
    """
    config_dict: Dict[str, Any] = {}
    
    for config_path in CONFIG_PATHS:
        path = Path(os.path.expanduser(config_path))
        if path.is_file():
            with open(path, "rb") as f:
                file_config = tomli.load(f)
                config_dict.update(file_config)
    
    env_config = _load_from_env()
    _deep_update(config_dict, env_config)
    
    return AppConfig(**config_dict)

def _load_from_env() -> Dict[str, Any]:
    """Load configuration from environment variables."""
    result: Dict[str, Any] = {}
    
    for key, value in os.environ.items():
        if key.startswith(ENV_PREFIX):
            config_key = key[len(ENV_PREFIX):].lower()
            parts = config_key.split("__")
            
            current = result
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
                
            current[parts[-1]] = _convert_env_value(value)
    
    return result

def _convert_env_value(value: str) -> Any:
    """Convert environment variable string to appropriate type."""
    if value.lower() in ("true", "yes", "1", "on"):
        return True
    if value.lower() in ("false", "no", "0", "off"):
        return False
    
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass
    
    if "," in value:
        return [item.strip() for item in value.split(",")]
    
    return value

def _deep_update(target: Dict[str, Any], source: Dict[str, Any]) -> None:
    """Recursively update a nested dictionary."""
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            _deep_update(target[key], value)
        else:
            target[key] = value
