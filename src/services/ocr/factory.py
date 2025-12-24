"""OCR 서비스 팩토리"""

from src.settings import settings

from .base import BaseOCRService
from .dummy import DummyOCR
from .google_vision import GoogleVisionOCR


def get_ocr_service() -> BaseOCRService:
    """설정에 따라 적절한 OCR 서비스 반환

    Returns:
        BaseOCRService 인스턴스
    """
    if settings.ocr_provider == "google":
        return GoogleVisionOCR()
    elif settings.ocr_provider == "dummy":
        return DummyOCR()
    else:
        raise ValueError(f"지원하지 않는 OCR 제공자: {settings.ocr_provider}")

