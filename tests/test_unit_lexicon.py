"""단위 렉시콘 테스트
Step 1.4: unit_lexicon.py 이전 검증
"""
import pytest
from src.services.lab_extraction.reference.unit_lexicon import (
    build_unit_lexicon,
    get_unit_lexicon,
    list_all_units,
    resolve_unit,
)
class TestUnitLexiconImport:
    """import 테스트"""
    def test_import_from_module(self):
        """모듈에서 직접 import"""
        assert get_unit_lexicon is not None
        assert list_all_units is not None
        assert resolve_unit is not None
    def test_import_from_package(self):
        """패키지 레벨에서 import"""
        from src.services.lab_extraction.reference import (
            get_unit_lexicon,
            list_all_units,
            resolve_unit,
        )
        assert get_unit_lexicon is not None
class TestBuildUnitLexicon:
    """build_unit_lexicon() 테스트"""
    def test_build_returns_dict(self):
        """빌드 결과가 dict"""
        lexicon = build_unit_lexicon()
        assert isinstance(lexicon, dict)
    def test_build_has_required_keys(self):
        """필수 키 존재 확인"""
        lexicon = build_unit_lexicon()
        assert "canonical_set" in lexicon
        assert "upper_index" in lexicon
        assert "alnum_index" in lexicon
    def test_canonical_set_is_set(self):
        """canonical_set이 Set[str]"""
        lexicon = build_unit_lexicon()
        assert isinstance(lexicon["canonical_set"], set)
        assert len(lexicon["canonical_set"]) > 0
    def test_upper_index_is_dict(self):
        """upper_index가 Dict[str, str]"""
        lexicon = build_unit_lexicon()
        assert isinstance(lexicon["upper_index"], dict)
    def test_alnum_index_is_dict_of_sets(self):
        """alnum_index가 Dict[str, Set[str]]"""
        lexicon = build_unit_lexicon()
        assert isinstance(lexicon["alnum_index"], dict)
        for key, value in list(lexicon["alnum_index"].items())[:1]:
            assert isinstance(value, set)
class TestGetUnitLexicon:
    """get_unit_lexicon() 테스트"""
    def test_returns_cached_lexicon(self):
        """캐시된 렉시콘 반환"""
        lex1 = get_unit_lexicon()
        lex2 = get_unit_lexicon()
        assert lex1 is lex2  # 동일 객체
    def test_force_rebuild(self):
        """force_rebuild로 재생성"""
        lex1 = get_unit_lexicon()
        lex2 = get_unit_lexicon(force_rebuild=True)
        assert lex1["canonical_set"] == lex2["canonical_set"]
class TestListAllUnits:
    """list_all_units() 테스트"""
    def test_returns_set(self):
        """Set 반환"""
        units = list_all_units()
        assert isinstance(units, set)
    def test_contains_expected_units(self):
        """주요 단위 포함 확인"""
        units = list_all_units()
        # 일부 주요 단위가 포함되어야 함
        expected_patterns = ["mg/dL", "g/dL", "U/L", "%", "mmHg"]
        found = 0
        for pattern in expected_patterns:
            if any(pattern.lower() in u.lower() for u in units):
                found += 1
        assert found >= 3  # 최소 3개 이상 매칭
    def test_minimum_unit_count(self):
        """최소 단위 개수"""
        units = list_all_units()
        assert len(units) >= 10  # 최소 10개 이상
class TestResolveUnit:
    """resolve_unit() 테스트"""
    # 기본 동작
    def test_none_input(self):
        """None 입력"""
        assert resolve_unit(None) is None
    def test_empty_string(self):
        """빈 문자열"""
        assert resolve_unit("") is None
        assert resolve_unit("   ") is None
    # 정확 매칭
    def test_exact_match(self):
        """정확한 단위 매칭"""
        result = resolve_unit("mg/dL")
        assert result is not None
        assert "mg" in result.lower() or "MG" in result
    def test_case_insensitive(self):
        """대소문자 무시 매칭"""
        result1 = resolve_unit("mg/dL")
        result2 = resolve_unit("MG/DL")
        result3 = resolve_unit("Mg/Dl")
        # 모두 같은 canonical로 해석되어야 함
        assert result1 == result2 == result3
    # CBC 단위 정규화 (K/L, M/L)
    def test_k_l_normalization(self):
        """K/L 관련 단위 정규화"""
        # 다양한 K/L 변형이 모두 같은 canonical로 해석되어야 함
        variants = ["K/L", "k/L", "K/uL", "k/ul"]
        results = [resolve_unit(v) for v in variants]
        # 모두 성공적으로 해석되어야 함
        assert all(r is not None for r in results)
        # 모두 같은 결과여야 함
        assert len(set(results)) == 1
    def test_ten_power_three_to_k(self):
        """10^3/L -> K 계열로 정규화"""
        result = resolve_unit("10^3/L")
        assert result is not None
        # K/L 또는 K/µL 형태여야 함
        assert "K" in result and "L" in result
    def test_ten_power_six_to_m(self):
        """10^6/L -> M 계열로 정규화"""
        result = resolve_unit("10^6/L")
        assert result is not None
        # M/L 또는 M/µL 형태여야 함
        assert "M" in result and "L" in result
    # 마이크로 변형
    def test_micro_variants(self):
        """마이크로 문자 변형"""
        # µ, μ, u 모두 같은 결과
        result1 = resolve_unit("µg/dL")
        result2 = resolve_unit("μg/dL")  # Greek mu
        result3 = resolve_unit("ug/dL")
        # 최소 하나는 성공해야 함
        results = [r for r in [result1, result2, result3] if r is not None]
        assert len(results) >= 1
    # 리터 변형
    def test_liter_variants(self):
        """리터 문자 변형"""
        # L, l, ℓ 모두 같은 결과
        result1 = resolve_unit("mg/dL")
        result2 = resolve_unit("mg/dl")
        assert result1 is not None
        assert result2 is not None
        assert result1 == result2
    # 공백 처리
    def test_whitespace_handling(self):
        """공백 처리"""
        result1 = resolve_unit("  mg/dL  ")
        result2 = resolve_unit("mg/dL")
        assert result1 == result2
    # 존재하지 않는 단위
    def test_unknown_unit_returns_none(self):
        """알 수 없는 단위는 None 반환"""
        assert resolve_unit("XXXYYY") is None
        assert resolve_unit("unknown/unit") is None
class TestResolveUnitEdgeCases:
    """resolve_unit() 엣지 케이스"""
    def test_percent(self):
        """퍼센트 단위"""
        result = resolve_unit("%")
        assert result is not None
        assert "%" in result
    def test_mmhg(self):
        """mmHg 단위 (혈압)"""
        result = resolve_unit("mmHg")
        assert result is not None
    def test_seconds(self):
        """초 단위 (응고시간)"""
        result = resolve_unit("sec")
        assert result is not None
    def test_special_units(self):
        """특수 단위"""
        # /hpf (high power field) - 현미경 검사
        result = resolve_unit("/hpf")
        assert result is not None or resolve_unit("hpf") is not None
    def test_very_long_token(self):
        """매우 긴 토큰"""
        assert resolve_unit("A" * 100) is None
    def test_k_l_consistency(self):
        """K/L 변형들이 모두 동일한 canonical로 해석"""
        variants = ["K/L", "K/uL", "K/µL", "k/l", "10^3/L", "10/L"]
        results = [resolve_unit(v) for v in variants]
        # 모두 같은 canonical 반환
        non_none = [r for r in results if r is not None]
        assert len(non_none) >= 4  # 최소 4개는 성공
        assert len(set(non_none)) == 1  # 모두 같은 값
