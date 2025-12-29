"""MyEasyOCR 서비스 테스트

Step 2.2: EasyOCR 기반 OCR 서비스 검증
- OCRResultEnvelope 반환 형식
- line_preprocessor 호환성
"""

import pytest
import numpy as np
from PIL import Image
from unittest.mock import MagicMock, patch

from src.models.envelopes import OCRResultEnvelope, OCRItem
from src.services.ocr.easy_ocr import MyEasyOCR


class TestMyEasyOCRInit:
    """MyEasyOCR 초기화 테스트"""

    def test_default_init(self):
        """기본 초기화"""
        with patch.object(MyEasyOCR, '_create_reader', return_value=MagicMock()):
            ocr = MyEasyOCR()
            assert ocr.lang == "korean"
            assert ocr.languages == ['ko', 'en']

    def test_custom_languages(self):
        """사용자 지정 언어"""
        with patch.object(MyEasyOCR, '_create_reader', return_value=MagicMock()):
            ocr = MyEasyOCR(languages=['ja', 'en'])
            assert ocr.languages == ['ja', 'en']

    def test_cpu_mode(self):
        """CPU 모드 명시적 지정"""
        with patch.object(MyEasyOCR, '_create_reader', return_value=MagicMock()):
            ocr = MyEasyOCR(use_gpu=False)
            assert ocr.use_gpu is False

    def test_gpu_fallback_when_unavailable(self):
        """CUDA 사용 불가 시 CPU 폴백"""
        with patch.object(MyEasyOCR, '_create_reader', return_value=MagicMock()):
            with patch('torch.cuda.is_available', return_value=False):
                ocr = MyEasyOCR(use_gpu=True)
                assert ocr.use_gpu is False


class TestMyEasyOCRConvert:
    """결과 변환 테스트"""

    def get_ocr(self):
        with patch.object(MyEasyOCR, '_create_reader', return_value=MagicMock()):
            return MyEasyOCR(use_gpu=False)

    def test_convert_to_ocr_item(self):
        """EasyOCR 결과를 OCRItem으로 변환"""
        ocr = self.get_ocr()
        raw_results = [
            ([[10, 100], [50, 100], [50, 120], [10, 120]], "WBC", 0.95),
            ([[60, 100], [100, 100], [100, 120], [60, 120]], "12.5", 0.92),
            ([[110, 100], [150, 100], [150, 120], [110, 120]], "K/L", 0.88),
        ]

        item = ocr._convert_to_ocr_item(raw_results)

        assert isinstance(item, OCRItem)
        assert item.rec_texts == ["WBC", "12.5", "K/L"]
        assert item.rec_scores == [0.95, 0.92, 0.88]
        assert len(item.dt_polys) == 3

    def test_convert_numpy_bbox(self):
        """numpy array bbox 변환"""
        ocr = self.get_ocr()
        raw_results = [
            (np.array([[10, 100], [50, 100], [50, 120], [10, 120]]), "WBC", 0.95),
        ]

        item = ocr._convert_to_ocr_item(raw_results)

        assert item.rec_texts == ["WBC"]
        assert isinstance(item.dt_polys[0], list)
        assert isinstance(item.dt_polys[0][0], list)

    def test_convert_empty_results(self):
        """빈 결과 변환"""
        ocr = self.get_ocr()
        item = ocr._convert_to_ocr_item([])

        assert item.rec_texts == []
        assert item.rec_scores == []
        assert item.dt_polys == []


class TestMyEasyOCRRunOCR:
    """OCR 실행 테스트"""

    def test_run_ocr_from_path(self):
        """파일 경로에서 OCR"""
        mock_reader = MagicMock()
        mock_reader.readtext.return_value = [
            ([[10, 10], [50, 10], [50, 30], [10, 30]], "WBC", 0.95),
            ([[10, 40], [50, 40], [50, 60], [10, 60]], "12.5", 0.92),
        ]

        with patch.object(MyEasyOCR, '_create_reader', return_value=mock_reader):
            ocr = MyEasyOCR(use_gpu=False)
            result = ocr.run_ocr_from_path("/path/to/image.png")

        assert isinstance(result, OCRResultEnvelope)
        assert result.stage == 'ocr'
        assert result.meta.source == 'path'
        assert result.meta.engine == 'EasyOCR'
        assert len(result.data.items) == 1
        assert result.data.items[0].rec_texts == ["WBC", "12.5"]

    def test_run_ocr_from_nparray(self):
        """numpy 배열에서 OCR"""
        mock_reader = MagicMock()
        mock_reader.readtext.return_value = [
            ([[0, 0], [10, 0], [10, 10], [0, 10]], "RBC", 0.90),
        ]

        with patch.object(MyEasyOCR, '_create_reader', return_value=mock_reader):
            ocr = MyEasyOCR(use_gpu=False)
            image = np.zeros((100, 100, 3), dtype=np.uint8)
            result = ocr.run_ocr_from_nparray(image)

        assert isinstance(result, OCRResultEnvelope)
        assert result.meta.source == 'nparray'
        assert result.data.items[0].rec_texts == ["RBC"]

    def test_run_ocr_unified(self):
        """통합 run_ocr 메서드"""
        mock_reader = MagicMock()
        mock_reader.readtext.return_value = []

        with patch.object(MyEasyOCR, '_create_reader', return_value=mock_reader):
            ocr = MyEasyOCR(use_gpu=False)

            # 파일 경로
            result = ocr.run_ocr("/path/to/image.png")
            assert result.meta.source == 'path'

            # numpy 배열
            result = ocr.run_ocr(np.zeros((10, 10, 3), dtype=np.uint8))
            assert result.meta.source == 'nparray'

            # PIL Image
            result = ocr.run_ocr(Image.new("RGB", (10, 10)))
            assert result.meta.source == 'nparray'

    def test_run_ocr_empty_result(self):
        """빈 OCR 결과"""
        mock_reader = MagicMock()
        mock_reader.readtext.return_value = []

        with patch.object(MyEasyOCR, '_create_reader', return_value=mock_reader):
            ocr = MyEasyOCR(use_gpu=False)
            result = ocr.run_ocr_from_path("/path/to/image.png")

        assert isinstance(result, OCRResultEnvelope)
        assert result.meta.items == 0
        assert result.data.items[0].rec_texts == []


class TestMyEasyOCRLinePreprocessorCompatibility:
    """line_preprocessor 호환성 테스트"""

    def test_ocr_item_getattr_access(self):
        """getattr 방식 접근 (line_preprocessor 호환)"""
        mock_reader = MagicMock()
        mock_reader.readtext.return_value = [
            ([[10, 100], [50, 100], [50, 120], [10, 120]], "WBC", 0.95),
            ([[60, 100], [100, 100], [100, 120], [60, 120]], "12.5", 0.92),
        ]

        with patch.object(MyEasyOCR, '_create_reader', return_value=mock_reader):
            ocr = MyEasyOCR(use_gpu=False)
            envelope = ocr.run_ocr_from_path("/path/to/image.png")

        # line_preprocessor가 사용하는 방식
        ocr_result = envelope.data.items[0]

        # getattr 접근
        rec_texts = getattr(ocr_result, 'rec_texts', None)
        rec_scores = getattr(ocr_result, 'rec_scores', None)
        dt_polys = getattr(ocr_result, 'dt_polys', None)

        assert rec_texts == ["WBC", "12.5"]
        assert rec_scores == [0.95, 0.92]
        assert len(dt_polys) == 2

    def test_ocr_item_dict_access(self):
        """to_dict 후 dict 접근"""
        mock_reader = MagicMock()
        mock_reader.readtext.return_value = [
            ([[10, 100], [50, 100], [50, 120], [10, 120]], "WBC", 0.95),
        ]

        with patch.object(MyEasyOCR, '_create_reader', return_value=mock_reader):
            ocr = MyEasyOCR(use_gpu=False)
            envelope = ocr.run_ocr_from_path("/path/to/image.png")

        # dict 변환 후 접근
        ocr_result = envelope.data.items[0].to_dict()

        assert ocr_result.get('rec_texts') == ["WBC"]
        assert ocr_result.get('rec_scores') == [0.95]
        assert 'dt_polys' in ocr_result


class TestMyEasyOCRDeviceInfo:
    """디바이스 정보 테스트"""

    def test_get_device_info(self):
        """디바이스 정보 조회"""
        with patch.object(MyEasyOCR, '_create_reader', return_value=MagicMock()):
            ocr = MyEasyOCR(use_gpu=False)
            info = ocr.get_device_info()

        assert info["engine"] == "EasyOCR"
        assert info["use_gpu"] is False
        assert info["lang"] == "korean"

    def test_is_gpu_enabled(self):
        """GPU 상태 확인"""
        with patch.object(MyEasyOCR, '_create_reader', return_value=MagicMock()):
            ocr = MyEasyOCR(use_gpu=False)
            assert ocr.is_gpu_enabled is False


class TestMyEasyOCRIntegration:
    """통합 테스트 (실제 EasyOCR 사용)"""

    @pytest.mark.skipif(
        not pytest.importorskip("easyocr", reason="easyocr not installed"),
        reason="easyocr not installed"
    )
    def test_real_ocr_simple_image(self):
        """실제 EasyOCR로 간단한 이미지 인식"""
        try:
            import torch
            use_gpu = torch.cuda.is_available()
        except ImportError:
            use_gpu = False

        # 텍스트 이미지 생성
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (200, 50), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "TEST123", fill="black")

        ocr = MyEasyOCR(languages=['en'], use_gpu=use_gpu)
        result = ocr.run_ocr(img)

        assert isinstance(result, OCRResultEnvelope)
        assert result.stage == 'ocr'
        assert result.meta.engine == 'EasyOCR'
        # 텍스트 인식 여부는 폰트에 따라 다를 수 있음
        assert isinstance(result.data.items[0].rec_texts, list)

