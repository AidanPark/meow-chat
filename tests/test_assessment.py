"""
Deterministic assessment 모듈 테스트

docs/LAB_ANALYSIS_PROFESSIONALIZATION.md Phase 3에 따른 테스트.
"""

import pytest

from src.services.lab_extraction.assessment import (
    AssessmentStatus,
    AssessmentDirection,
    AssessmentSeverity,
    Assessment,
    assess_single_test,
    assess_tests,
    assess_tests_to_dicts,
    create_assessed_payload,
)


class TestAssessmentEnums:
    """Enum 값 테스트"""

    def test_status_values(self):
        assert AssessmentStatus.NORMAL.value == "normal"
        assert AssessmentStatus.ABNORMAL.value == "abnormal"
        assert AssessmentStatus.UNKNOWN.value == "unknown"

    def test_direction_values(self):
        assert AssessmentDirection.UP.value == "↑"
        assert AssessmentDirection.DOWN.value == "↓"
        assert AssessmentDirection.NONE.value == "-"

    def test_severity_values(self):
        assert AssessmentSeverity.MILD.value == "mild"
        assert AssessmentSeverity.MODERATE.value == "moderate"
        assert AssessmentSeverity.SEVERE.value == "severe"
        assert AssessmentSeverity.UNKNOWN.value == "unknown"


class TestAssessmentToDict:
    """Assessment.to_dict() 테스트"""

    def test_to_dict(self):
        a = Assessment(
            code="RBC",
            value=6.79,
            unit="M/µL",
            reference_min=6.54,
            reference_max=12.2,
            status=AssessmentStatus.NORMAL,
            direction=AssessmentDirection.NONE,
            severity=AssessmentSeverity.UNKNOWN,
            reason="within_reference_range",
        )
        d = a.to_dict()
        assert d["code"] == "RBC"
        assert d["status"] == "normal"
        assert d["direction"] == "-"
        assert d["severity"] == "unknown"


class TestAssessSingleTest:
    """단일 test 평가 테스트"""

    def test_normal_within_range(self):
        """값이 정상 범위 내: status=normal, direction=-"""
        test = {
            "code": "RBC",
            "value": 8.0,
            "unit": "M/µL",
            "reference_min": 6.54,
            "reference_max": 12.2,
        }
        a = assess_single_test(test)
        assert a.status == AssessmentStatus.NORMAL
        assert a.direction == AssessmentDirection.NONE
        assert a.severity == AssessmentSeverity.UNKNOWN
        assert "within_reference_range" in a.reason

    def test_abnormal_above_max(self):
        """값이 최대값 초과: status=abnormal, direction=↑"""
        test = {
            "code": "WBC",
            "value": 20.0,
            "unit": "K/µL",
            "reference_min": 5.0,
            "reference_max": 15.0,
        }
        a = assess_single_test(test)
        assert a.status == AssessmentStatus.ABNORMAL
        assert a.direction == AssessmentDirection.UP
        assert "above_reference_max" in a.reason

    def test_abnormal_below_min(self):
        """값이 최소값 미만: status=abnormal, direction=↓"""
        test = {
            "code": "HCT",
            "value": 25.0,
            "unit": "%",
            "reference_min": 30.0,
            "reference_max": 50.0,
        }
        a = assess_single_test(test)
        assert a.status == AssessmentStatus.ABNORMAL
        assert a.direction == AssessmentDirection.DOWN
        assert "below_reference_min" in a.reason

    def test_boundary_at_min(self):
        """값이 정확히 최소값: 정상 처리"""
        test = {
            "code": "RBC",
            "value": 6.54,
            "unit": "M/µL",
            "reference_min": 6.54,
            "reference_max": 12.2,
        }
        a = assess_single_test(test)
        assert a.status == AssessmentStatus.NORMAL
        assert a.direction == AssessmentDirection.NONE

    def test_boundary_at_max(self):
        """값이 정확히 최대값: 정상 처리"""
        test = {
            "code": "RBC",
            "value": 12.2,
            "unit": "M/µL",
            "reference_min": 6.54,
            "reference_max": 12.2,
        }
        a = assess_single_test(test)
        assert a.status == AssessmentStatus.NORMAL
        assert a.direction == AssessmentDirection.NONE

    def test_missing_reference_range(self):
        """reference range 누락: status=unknown"""
        test = {
            "code": "RBC",
            "value": 8.0,
            "unit": "M/µL",
            "reference_min": None,
            "reference_max": None,
        }
        a = assess_single_test(test)
        assert a.status == AssessmentStatus.UNKNOWN
        assert a.direction == AssessmentDirection.NONE
        assert "reference_range_missing" in a.reason

    def test_value_not_numeric(self):
        """value가 숫자가 아닐 때: status=unknown"""
        test = {
            "code": "RBC",
            "value": None,
            "unit": "M/µL",
            "reference_min": 6.54,
            "reference_max": 12.2,
        }
        a = assess_single_test(test)
        assert a.status == AssessmentStatus.UNKNOWN
        assert "value_not_numeric" in a.reason


class TestAssessTests:
    """여러 tests 평가 테스트"""

    def test_empty_list(self):
        result = assess_tests([])
        assert result == []

    def test_multiple_tests(self):
        tests = [
            {"code": "RBC", "value": 8.0, "unit": "M/µL", "reference_min": 6.54, "reference_max": 12.2},
            {"code": "WBC", "value": 20.0, "unit": "K/µL", "reference_min": 5.0, "reference_max": 15.0},
        ]
        result = assess_tests(tests)
        assert len(result) == 2
        assert result[0].status == AssessmentStatus.NORMAL
        assert result[1].status == AssessmentStatus.ABNORMAL


class TestAssessTestsToDicts:
    """dict 변환 테스트"""

    def test_returns_dicts(self):
        tests = [
            {"code": "RBC", "value": 8.0, "unit": "M/µL", "reference_min": 6.54, "reference_max": 12.2},
        ]
        result = assess_tests_to_dicts(tests)
        assert isinstance(result, list)
        assert isinstance(result[0], dict)
        assert result[0]["status"] == "normal"


class TestCreateAssessedPayload:
    """assessments가 추가된 payload 생성 테스트"""

    def test_adds_assessments_field(self):
        docs = [{
            "hospital_name": "테스트 병원",
            "tests": [
                {"code": "RBC", "value": 8.0, "unit": "M/µL", "reference_min": 6.54, "reference_max": 12.2},
            ]
        }]
        result = create_assessed_payload(docs)
        assert len(result) == 1
        assert "assessments" in result[0]
        assert len(result[0]["assessments"]) == 1
        assert result[0]["assessments"][0]["status"] == "normal"

    def test_preserves_original_fields(self):
        docs = [{
            "hospital_name": "테스트 병원",
            "patient_name": "냥이",
            "tests": [],
        }]
        result = create_assessed_payload(docs)
        assert result[0]["hospital_name"] == "테스트 병원"
        assert result[0]["patient_name"] == "냥이"


class TestDeterministicProperty:
    """같은 입력에 항상 같은 출력(결정론) 테스트"""

    def test_same_input_same_output(self):
        """동일 입력에 동일 출력 보장"""
        test = {
            "code": "RBC",
            "value": 8.0,
            "unit": "M/µL",
            "reference_min": 6.54,
            "reference_max": 12.2,
        }
        results = [assess_single_test(test) for _ in range(10)]

        # 모든 결과가 동일한지 확인
        first = results[0].to_dict()
        for r in results[1:]:
            assert r.to_dict() == first

