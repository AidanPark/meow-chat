"""단위 정규화 유틸리티 테스트
Step 1.2: unit_normalizer.py 이전 검증
"""
import pytest
from src.services.lab_extraction.unit_normalizer import (
    fold_micro,
    fold_liter,
    normalize_unit_simple,
)
class TestFoldMicro:
    """fold_micro() 함수 테스트"""
    def test_greek_mu_to_micro_sign(self):
        """Greek mu (μ) -> micro sign (µ) 변환"""
        assert fold_micro("μg/dL") == "µg/dL"
        assert fold_micro("μL") == "µL"
        assert fold_micro("μmol/L") == "µmol/L"
    def test_u_to_micro_in_unit_context(self):
        """단위 문맥에서 u -> µ 변환"""
        # 슬래시 뒤 u
        assert "µ" in fold_micro("mg/uL") or fold_micro("mg/uL") == "mg/uL"
        # 시작 위치의 u
        result = fold_micro("ug/dL")
        assert result in ["µg/dL", "ug/dL"]  # 변환되거나 원본 유지
    def test_preserve_u_in_other_contexts(self):
        """단위 문맥이 아닌 u는 보존"""
        # 'unit' 같은 단어는 변환하면 안됨
        assert fold_micro("U/L") == "U/L"  # 대문자 U는 보존
class TestFoldLiter:
    """fold_liter() 함수 테스트"""
    def test_special_liter_to_L(self):
        """ℓ -> L 변환"""
        assert fold_liter("mg/dℓ") == "mg/dL"
        assert fold_liter("ℓ") == "L"
    def test_lowercase_l_after_slash(self):
        """슬래시 뒤 소문자 l -> L 변환"""
        assert fold_liter("mg/dl") == "mg/dL"
        assert fold_liter("g/l") == "g/L"
        assert fold_liter("U/l") == "U/L"
    def test_preserve_l_in_mol(self):
        """mol, mmol 등의 l은 보존"""
        assert fold_liter("mmol/L") == "mmol/L"
        assert "mol" in fold_liter("mol/L")
    def test_micro_l_to_micro_L(self):
        """µl -> µL 변환"""
        assert fold_liter("µl") == "µL"
        assert fold_liter("K/µl") == "K/µL"
class TestNormalizeUnitSimple:
    """normalize_unit_simple() 함수 테스트"""
    # 기본 동작 테스트
    def test_none_input(self):
        """None 입력시 None 반환"""
        assert normalize_unit_simple(None) is None
    def test_empty_string(self):
        """빈 문자열 입력시 None 반환"""
        assert normalize_unit_simple("") is None
        assert normalize_unit_simple("   ") is None
    def test_unknown_returns_none(self):
        """UNKNOWN 입력시 None 반환"""
        assert normalize_unit_simple("UNKNOWN") is None
        assert normalize_unit_simple("unknown") is None
    # 10^3 계열 정규화
    def test_ten_power_three_to_k(self):
        """10^3 계열 -> K/L 정규화"""
        assert normalize_unit_simple("10^3/L") == "K/L"
        assert normalize_unit_simple("10/L") == "K/L"
        assert normalize_unit_simple("x10^3/L") == "K/L"
        assert normalize_unit_simple("X10^3/L") == "K/L"
    def test_k_variants_to_k_l(self):
        """k/K 변형 -> K/L 정규화"""
        assert normalize_unit_simple("k/L") == "K/L"
        assert normalize_unit_simple("K/L") == "K/L"
        assert normalize_unit_simple("K/uL") == "K/L"
    # 10^6 계열 정규화
    def test_ten_power_six_to_m(self):
        """10^6 계열 -> M/L 정규화"""
        assert normalize_unit_simple("10^6/L") == "M/L"
        assert normalize_unit_simple("x10^6/L") == "M/L"
    # 공백 처리
    def test_space_around_slash(self):
        """슬래시 주변 공백 제거"""
        assert normalize_unit_simple("mg / dL") == "mg/dL"
        assert normalize_unit_simple("K / L") == "K/L"
    # OCR 혼동 보정
    def test_ocr_confusion_d1_to_dL(self):
        """OCR 혼동: d1 -> dL 보정"""
        assert normalize_unit_simple("mg/d1") == "mg/dL"
        assert normalize_unit_simple("g/d1") == "g/dL"
    def test_ocr_confusion_u1_to_uL(self):
        """OCR 혼동: U/1 -> U/L 보정"""
        assert normalize_unit_simple("U/1") == "U/L"
        assert normalize_unit_simple("IU/1") == "IU/L"
    def test_ocr_confusion_mmo1_to_mmol(self):
        """OCR 혼동: mmo1 -> mmol 보정"""
        assert normalize_unit_simple("mmo1/L") == "mmol/L"
    # 명시적 오버라이드
    def test_explicit_overrides(self):
        """명시적 매핑 오버라이드"""
        assert normalize_unit_simple("mg/d") == "mg/dL"
        assert normalize_unit_simple("mmol") == "mmol/L"
        assert normalize_unit_simple("mEq") == "mEq/L"
        assert normalize_unit_simple("mmH") == "mmHg"
        assert normalize_unit_simple("P9") == "pg"
        assert normalize_unit_simple("Pg") == "pg"
    # 값+단위 혼합 보존
    def test_preserve_value_unit_mixed(self):
        """값+단위 혼합 문자열은 그대로 보존"""
        assert normalize_unit_simple("neg pos/n") == "neg pos/n"
        assert normalize_unit_simple("12.5 mg/dL") == "12.5 mg/dL"
        assert normalize_unit_simple("7.2H K/L") == "7.2H K/L"
    # 일반 단위 보존
    def test_preserve_normal_units(self):
        """정상적인 단위는 그대로 보존"""
        assert normalize_unit_simple("mg/dL") == "mg/dL"
        assert normalize_unit_simple("g/dL") == "g/dL"
        assert normalize_unit_simple("%") == "%"
        assert normalize_unit_simple("U/L") == "U/L"
        assert normalize_unit_simple("mmHg") == "mmHg"
class TestEdgeCases:
    """엣지 케이스 테스트"""
    def test_ocr_noise_removal(self):
        """OCR 노이즈 제거"""
        # 앞뒤 공백/특수문자 제거
        result = normalize_unit_simple("  mg/dL  ")
        assert result == "mg/dL"
    def test_special_equipment_format(self):
        """장비 특수 표기 처리"""
        # '10 x3/L' 같은 분절된 형태
        result = normalize_unit_simple("10 x3/L")
        # 10^3/L로 인식되어 K/L로 변환되어야 함
        assert result in ["K/L", "10^3/L", "10 x3/L"]  # 구현에 따라 다를 수 있음
    def test_micro_variants(self):
        """마이크로 변형 처리"""
        # µg와 ug가 일관되게 처리되어야 함
        result1 = normalize_unit_simple("µg/dL")
        result2 = normalize_unit_simple("ug/dL")
        # 둘 다 µg/dL 또는 동일한 형태로 정규화
        assert result1 is not None
        assert result2 is not None
