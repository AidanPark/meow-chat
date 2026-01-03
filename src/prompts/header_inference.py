"""
헤더 추론용 프롬프트.

테이블 헤더 컬럼 역할(name/result/unit/reference/min/max)을 추론할 때 사용하는 LLM 프롬프트.
"""

HEADER_INFERENCE_SYSTEM_PROMPT = """You are an expert at labeling table columns in veterinary lab reports.
Given sample rows (array of token arrays), infer column roles among: name, result, unit, reference, min, max.
Return a single JSON object mapping each role to an object with fields: {label:'llm', hits:['llm'], col_index:<int>, tokens:[], confidence:0.9, meets_threshold:true}.

Rules:
- name is the first column with test codes (e.g., WBC, RBC, HGB)
- result is numeric values (may include H/L/N/High/Low/Normal suffix)
- unit is measurement units (e.g., 10^9/L, g/dL, mg/dL)
- reference is a range (a-b format, e.g., "5.0-10.0")
- If the document splits the range into two separate columns, use min and max instead of reference

Important:
- Choose either 'reference' OR ('min' and 'max'); never output both forms at the same time
- Do not assign the same column index to multiple roles
- Output only the JSON object with no extra text"""


HEADER_INFERENCE_USER_TEMPLATE = """Sample rows from the table body:
{sample_rows}

Notes:
- Pick exactly one index per applicable role
- Use reference OR (min and max), not both
- Avoid duplicate indices across roles"""


def format_header_inference_user_prompt(sample_rows: list) -> str:
    """헤더 추론용 user 프롬프트를 포맷팅합니다.

    Parameters
    ----------
    sample_rows : list
        테이블 바디의 샘플 행 리스트

    Returns
    -------
    str
        포맷팅된 user 프롬프트
    """
    import json

    sample_json = json.dumps({"sample_rows": sample_rows}, ensure_ascii=False, indent=2)

    return HEADER_INFERENCE_USER_TEMPLATE.format(
        sample_rows=sample_json
    )

