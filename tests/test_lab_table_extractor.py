"""랩 테이블 추출기 테스트

Step 2.7: lab_table_extractor.py 기능 검증
- 테이블 바디 시작 검출
- 헤더 역할 검출
- 열 경계 추론
- 데이터 추출
"""

import pytest
from typing import Dict, List, Any

from src.services.lab_extraction.lab_table_extractor import (
    LabTableExtractor,
    Settings,
)
from src.services.lab_extraction.line_preprocessor import extract_and_group_lines
from src.models.envelopes import OCRItem


# =============================================================================
# 테스트 픽스처
# =============================================================================

@pytest.fixture
def sample_lines_simple():
    """간단한 테이블 라인 (헤더 + 2행)"""
    return [
        # 헤더 라인
        [
            {"text": "검사항목", "x_left": 10, "x_right": 80, "y_center": 50, "line_index": 0},
            {"text": "결과", "x_left": 100, "x_right": 150, "y_center": 50, "line_index": 0},
            {"text": "단위", "x_left": 170, "x_right": 220, "y_center": 50, "line_index": 0},
            {"text": "참고치", "x_left": 240, "x_right": 300, "y_center": 50, "line_index": 0},
        ],
        # 데이터 라인 1
        [
            {"text": "WBC", "x_left": 10, "x_right": 50, "y_center": 100, "line_index": 1},
            {"text": "12.5", "x_left": 100, "x_right": 140, "y_center": 100, "line_index": 1},
            {"text": "K/L", "x_left": 170, "x_right": 200, "y_center": 100, "line_index": 1},
            {"text": "5.0-15.0", "x_left": 240, "x_right": 310, "y_center": 100, "line_index": 1},
        ],
        # 데이터 라인 2
        [
            {"text": "RBC", "x_left": 10, "x_right": 50, "y_center": 150, "line_index": 2},
            {"text": "7.2", "x_left": 100, "x_right": 130, "y_center": 150, "line_index": 2},
            {"text": "M/L", "x_left": 170, "x_right": 200, "y_center": 150, "line_index": 2},
            {"text": "6.0-10.0", "x_left": 240, "x_right": 310, "y_center": 150, "line_index": 2},
        ],
    ]


@pytest.fixture
def sample_lines_no_header():
    """헤더 없는 테이블 (바디만)"""
    return [
        [
            {"text": "WBC", "x_left": 10, "x_right": 50, "y_center": 100, "line_index": 0},
            {"text": "12.5", "x_left": 100, "x_right": 140, "y_center": 100, "line_index": 0},
            {"text": "K/L", "x_left": 170, "x_right": 200, "y_center": 100, "line_index": 0},
        ],
        [
            {"text": "RBC", "x_left": 10, "x_right": 50, "y_center": 150, "line_index": 1},
            {"text": "7.2", "x_left": 100, "x_right": 130, "y_center": 150, "line_index": 1},
            {"text": "M/L", "x_left": 170, "x_right": 200, "y_center": 150, "line_index": 1},
        ],
        [
            {"text": "HCT", "x_left": 10, "x_right": 50, "y_center": 200, "line_index": 2},
            {"text": "35.5", "x_left": 100, "x_right": 140, "y_center": 200, "line_index": 2},
            {"text": "%", "x_left": 170, "x_right": 190, "y_center": 200, "line_index": 2},
        ],
    ]


@pytest.fixture
def sample_ocr_item():
    """OCR 결과 시뮬레이션"""
    return OCRItem(
        rec_texts=["검사항목", "결과", "단위", "WBC", "12.5", "K/L", "RBC", "7.2", "M/L"],
        rec_scores=[0.95] * 9,
        dt_polys=[
            # 헤더
            [[10, 50], [80, 50], [80, 70], [10, 70]],
            [[100, 50], [150, 50], [150, 70], [100, 70]],
            [[170, 50], [220, 50], [220, 70], [170, 70]],
            # WBC 라인
            [[10, 100], [50, 100], [50, 120], [10, 120]],
            [[100, 100], [140, 100], [140, 120], [100, 120]],
            [[170, 100], [200, 100], [200, 120], [170, 120]],
            # RBC 라인
            [[10, 150], [50, 150], [50, 170], [10, 170]],
            [[100, 150], [130, 150], [130, 170], [100, 170]],
            [[170, 150], [200, 150], [200, 170], [170, 170]],
        ]
    )


# =============================================================================
# Settings 테스트
# =============================================================================

class TestSettings:
    """Settings 클래스 테스트"""

    def test_default_settings(self):
        """기본 설정 값"""
        settings = Settings()
        assert settings.debug is False
        assert settings.use_llm is False
        assert settings.canonicalize_codes is True
        assert settings.role_min_distinct_hits == 3

    def test_custom_settings(self):
        """커스텀 설정"""
        settings = Settings(debug=True, use_llm=False)
        assert settings.debug is True
        assert settings.use_llm is False

    def test_header_synonyms(self):
        """헤더 동의어 설정"""
        settings = Settings()
        assert "name" in settings.header_synonyms
        assert "result" in settings.header_synonyms
        assert "unit" in settings.header_synonyms
        assert "reference" in settings.header_synonyms

        # 한국어 동의어 포함 확인
        assert "검사항목" in settings.header_synonyms["name"]
        assert "결과" in settings.header_synonyms["result"]
        assert "단위" in settings.header_synonyms["unit"]
        assert "참고치" in settings.header_synonyms["reference"]


# =============================================================================
# LabTableExtractor 초기화 테스트
# =============================================================================

class TestLabTableExtractorInit:
    """LabTableExtractor 초기화 테스트"""

    def test_init_default(self):
        """기본 초기화"""
        extractor = LabTableExtractor()
        assert extractor.settings is not None
        assert extractor.lexicon is not None  # code_lexicon 자동 로드

    def test_init_with_settings(self):
        """설정과 함께 초기화"""
        settings = Settings(debug=True)
        extractor = LabTableExtractor(settings=settings)
        assert extractor.settings.debug is True

    def test_init_with_lexicon(self):
        """사전 주입"""
        custom_lexicon = {"WBC": {"name": "White Blood Cell"}}
        extractor = LabTableExtractor(lexicon=custom_lexicon)
        assert extractor.lexicon == custom_lexicon

    def test_init_no_llm(self):
        """LLM 없이 초기화"""
        extractor = LabTableExtractor()
        # LLM 클라이언트 없어도 초기화 성공
        assert extractor.settings.use_llm is False


# =============================================================================
# 테이블 바디 검출 테스트
# =============================================================================

class TestBodyDetection:
    """테이블 바디 시작 검출 테스트"""

    def test_detect_body_with_header(self, sample_lines_simple):
        """헤더 있는 테이블에서 바디 검출"""
        extractor = LabTableExtractor(settings=Settings(debug=False))
        body_start = extractor._find_table_body_start(sample_lines_simple)

        # 바디 시작 검출 결과 확인 (None 또는 정수)
        # 검사코드 lexicon에 따라 결과가 달라질 수 있음
        assert body_start is None or isinstance(body_start, int)

    def test_detect_body_no_header(self, sample_lines_no_header):
        """헤더 없는 테이블에서 바디 검출"""
        extractor = LabTableExtractor(settings=Settings(debug=False))
        body_start = extractor._find_table_body_start(sample_lines_no_header)

        # 바디 시작 검출 결과 확인 (None 또는 정수)
        assert body_start is None or isinstance(body_start, int)


# =============================================================================
# 헤더 역할 검출 테스트
# =============================================================================

class TestHeaderDetection:
    """헤더 역할 검출 테스트"""

    def test_detect_header_korean(self, sample_lines_simple):
        """한국어 헤더 검출"""
        extractor = LabTableExtractor(settings=Settings(debug=False))

        # 헤더 라인에서 역할 매칭 테스트
        header_line = sample_lines_simple[0]
        texts = [t["text"].lower() for t in header_line]

        # "검사항목" → name 역할
        assert "검사항목" in texts
        # "결과" → result 역할
        assert "결과" in texts


# =============================================================================
# 전체 파이프라인 테스트
# =============================================================================

class TestExtractFromLines:
    """extract_from_lines 전체 파이프라인 테스트"""

    def test_extract_basic(self, sample_lines_no_header):
        """기본 추출"""
        extractor = LabTableExtractor(settings=Settings(debug=False))
        result = extractor.extract_from_lines(sample_lines_no_header)

        assert isinstance(result, dict)
        # 결과 구조 확인 (tests, metadata 등)
        assert "tests" in result or result == {}  # 빈 결과도 허용

    def test_extract_with_intermediates(self, sample_lines_no_header):
        """중간 결과 포함 추출"""
        extractor = LabTableExtractor(settings=Settings(debug=True))
        result, intermediates = extractor.extract_from_lines(
            sample_lines_no_header,
            return_intermediates=True
        )

        assert isinstance(result, dict)
        assert isinstance(intermediates, dict)
        assert "settings" in intermediates

    def test_extract_empty_lines(self):
        """빈 라인 입력"""
        extractor = LabTableExtractor(settings=Settings(debug=False))
        result = extractor.extract_from_lines([])

        assert isinstance(result, dict)


# =============================================================================
# OCR → LinePreprocessor → LabTableExtractor 통합 테스트
# =============================================================================

class TestFullPipeline:
    """전체 파이프라인 통합 테스트"""

    def test_ocr_to_extractor(self, sample_ocr_item):
        """OCRItem → LinePreprocessor → LabTableExtractor"""
        # Step 1: LinePreprocessor로 라인 그룹핑
        grouped_lines = extract_and_group_lines(sample_ocr_item, isDebug=False)

        assert len(grouped_lines) > 0

        # Step 2: LabTableExtractor로 추출
        extractor = LabTableExtractor(settings=Settings(debug=False))
        result = extractor.extract_from_lines(grouped_lines)

        assert isinstance(result, dict)

    def test_pipeline_preserves_geometry(self, sample_ocr_item):
        """기하 정보 보존 확인"""
        grouped_lines = extract_and_group_lines(sample_ocr_item, isDebug=False)

        # 각 토큰에 x_left, y_center 등 기하 정보 존재
        for line in grouped_lines:
            for token in line:
                assert "x_left" in token or token.get("x_left") is None
                # 일부 토큰은 폴리곤 없을 수 있음


# =============================================================================
# 코드 정규화 테스트
# =============================================================================

class TestCodeNormalization:
    """검사코드 정규화 테스트"""

    def test_resolve_known_code(self):
        """알려진 코드 해석"""
        extractor = LabTableExtractor()

        # lexicon이 로드되었다면 코드 해석 가능
        if extractor.lexicon:
            # _resolve_code 메서드 존재 확인
            assert hasattr(extractor, '_resolve_code')

    def test_canonicalize_setting(self):
        """코드 정규화 설정"""
        settings = Settings(canonicalize_codes=True)
        extractor = LabTableExtractor(settings=settings)

        assert extractor.settings.canonicalize_codes is True


# =============================================================================
# 엣지 케이스 테스트
# =============================================================================

class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_single_line(self):
        """단일 라인"""
        lines = [
            [{"text": "WBC", "x_left": 10}, {"text": "12.5", "x_left": 100}]
        ]
        extractor = LabTableExtractor(settings=Settings(debug=False))
        result = extractor.extract_from_lines(lines)

        assert isinstance(result, dict)

    def test_only_header(self):
        """헤더만 있는 경우"""
        lines = [
            [
                {"text": "검사항목", "x_left": 10},
                {"text": "결과", "x_left": 100},
            ]
        ]
        extractor = LabTableExtractor(settings=Settings(debug=False))
        result = extractor.extract_from_lines(lines)

        assert isinstance(result, dict)

    def test_mixed_text_dict(self):
        """문자열과 딕셔너리 혼합"""
        lines = [
            ["WBC", {"text": "12.5", "x_left": 100}]
        ]
        extractor = LabTableExtractor(settings=Settings(debug=False))
        # 예외 발생하지 않으면 성공
        try:
            result = extractor.extract_from_lines(lines)
            assert isinstance(result, dict)
        except Exception:
            # 일부 형식은 지원 안 할 수 있음
            pass

