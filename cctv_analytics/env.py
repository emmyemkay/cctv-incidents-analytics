from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv is a development convenience
    load_dotenv = None

if load_dotenv and os.getenv("LOAD_DOTENV", "1").strip().lower() in {"1", "true", "yes", "on"}:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


class EnvironmentConfigurationError(RuntimeError):
    """Raised when required deployment configuration is missing or invalid."""


def env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise EnvironmentConfigurationError(f"{name} must be an integer") from exc


def env_list(name: str, default: Iterable[str] = ()) -> list[str]:
    raw = os.getenv(name)
    if raw is None:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise EnvironmentConfigurationError(f"Required environment variable {name} is not set")
    return value.strip()


def sqlite_path(base_dir: Path) -> Path:
    configured = env("SQLITE_PATH")
    return Path(configured) if configured else base_dir / "db.sqlite3"
