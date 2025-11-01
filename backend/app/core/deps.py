"""
프로젝트 핵심 서비스/설정 DI(Dependency Injection) 공급자 모듈

주요 역할:
- OCR, 이미지/라인 전처리, 추출기, 파이프라인 매니저 등 주요 컴포넌트의 인스턴스를 중앙에서 관리/제공합니다.
- 환경설정(AppConfig)을 기반으로 각 서비스의 옵션을 자동으로 반영합니다.
- 대부분의 서비스는 @lru_cache로 싱글톤(프로세스 내 1회 생성)으로 관리되어 성능과 일관성을 보장합니다.
- 추출기/파이프라인 매니저 등은 요청마다 새 인스턴스를 생성할 수 있도록 팩토리 함수로 제공합니다.
- clear_cached_providers() 함수로, 캐시된 싱글톤 인스턴스를 모두 초기화하여 환경변수 변경에도 즉시 반영할 수 있습니다.

주요 기능:
- get_config(): 환경변수 기반 앱 설정(AppConfig) 싱글톤 제공
- get_image_preprocessor(): 이미지 전처리기 싱글톤 제공
- get_ocr_service(): PaddleOCR 서비스 싱글톤 제공
- get_line_preprocessor(): 라인 전처리기 싱글톤 제공
- get_extractor(): LabTableExtractor 추출기 팩토리(설정 반영)
- get_pipeline_manager(): OCRPipelineManager 팩토리(중앙 DI로 연결)
- clear_cached_providers(): 모든 싱글톤 캐시 초기화(환경변수 변경 반영)
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

import app.compat  # noqa: F401  # 호환성 패치(예: langchain.docstore alias) 적용

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
    """
    환경변수 기반 앱 설정(AppConfig) 싱글톤 반환
    """
    return load_config_from_env()

# Image preprocessor provider (singleton)
@lru_cache(maxsize=1)
def get_image_preprocessor() -> ImagePreprocessor:
    """
    이미지 전처리기 싱글톤 반환 (기본 설정 적용)
    """
    _cfg = get_config()  # 향후 환경변수 기반 설정 확장 가능
    settings = ImageSettings(
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
    """
    환경설정 기반 PaddleOCR 서비스 싱글톤 반환
    """
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
    """
    라인 전처리기 싱글톤 반환 (기본 설정 적용)
    """
    _cfg = get_config()  # 향후 환경변수 기반 설정 확장 가능
    settings = LineSettings(order="x_left", alpha=0.7, debug=True)
    return LinePreprocessor(settings=settings)

# Extractor provider (factory: allow different settings per request if needed)
def get_extractor() -> LabTableExtractor:
    """
    환경설정 기반 LabTableExtractor 추출기 인스턴스 반환 (팩토리)
    """
    cfg = get_config()
    s = ExtractorSettings(
        use_llm=cfg.llm_use,
        enable_llm_lock=cfg.llm_enable_lock,
        llm_max_concurrency=cfg.llm_max_concurrency,
    )
    extractor = LabTableExtractor(
        settings=s,
        lexicon=get_code_lexicon(),
        resolver=resolve_code,
        api_key=cfg.openai_api_key,
        llm_model=cfg.llm_model,
    )
    return extractor

# OCR pipeline manager provider (factory)
def get_pipeline_manager(*, do_preprocess_default: bool = True, progress_cb=None) -> OCRPipelineManager:
    """
    OCRPipelineManager 인스턴스 반환 (DI로 각 컴포넌트 연결, progress 콜백 등 옵션 지원)
    - 싱글톤 기반 컴포넌트와 새 추출기를 조합해 반환
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
    """
    모든 싱글톤 캐시를 초기화하여 환경변수 변경을 즉시 반영 (노트북/스크립트에서 유용)
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
