"""Google Cloud Vision API OCR 구현"""

import io

from google.cloud import vision
from PIL import Image

from src.models.envelopes import OCRData, OCRItem, OCRMeta, OCRResultEnvelope
from .base import BaseOCRService


class GoogleVisionOCR(BaseOCRService):
    """Google Cloud Vision API를 사용한 OCR 서비스"""

    def __init__(self):
        """Google Vision 클라이언트 초기화"""
        self.client = vision.ImageAnnotatorClient()

    def extract_text(self, image: Image.Image) -> OCRResultEnvelope:
        """이미지에서 텍스트 추출

        Args:
            image: PIL Image 객체

        Returns:
            OCRResultEnvelope 객체
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
            # 빈 결과
            item = OCRItem(rec_texts=[], rec_scores=[], dt_polys=[])
            return OCRResultEnvelope(
                stage='ocr',
                data=OCRData(items=[item]),
                meta=OCRMeta(items=0, source='bytes', lang='auto', engine='GoogleVision')
            )

        # 첫 번째 annotation이 전체 텍스트
        full_text = texts[0].description

        # 단순 텍스트만 - 상세 위치 정보 없음 (필요시 나중에 추가 가능)
        item = OCRItem(
            rec_texts=[full_text],
            rec_scores=[1.0],
            dt_polys=[],  # Google Vision은 위치 정보 생략
        )

        return OCRResultEnvelope(
            stage='ocr',
            data=OCRData(items=[item]),
            meta=OCRMeta(
                items=1,
                source='bytes',
                lang='auto',
                engine='GoogleVision'
            )
        )
