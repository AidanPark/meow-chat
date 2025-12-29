"""OCR 서비스 기본 인터페이스

모든 OCR 서비스(DummyOCR, GoogleVisionOCR, MyEasyOCR, MyPaddleOCR)가 상속하는 기본 인터페이스.
통일된 OCRResultEnvelope 반환 타입 사용.

다양한 입력 타입 지원:
- PIL Image (extract_text)
- 파일 경로 (run_ocr_from_path)
- numpy array (run_ocr_from_nparray)
- bytes (run_ocr_from_bytes)
- 통합 메서드 (run_ocr)
"""
from __future__ import annotations

import io
import logging
from abc import ABC, abstractmethod
from typing import List, Literal, Optional, Union

import numpy as np
from PIL import Image

from src.models.envelopes import OCRData, OCRItem, OCRMeta, OCRResultEnvelope

logger = logging.getLogger(__name__)


class BaseOCRService(ABC):
    """OCR 서비스 기본 추상 클래스

    모든 OCR 서비스가 상속하는 통일된 인터페이스.

    필수 구현:
        - extract_text(Image.Image): 핵심 추상 메서드

    기본 구현 제공 (오버라이드 가능):
        - run_ocr_from_path(str): 파일 경로에서 OCR
        - run_ocr_from_nparray(np.ndarray): numpy 배열에서 OCR
        - run_ocr_from_bytes(bytes): 바이트 데이터에서 OCR
        - run_ocr(Union[...]): 입력 타입 자동 감지 통합 메서드

    성능이 중요한 구현체(PaddleOCR, EasyOCR)는 기본 구현을 오버라이드하여
    중간 변환 없이 직접 처리할 수 있습니다.
    """

    @abstractmethod
    def extract_text(self, image: Image.Image) -> OCRResultEnvelope:
        """이미지에서 텍스트 추출 (핵심 추상 메서드)

        Args:
            image: PIL Image 객체

        Returns:
            OCRResultEnvelope 객체
        """
        pass

    def run_ocr_from_bytes(self, image_bytes: bytes) -> Optional[OCRResultEnvelope]:
        """바이트 데이터에서 OCR 실행

        기본 구현: PIL Image로 변환 후 extract_text 호출.
        성능이 중요한 구현체에서는 오버라이드하여 직접 처리 가능.

        Args:
            image_bytes: 이미지 바이트 데이터

        Returns:
            OCRResultEnvelope 또는 None (실패 시)
        """
        try:
            image = Image.open(io.BytesIO(image_bytes))
            return self.extract_text(image)
        except Exception as e:
            logger.error(f"바이트 OCR 실패: {e}")
            return None

    def run_ocr_from_path(self, file_path: str) -> Optional[OCRResultEnvelope]:
        """파일 경로에서 OCR 실행

        기본 구현: PIL Image로 열어서 extract_text 호출.
        성능이 중요한 구현체에서는 오버라이드하여 직접 처리 가능.

        Args:
            file_path: 이미지 파일 경로

        Returns:
            OCRResultEnvelope 또는 None (실패 시)
        """
        try:
            image = Image.open(file_path)
            return self.extract_text(image)
        except Exception as e:
            logger.error(f"파일 OCR 실패: {e}")
            return None

    def run_ocr_from_nparray(
        self, image_array: np.ndarray
    ) -> Optional[OCRResultEnvelope]:
        """numpy 배열에서 OCR 실행

        기본 구현: PIL Image로 변환 후 extract_text 호출.
        성능이 중요한 구현체에서는 오버라이드하여 직접 처리 가능.

        Args:
            image_array: 이미지 numpy 배열 (RGB 또는 BGR)

        Returns:
            OCRResultEnvelope 또는 None (실패 시)
        """
        try:
            image = Image.fromarray(image_array)
            return self.extract_text(image)
        except Exception as e:
            logger.error(f"배열 OCR 실패: {e}")
            return None

    def run_ocr(
        self, image: Union[str, np.ndarray, Image.Image, bytes]
    ) -> Optional[OCRResultEnvelope]:
        """통합 OCR 실행 메서드

        입력 타입을 자동 감지하여 적절한 메서드 호출.

        Args:
            image: 이미지 (파일 경로, numpy array, PIL Image, bytes)

        Returns:
            OCRResultEnvelope 또는 None (실패 시)
        """
        if isinstance(image, str):
            return self.run_ocr_from_path(image)
        elif isinstance(image, bytes):
            return self.run_ocr_from_bytes(image)
        elif isinstance(image, Image.Image):
            return self.extract_text(image)
        elif isinstance(image, np.ndarray):
            return self.run_ocr_from_nparray(image)
        else:
            logger.error(f"지원하지 않는 이미지 타입: {type(image)}")
            return None

    def extract_text_from_images(
        self, images: List[Image.Image]
    ) -> List[OCRResultEnvelope]:
        """여러 이미지에서 텍스트 추출 (다중 페이지 지원)

        Args:
            images: PIL Image 객체 리스트

        Returns:
            OCRResultEnvelope 객체 리스트
        """
        return [self.extract_text(img) for img in images]

    def _create_empty_envelope(
        self,
        source: Literal["bytes", "nparray", "path"] = "nparray",
        lang: str = "unknown",
        engine: str = "BaseOCR",
    ) -> OCRResultEnvelope:
        """빈 OCRResultEnvelope 생성 (실패 시 반환용)

        Args:
            source: 입력 소스 타입 ('bytes', 'nparray', 'path')
            lang: 인식 언어
            engine: OCR 엔진 이름

        Returns:
            빈 OCRResultEnvelope
        """
        return OCRResultEnvelope(
            stage="ocr",
            data=OCRData(
                items=[OCRItem(rec_texts=[], rec_scores=[], dt_polys=[])]
            ),
            meta=OCRMeta(items=0, source=source, lang=lang, engine=engine),
        )


__all__ = [
    "BaseOCRService",
]

