"""검사결과지 데이터 추출 패키지

OCR 결과를 받아 검사결과 데이터를 추출하고 구조화하는 기능을 제공합니다.

주요 모듈:
- line_preprocessor: OCR 텍스트 라인 전처리 (Y좌표 기반 그룹핑, 토큰 분리)
- lab_table_extractor: 검사결과 테이블 추출 (규칙 기반 파싱)
- lab_report_extractor: 추출 파이프라인 오케스트레이션
- unit_normalizer: 단위 정규화 (g/dL, µg 등)
- code_normalizer: 검사코드 정규화
- reference/: 검사코드/단위 사전 데이터
"""

from .line_preprocessor import (
    LinePreprocessor,
    extract_and_group_lines,
    extract_tokens_with_geometry,
)

from .lab_table_extractor import (
    LabTableExtractor,
    Settings as LabTableExtractorSettings,
)

from .lab_report_extractor import LabReportExtractor

from .unit_normalizer import normalize_unit_simple

from .code_normalizer import resolve_code_with_fallback

__all__ = [
    # line_preprocessor
    "LinePreprocessor",
    "extract_and_group_lines",
    "extract_tokens_with_geometry",
    # lab_table_extractor
    "LabTableExtractor",
    "LabTableExtractorSettings",
    # lab_report_extractor
    "LabReportExtractor",
    # unit_normalizer
    "normalize_unit_simple",
    # code_normalizer
    "resolve_code_with_fallback",
]

