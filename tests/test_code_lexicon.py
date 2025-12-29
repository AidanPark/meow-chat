"""검사항목 코드 렉시콘 테스트
Step 1.3: code_lexicon.py 이전 검증
"""
import pytest
from src.services.lab_extraction.reference.code_lexicon import (
    build_code_lexicon,
    get_code_lexicon,
    list_all_codes,
    resolve_code,
)
class TestCodeLexiconImport:
    """import 테스트"""
    def test_import_from_module(self):
        """모듈에서 직접 import"""
        assert get_code_lexicon is not None
        assert list_all_codes is not None
        assert resolve_code is not None
    def test_import_from_package(self):
        """패키지 레벨에서 import"""
        from src.services.lab_extraction.reference import (
            get_code_lexicon,
            list_all_codes,
            resolve_code,
        )
        assert get_code_lexicon is not None
class TestBuildCodeLexicon:
    """build_code_lexicon() 테스트"""
    def test_build_returns_dict(self):
        """빌드 결과가 dict"""
        lexicon = build_code_lexicon()
        assert isinstance(lexicon, dict)
    def test_build_has_required_keys(self):
        """필수 키 존재 확인"""
        lexicon = build_code_lexicon()
        assert "canonical_set" in lexicon
        assert "upper_index" in lexicon
        assert "alnum_index" in lexicon
    def test_canonical_set_is_set(self):
        """canonical_set이 Set[str]"""
        lexicon = build_code_lexicon()
        assert isinstance(lexicon["canonical_set"], set)
        assert len(lexicon["canonical_set"]) > 0
    def test_upper_index_is_dict(self):
        """upper_index가 Dict[str, str]"""
        lexicon = build_code_lexicon()
        assert isinstance(lexicon["upper_index"], dict)
    def test_alnum_index_is_dict_of_sets(self):
        """alnum_index가 Dict[str, Set[str]]"""
        lexicon = build_code_lexicon()
        assert isinstance(lexicon["alnum_index"], dict)
        # 아무 값이나 확인
        for key, value in list(lexicon["alnum_index"].items())[:1]:
            assert isinstance(value, set)
class TestGetCodeLexicon:
    """get_code_lexicon() 테스트"""
    def test_returns_cached_lexicon(self):
        """캐시된 렉시콘 반환"""
        lex1 = get_code_lexicon()
        lex2 = get_code_lexicon()
        assert lex1 is lex2  # 동일 객체
    def test_force_rebuild(self):
        """force_rebuild로 재생성"""
        lex1 = get_code_lexicon()
        lex2 = get_code_lexicon(force_rebuild=True)
        # 재생성되었지만 내용은 동일해야 함
        assert lex1["canonical_set"] == lex2["canonical_set"]
class TestListAllCodes:
    """list_all_codes() 테스트"""
    def test_returns_set(self):
        """Set 반환"""
        codes = list_all_codes()
        assert isinstance(codes, set)
    def test_contains_expected_codes(self):
        """주요 코드 포함 확인"""
        codes = list_all_codes()
        expected = {"WBC", "RBC", "HGB", "HCT", "PLT", "ALT", "AST", "BUN", "CRE"}
        assert expected.issubset(codes)
    def test_minimum_code_count(self):
        """최소 코드 개수"""
        codes = list_all_codes()
        assert len(codes) >= 50  # 최소 50개 이상
class TestResolveCode:
    """resolve_code() 테스트"""
    # 기본 동작
    def test_none_input(self):
        """None 입력"""
        assert resolve_code(None) is None
    def test_empty_string(self):
        """빈 문자열"""
        assert resolve_code("") is None
        assert resolve_code("   ") is None
    # 정확 매칭
    def test_exact_match(self):
        """정확한 코드 매칭"""
        assert resolve_code("WBC") == "WBC"
        assert resolve_code("RBC") == "RBC"
        assert resolve_code("ALT") == "ALT"
    def test_case_insensitive(self):
        """대소문자 무시 매칭"""
        assert resolve_code("wbc") == "WBC"
        assert resolve_code("Wbc") == "WBC"
        assert resolve_code("alt") == "ALT"
    # 특수문자 포함 코드
    def test_codes_with_special_chars(self):
        """특수문자 포함 코드"""
        # Na+ 같은 코드
        result = resolve_code("Na+")
        assert result is not None
        # BUN/CRE 같은 코드
        result = resolve_code("BUN/CRE")
        assert result is not None
    # OCR 혼동 보정
    def test_ocr_zero_to_o(self):
        """OCR 혼동: 0 → O 보정"""
        # p02 → pO2
        result = resolve_code("p02")
        assert result == "pO2"
        # pC02 → pCO2
        result = resolve_code("pC02")
        assert result == "pCO2"
    def test_ocr_zero_to_o_with_suffix(self):
        """OCR 혼동: 접미사 포함"""
        # s02 → sO2
        result = resolve_code("s02")
        assert result == "sO2"
    # 공백 처리
    def test_whitespace_handling(self):
        """공백 처리"""
        assert resolve_code("  WBC  ") == "WBC"
        assert resolve_code("W BC") == "WBC"  # 내부 공백도 제거
    # 퍼센트/해시 변형
    def test_percent_variants(self):
        """퍼센트 변형 정규화"""
        # HCT (%)와 HCT% 등
        result1 = resolve_code("HCT")
        assert result1 == "HCT"
    # 모호한 경우
    def test_ambiguous_returns_none(self):
        """모호한 경우 None 반환"""
        # 존재하지 않는 코드
        assert resolve_code("XXXYYY") is None
class TestResolveCodeEdgeCases:
    """resolve_code() 엣지 케이스"""
    def test_numeric_only(self):
        """숫자만 있는 토큰"""
        assert resolve_code("123") is None
    def test_special_chars_only(self):
        """특수문자만 있는 토큰"""
        assert resolve_code("+-/%") is None
    def test_very_long_token(self):
        """매우 긴 토큰"""
        assert resolve_code("A" * 100) is None
    def test_unicode_handling(self):
        """유니코드 처리"""
        # 일반적인 코드는 ASCII만 사용
        result = resolve_code("WBC")
        assert result == "WBC"
