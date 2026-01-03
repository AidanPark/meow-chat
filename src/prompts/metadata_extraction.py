"""
메타데이터 추출용 프롬프트.

Patient name (환자명/반려동물명) 추출 시 사용하는 LLM 프롬프트.
"""

PATIENT_NAME_SYSTEM_PROMPT = """You are an expert at extracting patient names from veterinary lab report headers.
Given a text block from the document header (before the test results table), extract ONLY the patient name (반려동물/환자 이름).

IMPORTANT RULES:
- Do NOT confuse patient_name (환자명/반려동물명) with client_name (보호자명/의뢰인명).
- Common labels for patient_name: 환자명, 환자, 반려동물, 동물명, pet, animal, name, patient.
- Common labels for client_name: 의뢰인, 보호자, owner, client.
- If you see both, return ONLY the patient name.
- If uncertain or only client_name is present, return empty string.
- Return ONLY the name itself (no labels, no extra text).
- If multiple candidates exist, prefer the one with typical pet name patterns.

Output format: plain text (just the name or empty string)"""


PATIENT_NAME_USER_TEMPLATE = """Header text:
{header_text}
{client_note}"""


def format_patient_name_user_prompt(header_text: str, client_name: str | None = None) -> str:
    """patient_name 추출용 user 프롬프트를 포맷팅합니다.

    Parameters
    ----------
    header_text : str
        헤더 영역 텍스트 블록
    client_name : str | None
        이미 추출된 client_name (혼동 방지용)

    Returns
    -------
    str
        포맷팅된 user 프롬프트
    """
    client_note = ""
    if client_name:
        client_note = f"\nNote: client_name (보호자명) is already known as '{client_name}'. Do NOT return this value."

    return PATIENT_NAME_USER_TEMPLATE.format(
        header_text=header_text,
        client_note=client_note
    )
