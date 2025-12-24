"""OCR 서비스 기본 인터페이스"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from PIL import Image


@dataclass
class OCRResult:
    """OCR 결과 데이터 클래스"""

    text: str
    confidence: float | None = None
    metadata: dict | None = None

    def __str__(self) -> str:
        return self.text


class BaseOCRService(ABC):
    """OCR 서비스 기본 추상 클래스"""

    @abstractmethod
    def extract_text(self, image: Image.Image) -> OCRResult:
        """이미지에서 텍스트 추출

        Args:
            image: PIL Image 객체

        Returns:
            OCRResult 객체
        """
        pass

    def extract_text_from_images(self, images: list[Image.Image]) -> list[OCRResult]:
        """여러 이미지에서 텍스트 추출 (다중 페이지 지원)

        Args:
            images: PIL Image 객체 리스트

        Returns:
            OCRResult 객체 리스트
        """
        return [self.extract_text(img) for img in images]

