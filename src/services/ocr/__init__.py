"""OCR 서비스 패키지

다양한 OCR 엔진을 통일된 인터페이스로 제공합니다.
모든 서비스가 OCRResultEnvelope를 반환합니다.

주요 모듈:
- base: OCR 서비스 기본 인터페이스 (BaseOCRService)
- easy_ocr: EasyOCR 기반 구현체 (MyEasyOCR)
- paddle_ocr: PaddleOCR 기반 구현체 (MyPaddleOCR)
- dummy_ocr: 테스트용 더미 구현체 (DummyOCR)
- google_vision_ocr: Google Cloud Vision 구현체 (GoogleVisionOCR)
- factory: OCR 서비스 팩토리 함수
"""

from .base import BaseOCRService
from .easy_ocr import MyEasyOCR
from .paddle_ocr import MyPaddleOCR
from .factory import get_ocr_service

__all__ = [
    # 기본 인터페이스
    "BaseOCRService",
    # 서비스
    "MyEasyOCR",
    "MyPaddleOCR",
    # 팩토리
    "get_ocr_service",
]

