from __future__ import annotations

import os
from dataclasses import dataclass

from .errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class Settings:
    semantic_scholar_api_key: str | None
    http_timeout_seconds: float = 20.0
    http_max_retries: int = 3
    http_backoff_seconds: float = 0.5
    http_max_backoff_seconds: float = 8.0
    http_jitter_fraction: float = 0.1


def _read_float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a number.") from exc
    if parsed <= 0:
        raise ConfigurationError(f"{name} must be greater than 0.")
    return parsed


def _read_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer.") from exc
    if parsed < 0:
        raise ConfigurationError(f"{name} must be greater than or equal to 0.")
    return parsed


def _read_non_negative_float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a number.") from exc
    if parsed < 0:
        raise ConfigurationError(f"{name} must be greater than or equal to 0.")
    return parsed


def load_settings() -> Settings:
    return Settings(
        semantic_scholar_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY"),
        http_timeout_seconds=_read_float_env("PAPER_FINDER_HTTP_TIMEOUT", 20.0),
        http_max_retries=_read_int_env("PAPER_FINDER_HTTP_MAX_RETRIES", 3),
        http_backoff_seconds=_read_float_env("PAPER_FINDER_HTTP_BACKOFF", 0.5),
        http_max_backoff_seconds=_read_float_env("PAPER_FINDER_HTTP_MAX_BACKOFF", 8.0),
        http_jitter_fraction=_read_non_negative_float_env("PAPER_FINDER_HTTP_JITTER", 0.1),
    )
