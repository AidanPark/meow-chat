"""OCR 서비스 테스트"""

from PIL import Image

from src.models.envelopes import OCRResultEnvelope
from src.services.ocr.dummy_ocr import DummyOCR


def test_dummy_ocr_extract_text(dummy_ocr_service, sample_image):
    """더미 OCR 텍스트 추출 테스트"""
    result = dummy_ocr_service.extract_text(sample_image)

    assert isinstance(result, OCRResultEnvelope)
    assert result.stage == 'ocr'
    assert len(result.data.items) == 1
    assert len(result.data.items[0].rec_texts) > 0
    assert result.meta.engine == "DummyOCR"


def test_dummy_ocr_extract_from_multiple_images(dummy_ocr_service):
    """더미 OCR 다중 이미지 추출 테스트"""
    images = [Image.new("RGB", (100, 100), color="white") for _ in range(3)]
    results = dummy_ocr_service.extract_text_from_images(images)

    assert len(results) == 3
    for result in results:
        assert isinstance(result, OCRResultEnvelope)
        assert len(result.data.items[0].rec_texts) > 0
