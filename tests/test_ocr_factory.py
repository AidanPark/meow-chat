"""OCR Factory 테스트

Step 2.3: Factory 패턴으로 OCR 서비스 생성 테스트
"""

import pytest
from unittest.mock import patch

from src.services.ocr.factory import get_ocr_service
from src.services.ocr.dummy_ocr import DummyOCR
from src.services.ocr.easy_ocr import MyEasyOCR


class TestOCRFactory:
    """OCR Factory 테스트"""

    def test_get_easyocr_service(self):
        """easyocr provider 선택"""
        with patch('src.services.ocr.factory.settings') as mock_settings:
            mock_settings.ocr_provider = 'easyocr'
            # MyEasyOCR의 reader 생성 건너뛰기
            with patch.object(MyEasyOCR, '_create_reader', return_value=None):
                service = get_ocr_service()
                assert isinstance(service, MyEasyOCR)

    def test_get_dummy_service(self):
        """dummy provider 선택"""
        with patch('src.services.ocr.factory.settings') as mock_settings:
            mock_settings.ocr_provider = 'dummy'
            service = get_ocr_service()
            assert isinstance(service, DummyOCR)

    def test_invalid_provider(self):
        """잘못된 provider"""
        with patch('src.services.ocr.factory.settings') as mock_settings:
            mock_settings.ocr_provider = 'invalid'
            with pytest.raises(ValueError, match="지원하지 않는 OCR 제공자"):
                get_ocr_service()

