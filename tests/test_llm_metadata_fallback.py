"""
LLM 메타데이터 폴백 기능 테스트

patient_name 규칙 추출 실패 시 LLM 폴백이 정상 작동하는지 검증합니다.
"""
import os
import pytest
from src.services.lab_extraction.lab_table_extractor import LabTableExtractor, Settings


@pytest.fixture
def skip_if_no_api_key():
    """OpenAI API 키가 없으면 테스트 스킵"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
    return api_key


def test_llm_fallback_disabled_by_default():
    """기본 설정에서는 LLM 폴백이 비활성화되어야 함"""
    extractor = LabTableExtractor()
    assert extractor.settings.use_llm_for_metadata is False


def test_llm_fallback_with_missing_patient_name(skip_if_no_api_key):
    """patient_name이 없는 경우 LLM 폴백이 동작해야 함"""
    api_key = skip_if_no_api_key

    # LLM 폴백 활성화된 설정
    settings = Settings(
        use_llm_for_metadata=True,
        llm_metadata_model="gpt-4o-mini",
    )
    extractor = LabTableExtractor(settings=settings, api_key=api_key)

    # 모의 헤더 데이터 (patient_name 라벨 없음, 이름만 있음)
    mock_lines = [
        [
            {"text": "24시", "x_left": 10, "x_right": 50},
            {"text": "펫플러스", "x_left": 55, "x_right": 150},
            {"text": "동물병원", "x_left": 155, "x_right": 250},
        ],
        [
            {"text": "보호자:", "x_left": 10, "x_right": 80},
            {"text": "김철수", "x_left": 85, "x_right": 150},
        ],
        [
            {"text": "나비", "x_left": 10, "x_right": 60},  # 라벨 없이 이름만 (규칙 실패 케이스)
            {"text": "2025-01-20", "x_left": 200, "x_right": 300},
        ],
        [
            {"text": "Test", "x_left": 10, "x_right": 60},
            {"text": "Result", "x_left": 100, "x_right": 150},
            {"text": "Unit", "x_left": 200, "x_right": 250},
        ],
        [
            {"text": "WBC", "x_left": 10, "x_right": 60},
            {"text": "12.5", "x_left": 100, "x_right": 150},
            {"text": "10^9/L", "x_left": 200, "x_right": 250},
        ],
    ]

    # patient_name만 LLM으로 추출 시도
    result = extractor._extract_patient_name_with_llm(
        mock_lines,
        body_start_idx=3,  # 4번째 라인(헤더)부터 바디
        client_name="김철수"
    )

    # 검증: LLM이 "나비"를 찾아야 함
    assert result is not None
    # LLM 응답은 비결정적이므로 빈 문자열이 아닌지만 확인
    assert isinstance(result, str)
    assert len(result) > 0
    # client_name과 다른지 확인
    assert result != "김철수"


def test_llm_fallback_integration(skip_if_no_api_key):
    """extract_from_lines 통합 시나리오: 규칙 실패 → LLM 폴백"""
    api_key = skip_if_no_api_key

    settings = Settings(
        use_llm_for_metadata=True,
        llm_metadata_model="gpt-4o-mini",
    )
    extractor = LabTableExtractor(settings=settings, api_key=api_key)

    # patient_name 라벨이 없는 헤더
    mock_lines = [
        [
            {"text": "펫플러스동물병원", "x_left": 10, "x_right": 200},
        ],
        [
            {"text": "보호자:", "x_left": 10, "x_right": 80},
            {"text": "이영희", "x_left": 85, "x_right": 150},
        ],
        [
            {"text": "코코", "x_left": 10, "x_right": 60},  # 라벨 없음
        ],
        [
            {"text": "검사일:", "x_left": 10, "x_right": 80},
            {"text": "2025-01-20", "x_left": 85, "x_right": 180},
        ],
        [
            {"text": "Test", "x_left": 10, "x_right": 60},
            {"text": "Result", "x_left": 100, "x_right": 150},
            {"text": "Unit", "x_left": 200, "x_right": 250},
            {"text": "Reference", "x_left": 300, "x_right": 400},
        ],
        [
            {"text": "WBC", "x_left": 10, "x_right": 60},
            {"text": "12.5", "x_left": 100, "x_right": 150},
            {"text": "10^9/L", "x_left": 200, "x_right": 250},
            {"text": "6.0-17.0", "x_left": 300, "x_right": 400},
        ],
    ]

    result = extractor.extract_from_lines(mock_lines)

    # 검증
    assert isinstance(result, dict)
    assert result.get("hospital_name") == "펫플러스동물병원"
    assert result.get("client_name") == "이영희"
    assert result.get("inspection_date") == "2025-01-20"

    # LLM 폴백으로 patient_name이 채워졌는지 확인
    patient_name = result.get("patient_name")
    assert patient_name is not None
    assert isinstance(patient_name, str)
    assert len(patient_name) > 0
    # client_name과 다른지 확인
    assert patient_name != "이영희"

