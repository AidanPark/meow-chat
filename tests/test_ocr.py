"""OCR 서비스 테스트"""

from PIL import Image

from src.services.ocr.dummy import DummyOCR


def test_dummy_ocr_extract_text(dummy_ocr_service, sample_image):
    """더미 OCR 텍스트 추출 테스트"""
    result = dummy_ocr_service.extract_text(sample_image)

    assert result.text is not None
    assert len(result.text) > 0
    assert result.confidence == 1.0
    assert result.metadata["source"] == "dummy"


def test_dummy_ocr_extract_from_multiple_images(dummy_ocr_service):
    """더미 OCR 다중 이미지 추출 테스트"""
    images = [Image.new("RGB", (100, 100), color="white") for _ in range(3)]
    results = dummy_ocr_service.extract_text_from_images(images)

    assert len(results) == 3
    for result in results:
        assert result.text is not None
        assert len(result.text) > 0

