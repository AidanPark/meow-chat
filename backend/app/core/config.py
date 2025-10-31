"""
App configuration via environment variables.

Lightweight loader without external dependencies (avoids pydantic-settings).
Provide strongly-typed accessors and safe parsing with defaults.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional


# Helpers

def _get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.environ.get(name)
    if v is None:
        return default
    return v


def _get_bool(name: str, default: bool) -> bool:
    raw = _get_env(name)
    if raw is None:
        return bool(default)
    val = raw.strip().lower()
    if val in ("1", "true", "yes", "y", "on"):  # common truthy
        return True
    if val in ("0", "false", "no", "n", "off"):  # common falsy
        return False
    return bool(default)


def _get_int(name: str, default: int) -> int:
    raw = _get_env(name)
    if raw is None:
        return int(default)
    try:
        return int(raw.strip())
    except Exception:
        return int(default)


@dataclass(frozen=True)
class AppConfig:
    # OCR
    ocr_lang: str = "korean"
    ocr_max_concurrency: int = 2
    ocr_enable_lock: bool = True
    ocr_use_thread_pool: bool = False
    ocr_pool_size: Optional[int] = None

    # LLM
    llm_use: bool = False
    llm_max_concurrency: int = 2
    llm_enable_lock: bool = True
    llm_model: str = "gpt-4.1-mini"

    # Secrets
    openai_api_key: Optional[str] = None


@lru_cache(maxsize=1)
def load_config_from_env() -> AppConfig:
    # Secrets
    openai_api_key = _get_env("OPENAI_API_KEY")

    # OCR
    ocr_lang = _get_env("MEOW_OCR_LANG", "korean") or "korean"
    ocr_max_concurrency = _get_int("MEOW_OCR_MAX_CONCURRENCY", 2)
    ocr_enable_lock = _get_bool("MEOW_OCR_ENABLE_LOCK", True)
    ocr_use_thread_pool = _get_bool("MEOW_OCR_USE_POOL", False)
    ocr_pool_size_raw = _get_env("MEOW_OCR_POOL_SIZE")
    try:
        ocr_pool_size = int(ocr_pool_size_raw) if ocr_pool_size_raw is not None else None
    except Exception:
        ocr_pool_size = None

    # LLM
    llm_use = _get_bool("MEOW_LLM_USE", False)
    llm_max_concurrency = _get_int("MEOW_LLM_MAX_CONCURRENCY", 2)
    llm_enable_lock = _get_bool("MEOW_LLM_ENABLE_LOCK", True)
    llm_model = _get_env("MEOW_LLM_MODEL", "gpt-4.1-mini") or "gpt-4.1-mini"

    return AppConfig(
        ocr_lang=ocr_lang,
        ocr_max_concurrency=ocr_max_concurrency,
        ocr_enable_lock=ocr_enable_lock,
        ocr_use_thread_pool=ocr_use_thread_pool,
        ocr_pool_size=ocr_pool_size,
        llm_use=llm_use,
        llm_max_concurrency=llm_max_concurrency,
        llm_enable_lock=llm_enable_lock,
        llm_model=llm_model,
        openai_api_key=openai_api_key,
    )
