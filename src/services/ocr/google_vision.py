"""Google Cloud Vision API OCR 구현"""

import io

from google.cloud import vision
from PIL import Image

from .base import BaseOCRService, OCRResult


class GoogleVisionOCR(BaseOCRService):
    """Google Cloud Vision API를 사용한 OCR 서비스"""

    def __init__(self):
        """Google Vision 클라이언트 초기화"""
        self.client = vision.ImageAnnotatorClient()

    def extract_text(self, image: Image.Image) -> OCRResult:
        """이미지에서 텍스트 추출

        Args:
            image: PIL Image 객체

        Returns:
            OCRResult 객체
        """
        # PIL Image를 바이트로 변환
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format="PNG")
        img_byte_arr = img_byte_arr.getvalue()

        # Google Vision API 요청
        vision_image = vision.Image(content=img_byte_arr)
        response = self.client.text_detection(image=vision_image)

        if response.error.message:
            raise Exception(f"Google Vision API 오류: {response.error.message}")

        # 텍스트 추출
        texts = response.text_annotations
        if not texts:
            return OCRResult(text="", confidence=0.0, metadata={"source": "google_vision"})

        # 첫 번째 annotation이 전체 텍스트
        full_text = texts[0].description
        confidence = None  # Google Vision은 전체 신뢰도를 제공하지 않음

        return OCRResult(
            text=full_text,
            confidence=confidence,
            metadata={
                "source": "google_vision",
                "num_blocks": len(texts) - 1,  # 첫 번째는 전체 텍스트
            },
        )

