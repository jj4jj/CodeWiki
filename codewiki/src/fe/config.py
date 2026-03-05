#!/usr/bin/env python3
"""
Configuration settings for the CodeWiki web application.
"""

import os
from pathlib import Path


def _read_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


class WebAppConfig:
    """Configuration class for web application settings."""
    
    # Directories
    CACHE_DIR = "./output/cache"
    TEMP_DIR = "./output/temp"
    OUTPUT_DIR = "./output"
    
    # Queue settings
    QUEUE_SIZE = 100
    DEFAULT_TASK_CONCURRENCY = 2
    MAX_TASK_CONCURRENCY = 8
    TASK_CONCURRENCY = max(
        1,
        min(MAX_TASK_CONCURRENCY, _read_int_env("CODEWIKI_TASK_CONCURRENCY", DEFAULT_TASK_CONCURRENCY)),
    )
    
    # Cache settings
    CACHE_EXPIRY_DAYS = 365
    
    # Job cleanup settings
    JOB_CLEANUP_HOURS = 24000
    RETRY_COOLDOWN_MINUTES = 3
    
    # Server settings
    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 8000
    
    # Git settings
    CLONE_TIMEOUT = 300
    CLONE_DEPTH = 1
    
    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist."""
        directories = [
            cls.CACHE_DIR,
            cls.TEMP_DIR,
            cls.OUTPUT_DIR
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

    @classmethod
    def normalize_task_concurrency(cls, value: int | None) -> int:
        """Clamp worker concurrency into supported range [1, MAX_TASK_CONCURRENCY]."""
        if value is None:
            return cls.TASK_CONCURRENCY
        return max(1, min(cls.MAX_TASK_CONCURRENCY, int(value)))
    
    @classmethod
    def get_absolute_path(cls, path: str) -> str:
        """Get absolute path for a given relative path."""
        return os.path.abspath(path)
