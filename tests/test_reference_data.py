"""검사항목 참조 데이터 테스트
Step 1.1: reference_data.py 이전 검증
"""
import pytest
class TestReferenceDataImport:
    """import 및 기본 접근 테스트"""
    def test_import_reference_tests(self):
        """REFERENCE_TESTS를 import할 수 있어야 함"""
        from src.services.lab_extraction.reference.reference_data import REFERENCE_TESTS
        assert REFERENCE_TESTS is not None
    def test_import_from_package(self):
        """패키지 레벨에서 import할 수 있어야 함"""
        from src.services.lab_extraction.reference import REFERENCE_TESTS
        assert REFERENCE_TESTS is not None
class TestReferenceDataStructure:
    """데이터 구조 검증 테스트"""
    def test_reference_tests_is_list(self):
        """REFERENCE_TESTS는 리스트여야 함"""
        from src.services.lab_extraction.reference.reference_data import REFERENCE_TESTS
        assert isinstance(REFERENCE_TESTS, list)
    def test_reference_tests_not_empty(self):
        """REFERENCE_TESTS는 비어있지 않아야 함"""
        from src.services.lab_extraction.reference.reference_data import REFERENCE_TESTS
        assert len(REFERENCE_TESTS) > 0
    def test_reference_tests_minimum_count(self):
        """최소 100개 이상의 검사항목이 있어야 함"""
        from src.services.lab_extraction.reference.reference_data import REFERENCE_TESTS
        assert len(REFERENCE_TESTS) >= 100
class TestReferenceDataFields:
    """필수 필드 검증 테스트"""
    def test_all_items_have_code(self):
        """모든 항목에 code 필드가 있어야 함"""
        from src.services.lab_extraction.reference.reference_data import REFERENCE_TESTS
        for item in REFERENCE_TESTS:
            assert "code" in item, f"code 필드 누락: {item}"
            assert isinstance(item["code"], str), f"code는 문자열이어야 함: {item}"
            assert len(item["code"]) > 0, f"code는 비어있으면 안됨: {item}"
    def test_all_items_have_name(self):
        """모든 항목에 name 필드가 있어야 함"""
        from src.services.lab_extraction.reference.reference_data import REFERENCE_TESTS
        for item in REFERENCE_TESTS:
            assert "name" in item, f"name 필드 누락: {item}"
            assert isinstance(item["name"], str), f"name은 문자열이어야 함: {item}"
    def test_all_items_have_unit_field(self):
        """모든 항목에 unit 필드가 있어야 함 (None 허용)"""
        from src.services.lab_extraction.reference.reference_data import REFERENCE_TESTS
        for item in REFERENCE_TESTS:
            assert "unit" in item, f"unit 필드 누락: {item}"
            assert item["unit"] is None or isinstance(item["unit"], str), \
                f"unit은 None 또는 문자열이어야 함: {item}"
class TestReferenceDataCategories:
    """카테고리별 데이터 존재 검증"""
    def test_has_cbc_items(self):
        """CBC 관련 항목이 있어야 함"""
        from src.services.lab_extraction.reference.reference_data import REFERENCE_TESTS
        cbc_codes = {"WBC", "RBC", "HGB", "HCT", "PLT", "MCV", "MCH", "MCHC"}
        found_codes = {item["code"] for item in REFERENCE_TESTS}
        assert cbc_codes.issubset(found_codes), \
            f"누락된 CBC 코드: {cbc_codes - found_codes}"
    def test_has_chemistry_items(self):
        """생화학 검사 항목이 있어야 함"""
        from src.services.lab_extraction.reference.reference_data import REFERENCE_TESTS
        chem_codes = {"ALT", "AST", "BUN", "CRE", "GLU", "TP", "ALB"}
        found_codes = {item["code"] for item in REFERENCE_TESTS}
        assert chem_codes.issubset(found_codes), \
            f"누락된 생화학 코드: {chem_codes - found_codes}"
    def test_has_blood_gas_items(self):
        """혈액가스 분석 항목이 있어야 함"""
        from src.services.lab_extraction.reference.reference_data import REFERENCE_TESTS
        gas_codes = {"pH", "pCO2", "pO2", "HCO3"}
        found_codes = {item["code"] for item in REFERENCE_TESTS}
        assert gas_codes.issubset(found_codes), \
            f"누락된 혈액가스 코드: {gas_codes - found_codes}"
class TestReferenceDataSpecialCases:
    """특수 케이스 검증"""
    def test_sample_type_for_arterial_venous(self):
        """(Art)/(Ven) 코드는 sample_type 필드가 있어야 함"""
        from src.services.lab_extraction.reference.reference_data import REFERENCE_TESTS
        for item in REFERENCE_TESTS:
            code = item["code"]
            if "(Art)" in code or "(Ven)" in code:
                assert "sample_type" in item, \
                    f"sample_type 필드 누락: {code}"
    def test_no_excessive_duplicate_codes(self):
        """중복 코드가 너무 많으면 안됨 (90% 이상 고유)"""
        from src.services.lab_extraction.reference.reference_data import REFERENCE_TESTS
        codes = [item["code"] for item in REFERENCE_TESTS]
        unique_ratio = len(set(codes)) / len(codes)
        assert unique_ratio > 0.9, \
            f"중복 코드가 너무 많음: 고유 비율 {unique_ratio:.2%}"
