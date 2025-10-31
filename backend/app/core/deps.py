"""
FastAPI dependency providers for configuration and core services.

- get_config(): AppConfig loaded from environment, cached
- get_ocr_service(): Singleton PaddleOCRService configured from env
- get_extractor(): Factory for LabTableExtractor with env-based settings
- get_image_preprocessor(): Singleton ImagePreprocessor with sane defaults
- get_line_preprocessor(): Singleton LinePreprocessor with sane defaults
- get_pipeline_manager(): Factory for OCRPipelineManager wired with DI
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from app.core.config import AppConfig, load_config_from_env
from app.services.ocr.paddle_ocr_service import PaddleOCRService
from app.services.analysis.lab_table_extractor import LabTableExtractor, Settings as ExtractorSettings
from app.services.analysis.reference.code_lexicon import get_code_lexicon, resolve_code
from app.services.analysis.image_preprocessor import ImagePreprocessor, Settings as ImageSettings
from app.services.analysis.line_preprocessor import LinePreprocessor, Settings as LineSettings
from app.services.analysis.ocr_pipeline_manager import OCRPipelineManager


# Config provider
@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    return load_config_from_env()

# Image preprocessor provider (singleton)
@lru_cache(maxsize=1)
def get_image_preprocessor() -> ImagePreprocessor:
    _cfg = get_config()  # reserved for future env-driven mapping
    settings = ImageSettings(
        # long_edge_min=1920,
        long_edge_min=0,
        enable_flatten_transparency=True,
        enable_normalize_mode=True,
        enable_deskew=True,
        enable_table_enhance=False,
        debug=False,
    )
    return ImagePreprocessor(settings=settings)

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

# Line preprocessor provider (singleton)
@lru_cache(maxsize=1)
def get_line_preprocessor() -> LinePreprocessor:
    _cfg = get_config()  # reserved for future env-driven mapping
    settings = LineSettings(order="x_left", alpha=0.7, debug=True)
    return LinePreprocessor(settings=settings)

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
        # Provide default lexicon/resolver; callers can override per-call if needed
        lexicon=get_code_lexicon(),
        resolver=resolve_code,
        api_key=cfg.openai_api_key,
        llm_model=cfg.llm_model,
    )
    return extractor

# OCR pipeline manager provider (factory)
def get_pipeline_manager(*, do_preprocess_default: bool = True, progress_cb=None) -> OCRPipelineManager:
    """Create an OCRPipelineManager wired up with centralized DI providers.

    Notes:
    - Factory (not cached): caller may want different progress callbacks.
    - Uses singleton preprocessor/ocr/line_preproc and fresh extractor per call.
    """
    return OCRPipelineManager(
        preprocessor=get_image_preprocessor(),
        ocr_service=get_ocr_service(),
        line_preproc=get_line_preprocessor(),
        extractor=get_extractor(),
        do_preprocess_default=do_preprocess_default,
        progress_cb=progress_cb,
    )

def clear_cached_providers() -> None:
    """Clear lru_cache for cached providers to reflect environment changes.

    Useful in notebooks or scripts that modify os.environ without restarting the process.
    """
    try:
        get_config.cache_clear()
    except Exception:
        pass
    try:
        get_ocr_service.cache_clear()
    except Exception:
        pass
    try:
        get_image_preprocessor.cache_clear()
    except Exception:
        pass
    try:
        get_line_preprocessor.cache_clear()
    except Exception:
        pass
