"""
프로젝트 환경설정 관리 모듈

주요 역할:
- 환경변수 기반으로 OCR, LLM, API 키 등 주요 설정을 안전하게 불러와서 AppConfig 객체로 제공합니다.
- 외부 라이브러리 없이, 파이썬 표준 라이브러리만으로 타입 안전하게 파싱 및 기본값 적용을 구현합니다.
- @dataclass로 각 설정의 타입을 명확히 지정하고, @lru_cache로 1회만 읽어와 재사용합니다.

주요 기능:
- 환경변수에서 값을 읽어와 OCR/LLM/OpenAI API 키 등 다양한 옵션을 자동 파싱합니다.
- 불리언/정수/문자열 등 다양한 타입을 안전하게 변환하며, 값이 없거나 잘못된 경우에는 기본값을 사용합니다.
- 여러 서비스/모듈에서 load_config_from_env()를 통해 설정을 쉽게 불러올 수 있습니다.
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
    # 모델 우선순위: MEOW_LLM_MODEL → OPENAI_DEFAULT_MODEL → 하드코딩 폴백
    llm_model = _get_env("MEOW_LLM_MODEL", _get_env("OPENAI_DEFAULT_MODEL", "gpt-4.1-mini")) or (_get_env("OPENAI_DEFAULT_MODEL", "gpt-4.1-mini") or "gpt-4.1-mini")

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
