"""
LLM payload validation 모듈 테스트

docs/LAB_ANALYSIS_PROFESSIONALIZATION.md Phase 2에 따른 테스트.
"""

import pytest

from src.services.lab_extraction.validation import (
    is_valid_unit,
    is_valid_number,
    coerce_to_float,
    coerce_to_str_or_none,
    validate_tests,
    validate_document,
    create_llm_payload,
    ValidationResult,
)


class TestIsValidUnit:
    """unit 유효성 검증 테스트"""

    def test_none_is_invalid(self):
        assert is_valid_unit(None) is False

    def test_empty_string_is_invalid(self):
        assert is_valid_unit("") is False
        assert is_valid_unit("   ") is False

    def test_unknown_is_invalid(self):
        assert is_valid_unit("UNKNOWN") is False
        assert is_valid_unit("unknown") is False
        assert is_valid_unit("Unknown") is False

    def test_valid_units(self):
        assert is_valid_unit("M/µL") is True
        assert is_valid_unit("%") is True
        assert is_valid_unit("g/dL") is True
        assert is_valid_unit("mmol/L") is True


class TestIsValidNumber:
    """숫자 유효성 검증 테스트"""

    def test_none_is_invalid(self):
        assert is_valid_number(None) is False

    def test_int_is_valid(self):
        assert is_valid_number(42) is True
        assert is_valid_number(0) is True
        assert is_valid_number(-5) is True

    def test_float_is_valid(self):
        assert is_valid_number(3.14) is True
        assert is_valid_number(0.0) is True

    def test_numeric_string_is_valid(self):
        assert is_valid_number("6.79") is True
        assert is_valid_number("6,79") is True  # 유럽식 소수점
        assert is_valid_number("-3.5") is True

    def test_non_numeric_string_is_invalid(self):
        assert is_valid_number("abc") is False
        assert is_valid_number("UNKNOWN") is False


class TestCoerceToFloat:
    """float 변환 테스트"""

    def test_none_returns_none(self):
        assert coerce_to_float(None) is None

    def test_int_converts(self):
        assert coerce_to_float(42) == 42.0

    def test_float_passes_through(self):
        assert coerce_to_float(3.14) == 3.14

    def test_string_converts(self):
        assert coerce_to_float("6.79") == 6.79
        assert coerce_to_float("6,79") == 6.79

    def test_invalid_string_returns_none(self):
        assert coerce_to_float("abc") is None


class TestValidateTests:
    """tests 리스트 검증 테스트"""

    def test_empty_list(self):
        result = validate_tests([])
        assert result.accepted_count == 0
        assert result.rejected_count == 0

    def test_valid_test_accepted(self):
        tests = [{
            "code": "RBC",
            "value": 6.79,
            "unit": "M/µL",
            "reference_min": 6.54,
            "reference_max": 12.2,
        }]
        result = validate_tests(tests)
        assert result.accepted_count == 1
        assert result.rejected_count == 0
        assert result.accepted_tests[0]["code"] == "RBC"

    def test_missing_code_rejected(self):
        tests = [{
            "code": None,
            "value": 6.79,
            "unit": "M/µL",
            "reference_min": 6.54,
            "reference_max": 12.2,
        }]
        result = validate_tests(tests)
        assert result.accepted_count == 0
        assert result.rejected_count == 1
        assert "missing_code" in result.rejected_tests[0]["_rejection_reasons"]

    def test_invalid_value_rejected(self):
        tests = [{
            "code": "RBC",
            "value": None,
            "unit": "M/µL",
            "reference_min": 6.54,
            "reference_max": 12.2,
        }]
        result = validate_tests(tests)
        assert result.accepted_count == 0
        assert result.rejected_count == 1
        assert "invalid_value" in result.rejected_tests[0]["_rejection_reasons"]

    def test_unknown_unit_rejected(self):
        tests = [{
            "code": "RBC",
            "value": 6.79,
            "unit": "UNKNOWN",
            "reference_min": 6.54,
            "reference_max": 12.2,
        }]
        result = validate_tests(tests)
        assert result.accepted_count == 0
        assert result.rejected_count == 1
        assert "invalid_unit" in result.rejected_tests[0]["_rejection_reasons"]

    def test_missing_reference_min_rejected(self):
        tests = [{
            "code": "RBC",
            "value": 6.79,
            "unit": "M/µL",
            "reference_min": None,
            "reference_max": 12.2,
        }]
        result = validate_tests(tests)
        assert result.accepted_count == 0
        assert result.rejected_count == 1
        assert "missing_reference_min" in result.rejected_tests[0]["_rejection_reasons"]

    def test_missing_reference_max_rejected(self):
        tests = [{
            "code": "RBC",
            "value": 6.79,
            "unit": "M/µL",
            "reference_min": 6.54,
            "reference_max": None,
        }]
        result = validate_tests(tests)
        assert result.accepted_count == 0
        assert result.rejected_count == 1
        assert "missing_reference_max" in result.rejected_tests[0]["_rejection_reasons"]

    def test_mixed_valid_and_invalid(self):
        tests = [
            {
                "code": "RBC",
                "value": 6.79,
                "unit": "M/µL",
                "reference_min": 6.54,
                "reference_max": 12.2,
            },
            {
                "code": "WBC",
                "value": None,  # invalid
                "unit": "K/µL",
                "reference_min": 5.0,
                "reference_max": 15.0,
            },
            {
                "code": "HCT",
                "value": 45.0,
                "unit": "UNKNOWN",  # invalid
                "reference_min": 30.0,
                "reference_max": 50.0,
            },
        ]
        result = validate_tests(tests)
        assert result.accepted_count == 1
        assert result.rejected_count == 2
        assert result.accepted_tests[0]["code"] == "RBC"


class TestValidateDocument:
    """문서 검증 테스트"""

    def test_document_with_valid_tests(self):
        doc = {
            "hospital_name": "테스트 동물병원",
            "patient_name": "냥이",
            "inspection_date": "2026-01-03",
            "tests": [{
                "code": "RBC",
                "value": 6.79,
                "unit": "M/µL",
                "reference_min": 6.54,
                "reference_max": 12.2,
            }]
        }
        result = validate_document(doc)
        assert result["hospital_name"] == "테스트 동물병원"
        assert result["patient_name"] == "냥이"
        assert len(result["tests"]) == 1
        assert result["_validation_summary"]["accepted"] == 1

    def test_empty_document(self):
        result = validate_document({})
        assert result["tests"] == []
        assert result["_validation_summary"]["total"] == 0


class TestCreateLlmPayload:
    """LLM payload 생성 테스트"""

    def test_single_document(self):
        docs = [{
            "hospital_name": "병원A",
            "tests": [{
                "code": "RBC",
                "value": 6.79,
                "unit": "M/µL",
                "reference_min": 6.54,
                "reference_max": 12.2,
            }]
        }]
        payload = create_llm_payload(docs)
        assert len(payload) == 1
        assert payload[0]["hospital_name"] == "병원A"
        assert len(payload[0]["tests"]) == 1

    def test_multiple_documents(self):
        docs = [
            {"hospital_name": "병원A", "tests": []},
            {"hospital_name": "병원B", "tests": []},
        ]
        payload = create_llm_payload(docs)
        assert len(payload) == 2

