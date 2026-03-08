"""
Configuration management for X Brief.
"""

import json
from pathlib import Path

from .models import UserConfig


def load_user_config(path) -> UserConfig:
    """Load user configuration from JSON file"""
    path = Path(path) if isinstance(path, str) else path
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    
    with open(path, "r") as f:
        data = json.load(f)
    
    return UserConfig(**data)


def save_user_config(config: UserConfig, path: Path) -> None:
    """Save user configuration to JSON file"""
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, "w") as f:
        json.dump(config.model_dump(), f, indent=2)
