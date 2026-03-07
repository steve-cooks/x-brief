"""
Configuration management for X Brief
"""

import json
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from .models import UserConfig


class XBriefConfig(BaseModel):
    """Core X Brief configuration"""
    x_api_bearer_token: str
    cache_dir: Path = Field(default_factory=lambda: Path.home() / ".x-brief" / "cache")
    db_path: Path = Field(default_factory=lambda: Path.home() / ".x-brief" / "cache.db")

    def __init__(self, **data):
        # Environment variable overrides
        if "x_api_bearer_token" not in data:
            data["x_api_bearer_token"] = os.getenv("X_BRIEF_BEARER_TOKEN", "")
        
        super().__init__(**data)
        
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)


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


def load_system_config(
    bearer_token: Optional[str] = None,
    cache_dir: Optional[Path] = None,
    db_path: Optional[Path] = None,
) -> XBriefConfig:
    """Load system configuration with optional overrides"""
    config_data = {}
    
    if bearer_token:
        config_data["x_api_bearer_token"] = bearer_token
    if cache_dir:
        config_data["cache_dir"] = cache_dir
    if db_path:
        config_data["db_path"] = db_path
    
    return XBriefConfig(**config_data)
