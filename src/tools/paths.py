"""Helpers for runtime directories and files used by the application."""

from __future__ import annotations

from pathlib import Path

from src.config import settings


def get_project_root() -> Path:
    return settings.PROJECT_ROOT


def get_data_dir() -> Path:
    return get_project_root() / settings.DATA_DIR_NAME


def get_log_dir() -> Path:
    return get_data_dir() / settings.LOG_DIR_NAME


def get_config_dir() -> Path:
    return get_data_dir() / settings.CONFIG_DIR_NAME


def get_recordings_dir() -> Path:
    return get_data_dir() / settings.RECORDINGS_DIR_NAME


def get_log_file_path(filename: str | None = None) -> Path:
    return get_log_dir() / (filename or settings.DEFAULT_LOG_FILE_NAME)


def ensure_runtime_directories() -> dict[str, Path]:
    directories = {
        "data": get_data_dir(),
        "logs": get_log_dir(),
        "config": get_config_dir(),
        "recordings": get_recordings_dir(),
    }
    for path in directories.values():
        path.mkdir(parents=True, exist_ok=True)
    return directories

