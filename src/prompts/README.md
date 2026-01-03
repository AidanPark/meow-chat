# Lab Extraction Prompts

검사지 추출 및 챗봇 응답에 사용되는 LLM 프롬프트를 중앙 관리하는 모듈입니다.

## 📂 구조

```
src/prompts/
├── __init__.py                    # 프롬프트 export
├── metadata_extraction.py         # patient_name 추출 프롬프트
├── header_inference.py            # 테이블 헤더 추론 프롬프트
├── chat.py                        # 스몰톡/일반 대화 프롬프트
├── lab_analysis.py                # 검사지 분석 프롬프트
├── intent_classification.py       # 의도 분류 프롬프트
└── README.md                      # 사용 가이드
```

## 🎯 설계 목적

### 1. **유지보수성 향상**
- 프롬프트를 코드에서 분리
- 프롬프트 수정 시 Python 코드 수정 불필요
- 버전 관리 용이

### 2. **재사용성**
- 여러 곳에서 동일한 프롬프트 import
- 중복 제거

### 3. **협업 편의성**
- 비개발자도 프롬프트 검토/수정 가능
- 프롬프트만 모아서 리뷰 가능

## 📝 사용법

### Import
```python
from src.prompts import (
    PATIENT_NAME_SYSTEM_PROMPT,
    HEADER_INFERENCE_SYSTEM_PROMPT,
)
from src.prompts.metadata_extraction import (
    format_patient_name_user_prompt
)
```

### 사용 예시

#### 1. Patient Name 추출
```python
# System prompt
system_prompt = PATIENT_NAME_SYSTEM_PROMPT

# User prompt 포맷팅
header_text = """
24시 펫플러스 동물병원
보호자: 김철수
나비
검사일: 2025-01-20
"""

user_prompt = format_patient_name_user_prompt(
    header_text=header_text,
    client_name="김철수"  # client_name과 혼동 방지
)

# LLM 호출
response = llm.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ],
    temperature=0,
)
```

#### 2. Header Inference
```python
from src.prompts.header_inference import (
    format_header_inference_user_prompt
)

# System prompt
system_prompt = HEADER_INFERENCE_SYSTEM_PROMPT

# User prompt 포맷팅
sample_rows = [
    ["WBC", "12.5", "10^9/L", "6.0-17.0"],
    ["RBC", "7.2", "10^12/L", "5.0-10.0"],
]

user_prompt = format_header_inference_user_prompt(sample_rows)

# LLM 호출
response = llm.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ],
    temperature=0,
    response_format={"type": "json_object"},
)
```

#### 3. Chat (스몰톡)
```python
from src.prompts import (
    CHAT_SYSTEM_PROMPT,
    EMERGENCY_SYSTEM_PROMPT,
)

# 일반 대화
system_prompt = CHAT_SYSTEM_PROMPT
user_input = "우리 고양이가 밥을 안 먹어요"

response = llm.chat.completions.create(
    model="gpt-5-mini",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ],
    temperature=0.7,
)

# 응급 상황 감지 시
system_prompt = EMERGENCY_SYSTEM_PROMPT
```

#### 4. Lab Analysis (검사지 분석)
```python
from src.prompts.lab_analysis import (
    LAB_ANALYSIS_SYSTEM_PROMPT,
    format_lab_analysis_user_prompt,
)

# System prompt
system_prompt = LAB_ANALYSIS_SYSTEM_PROMPT

# 검사 데이터 (JSON 형식)
document_context = """
{
  "hospital_name": "펫플러스동물병원",
  "patient_name": "나비",
  "inspection_date": "2025-01-20",
  "tests": [
    {"code": "WBC", "value": "12.5", "unit": "10^9/L", "reference_min": "6.0", "reference_max": "17.0"},
    {"code": "RBC", "value": "7.2", "unit": "10^12/L", "reference_min": "5.0", "reference_max": "10.0"}
  ]
}
"""

user_prompt = format_lab_analysis_user_prompt(
    document_context=document_context,
    user_question="간 수치가 걱정돼요"  # 옵션
)

response = llm.chat.completions.create(
    model="gpt-4.1",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ],
    temperature=0,
)
```

#### 5. Intent Classification (의도 분류)
```python
from src.prompts import INTENT_CLASSIFICATION_SYSTEM_PROMPT

# System prompt
system_prompt = INTENT_CLASSIFICATION_SYSTEM_PROMPT

# 사용자 입력
user_input = "혈액검사 결과 좀 봐줘"

response = llm.chat.completions.create(
    model="gpt-5-nano",  # 빠른 경량 모델
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ],
    temperature=0,
    max_tokens=100,
)

# 응답: {"intent": "lab_analysis", "confidence": 0.95}
```

## 🔧 프롬프트 수정 가이드

### 프롬프트 수정 시
1. 해당 모듈 파일 수정 (`metadata_extraction.py` 또는 `header_inference.py`)
2. 테스트 실행으로 검증
3. Git commit (프롬프트 변경 이력 추적)

### 새 프롬프트 추가 시
1. 새 모듈 파일 생성 (예: `quality_check.py`)
2. `__init__.py`에 export 추가
3. 사용처에서 import

## 📋 프롬프트 목록

### 1. metadata_extraction.py

#### PATIENT_NAME_SYSTEM_PROMPT
- **용도**: 검사지 헤더에서 patient_name(환자명/반려동물명) 추출
- **핵심 규칙**:
  - client_name(보호자명)과 혼동 금지
  - 확실하지 않으면 빈 문자열 반환
  - 라벨 제거 후 이름만 반환

#### format_patient_name_user_prompt()
- **용도**: patient_name 추출용 user 프롬프트 생성
- **파라미터**:
  - `header_text`: 헤더 텍스트 블록
  - `client_name`: 이미 추출된 client_name (옵션)

### 2. header_inference.py

#### HEADER_INFERENCE_SYSTEM_PROMPT
- **용도**: 테이블 컬럼 역할(name/result/unit/reference/min/max) 추론
- **핵심 규칙**:
  - reference 또는 (min, max) 중 하나만 사용
  - 중복 col_index 금지
  - JSON 형식 응답

#### format_header_inference_user_prompt()
- **용도**: 헤더 추론용 user 프롬프트 생성
- **파라미터**:
  - `sample_rows`: 테이블 바디 샘플 행 리스트

### 3. chat.py

#### CHAT_SYSTEM_PROMPT
- **용도**: 스몰톡/일반 대화 응답 생성
- **핵심 규칙**:
  - 친근하고 공감적인 톤
  - 직접 진단/처방 금지
  - 응급 상황 시 병원 방문 권유

#### EMERGENCY_SYSTEM_PROMPT
- **용도**: 응급 상황 감지 시 사용
- **핵심 규칙**:
  - 즉시 동물병원 방문 강력 권유
  - 절대 진단/처방 금지
  - 24시간 동물병원 안내

### 4. lab_analysis.py

#### LAB_ANALYSIS_SYSTEM_PROMPT
- **용도**: OCR 추출된 검사 결과 분석 및 설명
- **출력 형식**:
  1. 데이터프레임 표 (항목/값/단위/참고범위/정상여부/방향/중증도)
  2. 종합 임상 판단과 소견
- **핵심 규칙**:
  - 절대 진단/처방 금지
  - 응급 징후 시 즉시 병원 권유
  - 불확실성 명시
  - "참고용" 안내 필수

#### format_lab_analysis_user_prompt()
- **용도**: 검사지 분석용 user 프롬프트 생성
- **파라미터**:
  - `document_context`: OCR 추출 데이터
  - `user_question`: 사용자 추가 질문 (옵션)

### 5. intent_classification.py

#### INTENT_CLASSIFICATION_SYSTEM_PROMPT
- **용도**: 사용자 입력의 의도를 6가지로 분류
- **의도 유형**:
  1. `lab_analysis`: 검사지/검진 결과 분석 요청
  2. `health_question`: 건강 관련 일반 질문
  3. `emergency`: 응급 상황
  4. `upload_help`: 업로드 방법 문의
  5. `smalltalk`: 일반 대화, 인사, 잡담
  6. `other`: 기타/분류 불가
- **응답 형식**: JSON `{"intent": "유형", "confidence": 0.0-1.0}`

## 🎨 프롬프트 작성 가이드라인

### 1. 명확한 역할 정의
```python
SYSTEM_PROMPT = """You are an expert at [구체적 역할].
Given [입력 형식], [수행 작업].
"""
```

### 2. IMPORTANT RULES 섹션
- 혼동하기 쉬운 개념 명시
- 엣지 케이스 처리 방법
- 출력 형식 명시

### 3. 예시 포함 (필요 시)
```python
SYSTEM_PROMPT = """...
Examples:
- Input: "환자: 나비" → Output: "나비"
- Input: "보호자: 김철수" → Output: ""
"""
```

### 4. 출력 형식 명시
```python
SYSTEM_PROMPT = """...
Output format: plain text | JSON | list
"""
```

## 🧪 테스트

### 프롬프트 import 테스트
```bash
poetry run python -c "
from src.services.lab_extraction.prompts import (
    PATIENT_NAME_SYSTEM_PROMPT,
    HEADER_INFERENCE_SYSTEM_PROMPT,
)
print('✅ Import 성공')
print(f'patient_name 프롬프트 길이: {len(PATIENT_NAME_SYSTEM_PROMPT)}')
print(f'header_inference 프롬프트 길이: {len(HEADER_INFERENCE_SYSTEM_PROMPT)}')
"
```

### 통합 테스트
```bash
poetry run pytest tests/test_llm_metadata_fallback.py -v
```

## 🔍 디버깅 팁

### 프롬프트 출력 확인
```python
from src.services.lab_extraction.prompts.metadata_extraction import (
    format_patient_name_user_prompt
)

user_prompt = format_patient_name_user_prompt(
    header_text="펫플러스동물병원\n보호자: 김철수\n나비",
    client_name="김철수"
)

print(user_prompt)
```

### LLM 응답 확인
```python
# lab_table_extractor.py의 _extract_patient_name_with_llm 메서드에서
# LLM 응답을 로깅하여 프롬프트 효과 검증
```

## 📚 참고 자료

- OpenAI Best Practices: https://platform.openai.com/docs/guides/prompt-engineering
- Anthropic Prompt Engineering: https://docs.anthropic.com/claude/docs/prompt-engineering

