"""라인 전처리 모듈 테스트

Step 2.6: line_preprocessor.py 기능 검증
- OCR 결과에서 토큰 추출
- Y좌표 기반 라인 그룹핑
- 값/단위 분리
- OCRResultEnvelope/OCRItem 호환성
"""

import pytest
from typing import Dict, List

from src.services.lab_extraction.line_preprocessor import (
    extract_tokens_with_geometry,
    assign_line_indices_by_y,
    group_tokens_by_line,
    extract_and_group_lines,
    Settings,
    LinePreprocessor,
)
from src.models.envelopes import OCRItem, OCRData, OCRMeta, OCRResultEnvelope


# =============================================================================
# 테스트 픽스처
# =============================================================================

@pytest.fixture
def sample_ocr_item():
    """샘플 OCRItem - 간단한 검사 결과"""
    return OCRItem(
        rec_texts=["WBC", "12.5", "K/L", "RBC", "7.2", "M/L"],
        rec_scores=[0.95, 0.92, 0.88, 0.94, 0.91, 0.89],
        dt_polys=[
            # WBC: 첫 번째 줄 왼쪽
            [[10, 100], [60, 100], [60, 120], [10, 120]],
            # 12.5: 첫 번째 줄 중간
            [[70, 100], [120, 100], [120, 120], [70, 120]],
            # K/L: 첫 번째 줄 오른쪽
            [[130, 100], [170, 100], [170, 120], [130, 120]],
            # RBC: 두 번째 줄 왼쪽
            [[10, 150], [60, 150], [60, 170], [10, 170]],
            # 7.2: 두 번째 줄 중간
            [[70, 150], [120, 150], [120, 170], [70, 170]],
            # M/L: 두 번째 줄 오른쪽
            [[130, 150], [170, 150], [170, 170], [130, 170]],
        ]
    )


@pytest.fixture
def sample_ocr_item_single_line():
    """단일 라인 OCRItem"""
    return OCRItem(
        rec_texts=["ALT", "45", "U/L"],
        rec_scores=[0.95, 0.92, 0.88],
        dt_polys=[
            [[10, 100], [50, 100], [50, 120], [10, 120]],
            [[60, 100], [100, 100], [100, 120], [60, 120]],
            [[110, 100], [150, 100], [150, 120], [110, 120]],
        ]
    )


@pytest.fixture
def sample_ocr_dict():
    """딕셔너리 형태 OCR 결과 (레거시 호환)"""
    return {
        'rec_texts': ["BUN", "25", "mg/dL"],
        'rec_scores': [0.95, 0.92, 0.88],
        'dt_polys': [
            [[10, 100], [50, 100], [50, 120], [10, 120]],
            [[60, 100], [100, 100], [100, 120], [60, 120]],
            [[110, 100], [180, 100], [180, 120], [110, 120]],
        ]
    }


@pytest.fixture
def sample_envelope(sample_ocr_item):
    """샘플 OCRResultEnvelope"""
    return OCRResultEnvelope(
        stage='ocr',
        data=OCRData(items=[sample_ocr_item]),
        meta=OCRMeta(items=6, engine='EasyOCR')
    )


# =============================================================================
# extract_tokens_with_geometry 테스트
# =============================================================================

class TestExtractTokensWithGeometry:
    """토큰 추출 테스트"""

    def test_extract_from_ocr_item(self, sample_ocr_item):
        """OCRItem에서 토큰 추출"""
        tokens = extract_tokens_with_geometry(sample_ocr_item)

        assert len(tokens) == 6
        assert tokens[0]["text"] == "WBC"
        assert tokens[0]["confidence"] == 0.95
        assert tokens[0]["x_left"] is not None
        assert tokens[0]["y_center"] is not None

    def test_extract_from_dict(self, sample_ocr_dict):
        """딕셔너리에서 토큰 추출"""
        tokens = extract_tokens_with_geometry(sample_ocr_dict)

        assert len(tokens) == 3
        assert tokens[0]["text"] == "BUN"

    def test_extract_geometry_values(self, sample_ocr_item_single_line):
        """기하 정보 추출 확인"""
        tokens = extract_tokens_with_geometry(sample_ocr_item_single_line)

        first_token = tokens[0]
        assert first_token["x_left"] == 10
        assert first_token["x_right"] == 50
        assert first_token["y_top"] == 100
        assert first_token["y_bottom"] == 120
        assert first_token["y_center"] == 110
        assert first_token["raw_h"] == 20

    def test_extract_empty_result(self):
        """빈 결과 처리"""
        empty_item = OCRItem(rec_texts=[], rec_scores=[], dt_polys=[])
        tokens = extract_tokens_with_geometry(empty_item)
        assert tokens == []

    def test_extract_mismatched_lengths(self):
        """길이 불일치 시 빈 결과"""
        bad_item = OCRItem(
            rec_texts=["A", "B"],
            rec_scores=[0.9],  # 길이 불일치
            dt_polys=[]
        )
        tokens = extract_tokens_with_geometry(bad_item)
        assert tokens == []


# =============================================================================
# assign_line_indices_by_y 테스트
# =============================================================================

class TestAssignLineIndicesByY:
    """Y좌표 기반 라인 인덱스 부여 테스트"""

    def test_assign_two_lines(self, sample_ocr_item):
        """두 줄 라인 인덱스 부여"""
        tokens = extract_tokens_with_geometry(sample_ocr_item)
        tokens = assign_line_indices_by_y(tokens)

        # 첫 번째 줄 (y~110)
        assert tokens[0]["line_index"] == 0
        assert tokens[1]["line_index"] == 0
        assert tokens[2]["line_index"] == 0

        # 두 번째 줄 (y~160)
        assert tokens[3]["line_index"] == 1
        assert tokens[4]["line_index"] == 1
        assert tokens[5]["line_index"] == 1

    def test_assign_single_line(self, sample_ocr_item_single_line):
        """단일 라인"""
        tokens = extract_tokens_with_geometry(sample_ocr_item_single_line)
        tokens = assign_line_indices_by_y(tokens)

        for token in tokens:
            assert token["line_index"] == 0

    def test_assign_empty(self):
        """빈 리스트"""
        result = assign_line_indices_by_y([])
        assert result == []

    def test_alpha_sensitivity(self, sample_ocr_item):
        """alpha 파라미터 민감도"""
        tokens = extract_tokens_with_geometry(sample_ocr_item)

        # 낮은 alpha (더 엄격)
        tokens_strict = assign_line_indices_by_y(tokens.copy(), alpha=0.3)

        # 높은 alpha (더 관대)
        tokens_loose = assign_line_indices_by_y(tokens.copy(), alpha=1.5)

        # 결과가 다를 수 있음 (기본적으로 두 줄이 분리되어야 함)
        assert all("line_index" in t for t in tokens_strict)
        assert all("line_index" in t for t in tokens_loose)


# =============================================================================
# group_tokens_by_line 테스트
# =============================================================================

class TestGroupTokensByLine:
    """라인 그룹핑 테스트"""

    def test_group_two_lines(self, sample_ocr_item):
        """두 줄 그룹핑"""
        tokens = extract_tokens_with_geometry(sample_ocr_item)
        grouped = group_tokens_by_line(tokens)

        assert len(grouped) == 2
        assert len(grouped[0]) == 3  # WBC, 12.5, K/L
        assert len(grouped[1]) == 3  # RBC, 7.2, M/L

    def test_group_x_order(self, sample_ocr_item):
        """x_left 기준 정렬"""
        tokens = extract_tokens_with_geometry(sample_ocr_item)
        grouped = group_tokens_by_line(tokens, order="x_left")

        # 첫 번째 줄 x 순서 확인
        line1 = grouped[0]
        assert line1[0]["text"] == "WBC"  # x_left=10
        assert line1[1]["text"] == "12.5"  # x_left=70
        assert line1[2]["text"] == "K/L"  # x_left=130

    def test_group_empty(self):
        """빈 리스트"""
        result = group_tokens_by_line([])
        assert result == []


# =============================================================================
# extract_and_group_lines 통합 테스트
# =============================================================================

class TestExtractAndGroupLines:
    """통합 파이프라인 테스트"""

    def test_full_pipeline_ocr_item(self, sample_ocr_item):
        """OCRItem 전체 파이프라인"""
        grouped = extract_and_group_lines(sample_ocr_item, isDebug=False)

        assert len(grouped) == 2
        assert grouped[0][0]["text"] == "WBC"
        assert grouped[1][0]["text"] == "RBC"

    def test_full_pipeline_dict(self, sample_ocr_dict):
        """딕셔너리 전체 파이프라인"""
        grouped = extract_and_group_lines(sample_ocr_dict, isDebug=False)

        assert len(grouped) == 1
        assert grouped[0][0]["text"] == "BUN"

    def test_geometry_preserved(self, sample_ocr_item):
        """기하 정보 보존 확인"""
        grouped = extract_and_group_lines(sample_ocr_item, isDebug=False)

        first_token = grouped[0][0]
        assert "x_left" in first_token
        assert "x_right" in first_token
        assert "y_top" in first_token
        assert "y_bottom" in first_token
        assert "line_index" in first_token


# =============================================================================
# OCRResultEnvelope 호환성 테스트
# =============================================================================

class TestEnvelopeCompatibility:
    """OCRResultEnvelope 호환성 테스트"""

    def test_extract_from_envelope_item(self, sample_envelope):
        """Envelope의 items[0]에서 추출"""
        ocr_item = sample_envelope.data.items[0]
        tokens = extract_tokens_with_geometry(ocr_item)

        assert len(tokens) == 6
        assert tokens[0]["text"] == "WBC"

    def test_full_pipeline_with_envelope(self, sample_envelope):
        """Envelope 전체 파이프라인"""
        ocr_item = sample_envelope.data.items[0]
        grouped = extract_and_group_lines(ocr_item, isDebug=False)

        assert len(grouped) == 2

    def test_getattr_access(self, sample_ocr_item):
        """getattr 방식 접근 호환성"""
        # line_preprocessor 내부에서 getattr 사용
        rec_texts = getattr(sample_ocr_item, 'rec_texts', None)
        rec_scores = getattr(sample_ocr_item, 'rec_scores', None)
        dt_polys = getattr(sample_ocr_item, 'dt_polys', None)

        assert rec_texts is not None
        assert rec_scores is not None
        assert dt_polys is not None


# =============================================================================
# Settings 및 LinePreprocessor 클래스 테스트
# =============================================================================

class TestSettings:
    """Settings 테스트"""

    def test_default_settings(self):
        """기본 설정"""
        settings = Settings()
        assert settings.order == "x_left"
        assert settings.alpha == 0.7
        assert settings.debug is True

    def test_custom_settings(self):
        """커스텀 설정"""
        settings = Settings(order="source", alpha=0.5, debug=False)
        assert settings.order == "source"
        assert settings.alpha == 0.5
        assert settings.debug is False


class TestLinePreprocessor:
    """LinePreprocessor 클래스 테스트"""

    def test_init_default(self):
        """기본 초기화"""
        processor = LinePreprocessor()
        assert processor.settings is not None
        assert processor.unit_lexicon is None

    def test_init_with_settings(self):
        """설정과 함께 초기화"""
        settings = Settings(debug=False, alpha=0.5)
        processor = LinePreprocessor(settings=settings)
        assert processor.settings.debug is False
        assert processor.settings.alpha == 0.5

    def test_extract_tokens(self, sample_ocr_item):
        """토큰 추출"""
        processor = LinePreprocessor()
        tokens = processor.extract_tokens_with_geometry(sample_ocr_item)
        assert len(tokens) == 6

    def test_assign_line_indices(self, sample_ocr_item):
        """라인 인덱스 부여"""
        processor = LinePreprocessor()
        tokens = processor.extract_tokens_with_geometry(sample_ocr_item)
        tokens = processor.assign_line_indices_by_y(tokens)
        assert all("line_index" in t for t in tokens)

    def test_group_tokens(self, sample_ocr_item):
        """토큰 그룹핑"""
        processor = LinePreprocessor()
        tokens = processor.extract_tokens_with_geometry(sample_ocr_item)
        grouped = processor.group_tokens_by_line(tokens)
        assert len(grouped) == 2

    def test_extract_and_group(self, sample_ocr_item):
        """통합 파이프라인"""
        processor = LinePreprocessor(settings=Settings(debug=False))
        grouped = processor.extract_and_group_lines(sample_ocr_item)
        assert len(grouped) == 2
        assert grouped[0][0]["text"] == "WBC"


# =============================================================================
# 값/단위 분리 테스트
# =============================================================================

class TestValueUnitSplit:
    """값/단위 분리 테스트 (extract_and_group_lines 내부 로직)"""

    def test_value_with_unit(self):
        """값과 단위가 붙은 경우"""
        ocr_item = OCRItem(
            rec_texts=["ALT", "45 U/L"],  # 값과 단위가 공백으로 분리
            rec_scores=[0.95, 0.92],
            dt_polys=[
                [[10, 100], [50, 100], [50, 120], [10, 120]],
                [[60, 100], [150, 100], [150, 120], [60, 120]],
            ]
        )
        grouped = extract_and_group_lines(ocr_item, isDebug=False)

        # 분리 후 토큰 수 확인 (45와 U/L이 분리될 수 있음)
        assert len(grouped) == 1
        line = grouped[0]
        # 최소한 2개 이상의 토큰
        assert len(line) >= 2


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_none_input(self):
        """None 입력"""
        # rec_texts가 None인 경우
        result = extract_tokens_with_geometry({'rec_texts': None})
        assert result == []

    def test_missing_polys(self):
        """폴리곤 정보 없음"""
        ocr_item = OCRItem(
            rec_texts=["ABC"],
            rec_scores=[0.9],
            dt_polys=[]  # 빈 폴리곤
        )
        tokens = extract_tokens_with_geometry(ocr_item)
        assert len(tokens) == 1
        assert tokens[0]["text"] == "ABC"
        assert tokens[0]["x_left"] is None  # 폴리곤 없으므로 None

    def test_flat_poly_format(self):
        """플랫 폴리곤 형식 (8개 값)"""
        ocr_dict = {
            'rec_texts': ["TEST"],
            'rec_scores': [0.9],
            'dt_polys': [
                [10, 100, 50, 100, 50, 120, 10, 120]  # 플랫 형식
            ]
        }
        tokens = extract_tokens_with_geometry(ocr_dict)
        assert len(tokens) == 1
        assert tokens[0]["x_left"] == 10
        assert tokens[0]["x_right"] == 50

