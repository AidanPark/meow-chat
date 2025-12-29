"""참조 데이터 패키지
검사항목 코드/단위의 렉시콘 및 참조 데이터를 제공합니다.
주요 모듈:
- reference_data: 검사항목 참조 데이터 (CBC, Chemistry 등)
- code_lexicon: 검사항목 코드 사전 및 해석기
- unit_lexicon: 단위 사전 및 해석기
"""
from .reference_data import REFERENCE_TESTS
from .code_lexicon import (
    build_code_lexicon,
    get_code_lexicon,
    list_all_codes,
    resolve_code,
)
from .unit_lexicon import (
    build_unit_lexicon,
    get_unit_lexicon,
    list_all_units,
    resolve_unit,
)
__all__ = [
    # reference_data
    "REFERENCE_TESTS",
    # code_lexicon
    "build_code_lexicon",
    "get_code_lexicon",
    "list_all_codes",
    "resolve_code",
    # unit_lexicon
    "build_unit_lexicon",
    "get_unit_lexicon",
    "list_all_units",
    "resolve_unit",
]
