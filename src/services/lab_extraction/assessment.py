"""
Deterministic 판정 모듈 (Assessment)

이 모듈은 tests에서 assessments를 생성합니다.
LLM은 이 판정 결과를 설명만 하고, 판정 자체를 생성하지 않습니다.

MVP 정책 (docs/LAB_ANALYSIS_PROFESSIONALIZATION.md Phase 3):
- status: normal | abnormal | unknown
- direction: ↑ | ↓ | -
- severity: unknown (MVP에서는 고정)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class AssessmentStatus(Enum):
    """판정 상태"""
    NORMAL = "normal"
    ABNORMAL = "abnormal"
    UNKNOWN = "unknown"


class AssessmentDirection(Enum):
    """판정 방향"""
    UP = "↑"
    DOWN = "↓"
    NONE = "-"


class AssessmentSeverity(Enum):
    """중증도 (MVP에서는 unknown 고정)"""
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    UNKNOWN = "unknown"


@dataclass
class Assessment:
    """단일 검사 항목의 판정 결과"""

    code: str
    value: float
    unit: str
    reference_min: float
    reference_max: float
    status: AssessmentStatus
    direction: AssessmentDirection
    severity: AssessmentSeverity
    reason: str

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "code": self.code,
            "value": self.value,
            "unit": self.unit,
            "reference_min": self.reference_min,
            "reference_max": self.reference_max,
            "status": self.status.value,
            "direction": self.direction.value,
            "severity": self.severity.value,
            "reason": self.reason,
        }


def assess_single_test(test: dict) -> Assessment:
    """
    단일 검사 항목을 평가하여 Assessment를 반환합니다.

    Args:
        test: 검증된 test dict (code, value, unit, reference_min, reference_max)

    Returns:
        Assessment 객체
    """
    code = test.get("code", "")
    value = test.get("value")
    unit = test.get("unit", "")
    ref_min = test.get("reference_min")
    ref_max = test.get("reference_max")

    # 기본값
    status = AssessmentStatus.UNKNOWN
    direction = AssessmentDirection.NONE
    severity = AssessmentSeverity.UNKNOWN  # MVP에서는 항상 unknown
    reason = ""

    # value가 숫자가 아니면 unknown
    if not isinstance(value, (int, float)):
        reason = "value_not_numeric"
        return Assessment(
            code=code,
            value=0.0,
            unit=unit,
            reference_min=ref_min if isinstance(ref_min, (int, float)) else 0.0,
            reference_max=ref_max if isinstance(ref_max, (int, float)) else 0.0,
            status=status,
            direction=direction,
            severity=severity,
            reason=reason,
        )

    # reference range가 없으면 unknown
    if not isinstance(ref_min, (int, float)) or not isinstance(ref_max, (int, float)):
        reason = "reference_range_missing"
        return Assessment(
            code=code,
            value=float(value),
            unit=unit,
            reference_min=0.0,
            reference_max=0.0,
            status=AssessmentStatus.UNKNOWN,
            direction=AssessmentDirection.NONE,
            severity=severity,
            reason=reason,
        )

    ref_min_f = float(ref_min)
    ref_max_f = float(ref_max)
    value_f = float(value)

    # 판정 로직
    if value_f < ref_min_f:
        status = AssessmentStatus.ABNORMAL
        direction = AssessmentDirection.DOWN
        reason = f"below_reference_min ({value_f} < {ref_min_f})"
    elif value_f > ref_max_f:
        status = AssessmentStatus.ABNORMAL
        direction = AssessmentDirection.UP
        reason = f"above_reference_max ({value_f} > {ref_max_f})"
    else:
        status = AssessmentStatus.NORMAL
        direction = AssessmentDirection.NONE
        reason = f"within_reference_range ({ref_min_f} <= {value_f} <= {ref_max_f})"

    return Assessment(
        code=code,
        value=value_f,
        unit=unit,
        reference_min=ref_min_f,
        reference_max=ref_max_f,
        status=status,
        direction=direction,
        severity=severity,
        reason=reason,
    )


def assess_tests(tests: list[dict]) -> list[Assessment]:
    """
    여러 검사 항목을 평가하여 Assessment 리스트를 반환합니다.

    Args:
        tests: 검증된 test dict 리스트

    Returns:
        Assessment 객체 리스트
    """
    return [assess_single_test(t) for t in tests]


def assess_tests_to_dicts(tests: list[dict]) -> list[dict]:
    """
    여러 검사 항목을 평가하여 dict 리스트를 반환합니다.
    (JSON 직렬화에 편리)

    Args:
        tests: 검증된 test dict 리스트

    Returns:
        Assessment dict 리스트
    """
    return [a.to_dict() for a in assess_tests(tests)]


def create_assessed_payload(validated_docs: list[dict]) -> list[dict]:
    """
    검증된 문서 리스트에 assessments를 추가합니다.

    Args:
        validated_docs: validate_document()로 검증된 문서 리스트

    Returns:
        각 문서에 assessments 필드가 추가된 리스트
    """
    result = []
    for doc in validated_docs:
        tests = doc.get("tests", [])
        assessments = assess_tests_to_dicts(tests)

        new_doc = dict(doc)
        new_doc["assessments"] = assessments
        result.append(new_doc)

    return result

