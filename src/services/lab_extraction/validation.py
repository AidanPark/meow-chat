"""
LLM payload 검증/필터링 모듈 (Quality Gate)

이 모듈은 Step 13 final_doc의 tests를 LLM에 보내기 전에 필터링합니다.

MVP 정책 (docs/LAB_ANALYSIS_PROFESSIONALIZATION.md 8.1절):
- tests 포함 조건:
  - code가 비어있지 않음
  - value가 숫자
  - unit이 존재하며 UNKNOWN/빈 문자열이 아님
  - reference_min과 reference_max가 둘 다 숫자
- tests 제외 조건:
  - unit이 None/빈 문자열/UNKNOWN이면 제외
  - reference_min 또는 reference_max가 누락되면 제외
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationResult:
    """Quality gate 검증 결과"""

    accepted_tests: list[dict] = field(default_factory=list)
    rejected_tests: list[dict] = field(default_factory=list)

    @property
    def accepted_count(self) -> int:
        return len(self.accepted_tests)

    @property
    def rejected_count(self) -> int:
        return len(self.rejected_tests)

    @property
    def total_count(self) -> int:
        return self.accepted_count + self.rejected_count

    def summary(self) -> dict:
        """QA 요약 반환"""
        return {
            "total": self.total_count,
            "accepted": self.accepted_count,
            "rejected": self.rejected_count,
        }


def is_valid_unit(unit: Any) -> bool:
    """unit이 유효한지 검증 (None/빈값/UNKNOWN이면 False)"""
    if unit is None:
        return False
    if not isinstance(unit, str):
        return False
    s = unit.strip().upper()
    return s != "" and s != "UNKNOWN"


def is_valid_number(val: Any) -> bool:
    """숫자로 유효한지 검증"""
    if val is None:
        return False
    if isinstance(val, (int, float)):
        return True
    if isinstance(val, str):
        try:
            float(val.replace(",", "."))
            return True
        except ValueError:
            return False
    return False


def coerce_to_float(val: Any) -> float | None:
    """숫자로 변환, 불가하면 None"""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val.replace(",", "."))
        except ValueError:
            return None
    return None


def coerce_to_str_or_none(val: Any) -> str | None:
    """문자열로 변환, 빈값이면 None"""
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def validate_tests(tests: list[dict]) -> ValidationResult:
    """
    tests 리스트를 검증하여 accepted/rejected로 분리합니다.

    Args:
        tests: Step 13 final_doc의 tests 리스트

    Returns:
        ValidationResult: accepted_tests, rejected_tests 포함
    """
    result = ValidationResult()

    for t in tests:
        code = coerce_to_str_or_none(t.get("code"))
        value = coerce_to_float(t.get("value"))
        unit = t.get("unit")
        ref_min = coerce_to_float(t.get("reference_min"))
        ref_max = coerce_to_float(t.get("reference_max"))

        # 제외 사유 수집
        rejection_reasons = []

        if not code:
            rejection_reasons.append("missing_code")
        if value is None:
            rejection_reasons.append("invalid_value")
        if not is_valid_unit(unit):
            rejection_reasons.append("invalid_unit")
        if ref_min is None:
            rejection_reasons.append("missing_reference_min")
        if ref_max is None:
            rejection_reasons.append("missing_reference_max")

        if rejection_reasons:
            # 제외
            rejected_entry = dict(t)
            rejected_entry["_rejection_reasons"] = rejection_reasons
            result.rejected_tests.append(rejected_entry)
        else:
            # 포함: 정규화된 형태로 추가
            result.accepted_tests.append({
                "code": code,
                "value": value,
                "unit": unit.strip() if isinstance(unit, str) else unit,
                "reference_min": ref_min,
                "reference_max": ref_max,
            })

    return result


def validate_document(doc: dict) -> dict:
    """
    단일 문서(doc)를 검증하여 accepted tests만 포함한 문서 반환.

    Args:
        doc: Step 13 final_doc 형태의 문서

    Returns:
        검증된 문서 (tests는 accepted만 포함)
    """
    raw_tests = doc.get("tests", []) if doc else []
    validation = validate_tests(raw_tests)

    return {
        "hospital_name": coerce_to_str_or_none(doc.get("hospital_name")) if doc else None,
        "client_name": coerce_to_str_or_none(doc.get("client_name")) if doc else None,
        "patient_name": coerce_to_str_or_none(doc.get("patient_name")) if doc else None,
        "inspection_date": coerce_to_str_or_none(doc.get("inspection_date")) if doc else None,
        "tests": validation.accepted_tests,
        "_validation_summary": validation.summary(),
    }


def create_llm_payload(docs: list[dict]) -> list[dict]:
    """
    여러 문서를 받아 LLM payload(문서 배열)를 생성합니다.

    Args:
        docs: Step 13 final_doc 형태의 문서 리스트

    Returns:
        LLM에 전달할 문서 배열 (각 문서는 validated)
    """
    return [validate_document(d) for d in docs]

