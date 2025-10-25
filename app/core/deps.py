"""
FastAPI dependency providers for configuration and core services.

- get_config(): AppConfig loaded from environment, cached
- get_ocr_service(): Singleton PaddleOCRService configured from env
- get_extractor(): Factory for LabTableExtractor with env-based settings
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from app.core.config import AppConfig, load_config_from_env
from app.services.ocr.paddle_ocr import PaddleOCRService
from app.services.analysis.lab_table_extractor import LabTableExtractor, Settings as ExtractorSettings


# Config provider
@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    return load_config_from_env()


# OCR service provider (singleton)
@lru_cache(maxsize=1)
def get_ocr_service() -> PaddleOCRService:
    cfg = get_config()
    svc = PaddleOCRService(
        lang=cfg.ocr_lang,
        enable_ocr_lock=cfg.ocr_enable_lock,
        ocr_max_concurrency=cfg.ocr_max_concurrency,
        ocr_use_thread_pool=cfg.ocr_use_thread_pool,
        ocr_pool_size=cfg.ocr_pool_size,
    )
    return svc


# Extractor provider (factory: allow different settings per request if needed)
def get_extractor() -> LabTableExtractor:
    cfg = get_config()
    # Map env-driven settings into the extractor's Settings dataclass
    s = ExtractorSettings(
        use_llm=cfg.llm_use,
        # Concurrency knobs
        enable_llm_lock=cfg.llm_enable_lock,
        llm_max_concurrency=cfg.llm_max_concurrency,
    )
    extractor = LabTableExtractor(
        settings=s,
        api_key=cfg.openai_api_key,
        llm_model=cfg.llm_model,
    )
    return extractor
