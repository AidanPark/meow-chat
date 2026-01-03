# 검사지 분석 전문성 향상 작업 계획서 (프레임워크 없이도 가능한 범위)

> 작성일: 2026-01-03  
> 범위: meow-chat(고양이 건강검진 OCR 챗봇 MVP)에서 **검사 결과지 기반 분석**의 신뢰도/전문성/재현성을 올리는 실행 계획서.  
> 핵심 목표: **LLM이 판정을 “생성”하지 않게** 하고(결정론), LLM은 **설명/요약/주의사항**만 담당하도록 분리.

---

## 0) TL;DR (우선순위)

1. **LLM 입력을 Step 13 기반 JSON payload로 고정** (표 문자열 → JSON)  
2. **Quality gate(검증/필터링) 추가** (무엇을 “정확히 인식”으로 볼지 정책화)  
3. **Deterministic 판정 모듈 추가** (정상/↑/↓/(중증도)) → LLM은 설명만  
4. **전문가처럼 묻는 고정 질문 2~3개**를 템플릿화 (일관성/전문성 체감)

---

## 1) 현재 상태(As-Is) 점검

### 1.1 구조화 데이터 원천
- 노트북 Step 13 `final_doc`는 `LabTableExtractor.extract_from_lines(..., return_intermediates=True)`가 생성
- Step 12/13 출력 문자열은 디버그 함수가 렌더링:
  - Step 12: `debug_step12(intermediates)`
  - Step 13: `debug_step13(intermediates)`

### 1.2 현재 앱에서 LLM 입력 방식
- `app/Home.py::format_document_context()`가 `st.session_state.ocr_structured['tests']`를 **마크다운 표 문자열**로 변환
- `src/services/orchestration/lab_analysis_responder.py`가 `context.document_context`를 user 메시지로 LLM에 전달

### 1.3 핵심 문제 정의
- 표 문자열은 파싱/추정 여지가 크고, 토큰 낭비도 발생
- `final_doc`는 정규화된 “측정값”이지만, **판정(정상/↑/↓/중증도)** 은 생성하지 않음
  - 따라서 `final_doc`만 LLM에 줘도 LLM이 판정을 ‘생성’할 수 있음

---

## 2) 목표 상태(To-Be) 정의

### 2.1 LLM 입력 계약(Contract)
- 입력은 **문서 배열(JSON)** 로 고정
- 각 문서:
  - `hospital_name/client_name/patient_name/inspection_date`: optional
  - `tests`: required

```jsonc
[
  {
    "hospital_name": "...",
    "client_name": "...",
    "patient_name": "...",
    "inspection_date": "YYYY-MM-DD",
    "tests": [
      {"code":"RBC","value":6.79,"unit":"M/µL","reference_min":6.54,"reference_max":12.2}
    ]
  }
]
```

### 2.2 판정 책임 분리(핵심)
- 코드: `tests` → `assessments`(정상/↑/↓/중증도/근거)
- LLM: `assessments`를 바탕으로 **설명/요약/주의사항**만 생성

---

## 3) 작업 계획(TODO) — 단계별 진행

> 표기 규칙
> - [ ] TODO (미완료)
> - [x] DONE (완료)
> - ✅ 완료 조건(Definition of Done)
> - 🧪 테스트/검증

---

### Phase 0 — 안전망/관측성(권장, 0.5~1h)

- [x] (P0) 변경 전/후 비교를 위한 샘플 데이터 고정
  - ✅ 완료 조건: 테스트/노트북 실행 시 같은 입력에서 출력 비교 가능
  - 🧪 고정 샘플(레포 내 존재):
    - `tests/fixtures/images/sample_checkup.png`
    - `tests/fixtures/images/test_image_5.png`

- [x] (P0) 디버그 출력/로그 정책 확인
  - ✅ 완료 조건: Step 12(제외 사유)와 Step 13(최종 tests)을 UI/노트북에서 구분해 볼 수 있음
  - 현재 상태:
    - 구조화 결과: `st.session_state.ocr_structured` (Step 13 final_doc)
    - 디버그 출력: expander("🔍 상세 디버그 정보")로 별도 표시

---

### Phase 1 — LLM 입력을 Step 13 기반 JSON payload로 고정 (P0)

**목표:** 앱에서도 "표 문자열" 대신, Step 13 형태의 구조화 JSON(문서 배열)을 LLM에 전달.

- [x] (P0) `format_document_context()`를 "JSON payload 생성 함수"로 교체 또는 신규 생성
  - 구현 옵션 A(간단): 기존 `document_context: str`에 `json.dumps(payload)` 문자열을 넣기 ✅ 적용됨
  - 구현 옵션 B(권장): `OrchestrationContext`에 `document_payload: dict | None` 추가 후, responder에서 JSON 직렬화
  - ✅ 완료 조건: LLM 입력이 표가 아닌 JSON(문서 배열)로 고정됨

- [x] (P0) 멀티 문서 지원 방식 결정
  - 옵션 1: 일단 `[doc]` (단일 원소 배열)로 시작 ✅ 적용됨
  - 옵션 2: 파일 단위로 doc 분리하여 `[doc1, doc2, ...]`
  - ✅ 완료 조건: payload 최상단이 항상 배열

- [x] (P0) LLM 프롬프트에 "입력은 JSON이며, 누락/UNKNOWN은 추정하지 말 것" 추가
  - ✅ 완료 조건: LLM이 없던 수치를 상상해 채우지 않음(프롬프트 준수)

🧪 검증
- [x] (P0) 오케스트레이션/LLM/채팅 관련 pytest 통과 확인 (27 passed)

---

### Phase 2 — Quality Gate(검증/필터링) 정책 확정 및 적용 (P0~P1)

**목표:** "정확히 인식된 데이터만 LLM에 준다"의 정의를 코드로 고정.

- [x] (P0) 통과/제외 기준을 문서화
  - 정책(확정):
    - code는 필수(없으면 제외)
    - value는 숫자 필수(없으면 제외)
    - unit이 UNKNOWN/None/빈값이면 제외
    - reference_min/max 둘 다 숫자 필수(하나라도 없으면 제외)
  - ✅ 완료 조건: 정책이 문서/코드에 동일하게 반영 (8.1절 + validation.py)

- [x] (P0) payload validator 구현(도메인 계층)
  - 위치: `src/services/lab_extraction/validation.py` ✅ 구현 완료
  - 출력: `accepted_tests`, `rejected_tests(with reason)`, `quality_summary`
  - ✅ 완료 조건: LLM에 들어가는 tests는 accepted만

- [ ] (P1) UI에 "인식 제외 항목(사유)" 표시(선택)
  - ✅ 완료 조건: 사용자가 왜 빠졌는지 이해 가능

🧪 검증
- [x] pytest로 validator 단위 테스트 추가 (26개 테스트 통과)
  - code 없음 제외 ✅
  - value non-numeric 제외 ✅
  - unit UNKNOWN 제외 ✅
  - reference_min/max 누락 제외 ✅

---

### Phase 3 — Deterministic 판정 모듈 추가 (P0)

**목표:** (정상/↑/↓/중증도)을 코드로 계산하고, LLM은 설명만.

- [x] (P0) 판정 스키마 정의
  - `status`: normal | abnormal | unknown
  - `direction`: ↑ | ↓ | -
  - `severity`: mild | moderate | severe | unknown (MVP는 unknown 고정) ✅ 적용됨
  - ✅ 완료 조건: 스키마가 코드/테스트/프롬프트에 일치

- [x] (P0) 결정론 판정 함수 구현
  - 위치: `src/services/lab_extraction/assessment.py` ✅ 구현 완료
  - 입력: `{code,value,unit,reference_min,reference_max}`
  - 출력: `{status,direction,severity,reason}`
  - ✅ 완료 조건: 같은 입력이면 항상 같은 판정

- [x] (P0) 프롬프트 수정: LLM이 판정을 "생성"하지 못하게 제한
  - `src/prompts/lab_analysis.py` 수정됨
  - "판정은 이미 제공됨. assessments를 그대로 사용."
  - ✅ 완료 조건: LLM 출력에서 판정 컬럼을 새로 만들지 않음

🧪 검증
- [x] pytest로 판정 로직 단위 테스트 (17개 테스트 통과)
  - 정상/상승/하강/범위없음/값없음 ✅
  - 결정론 속성(같은 입력=같은 출력) ✅

---

### Phase 4 — 전문가처럼 묻는 고정 질문 2~3개 템플릿 (P1)

**목표:** 항상 일관된 "추가 확인 질문" 섹션 제공.

- [x] (P1) 질문 템플릿 정의 및 출력 위치 결정
  - `src/prompts/lab_analysis.py`에 "추가 확인 질문" 섹션 추가 ✅
  - 고정 질문 풀 5개 정의:
    1. 공복 상태 여부
    2. 식욕/음수량/소변량 변화
    3. 구토/설사/체중 변화
    4. 수액 치료/약물 복용 여부
    5. 이전 검사 결과 비교
  - ✅ 완료 조건: 분석 응답에 항상 동일 섹션/형식으로 등장

- [x] (P1) 조건부 노출
  - 프롬프트에 선택 기준 명시:
    - 신장 지표 이상 → 질문 2, 4 우선
    - 간 지표 이상 → 질문 1, 3 우선
    - 전해질 이상 → 질문 4 우선
    - 특별한 이상 없음 → 질문 1, 2, 5 중 선택
  - ✅ 완료 조건: 질문이 과도하게 늘어나지 않음(최대 3개)

🧪 검증
- [x] 오케스트레이션/LLM/채팅 관련 pytest 통과 확인 (27 passed)

---

## 4) '논문/권위 사이트' 활용 가이드(운영 관점)

- 프레임워크/RAG 없이 당장 가능한 방식:
  - 프로젝트 내에 **레퍼런스 노트(짧은 요약 + 링크)** 를 축적
  - LLM에는 “필요 최소” 근거 문장만 컨텍스트로 제공
- 주의: LLM에게 외부 자료를 즉석에서 ‘찾아오게’ 하는 방식은 재현성이 낮고, 실수 시 책임 문제가 커질 수 있음.

---

## 5) 관련 코드 위치(빠른 링크)

- 구조화/정규화
  - `src/services/lab_extraction/lab_table_extractor.py`
    - `extract_from_lines()` → Step 13 `final_doc` 생성
    - `_apply_step12_filters()` → Step 12 필터(unknown/low_conf/dedup)
    - `debug_step12()` / `debug_step13()` → 노트북 출력
- 앱 컨텍스트
  - `app/Home.py::format_document_context()`
- 오케스트레이션
  - `src/services/orchestration/lab_analysis_responder.py`
- 프롬프트
  - `src/prompts/lab_analysis.py`

---

## 6) 최종 산출물(Definition of Done)

- [x] LLM 입력이 JSON payload로 고정되고, 표 문자열 파싱을 제거
- [x] LLM에 들어가는 데이터는 validator를 통과한 항목만
- [x] 판정은 코드에서 deterministic으로 산출되며, LLM은 설명만 담당
- [x] 핵심 단위 테스트/스모크 테스트가 있어 회귀를 막을 수 있음
  - 관련 테스트 스위트: `tests/test_orchestration.py`, `tests/test_lab_validation.py`, `tests/test_assessment.py`

---

## 7) 이 계획서로 작업 수행이 충분한가? (점검)

결론: **대부분 충분합니다.** 다만 형님이 저에게 “바로 구현”을 시킬 때 막히지 않으려면 아래 항목이 추가로 명시되면 더 완벽해집니다.

### 7.1 반드시 확정해야 하는 ‘결정사항(Decisions)’
아래 4가지는 구현 시작 전에 정해야, 중간에 방향이 흔들리지 않습니다.

1) **멀티 문서 정책**
- A. 당장 `[doc]`(단일 원소 배열)로 시작 (MVP 우선)
- B. 업로드 파일 단위로 `[doc1, doc2, ...]` 생성
- C. 병합 로직(LabReportExtractor.merge_extractions) 기준으로 문서 분리 유지

2) **LLM 입력 채널**
- A. 기존 `OrchestrationContext.document_context: str`에 JSON 문자열을 넣는다(변경 최소)
- B. `OrchestrationContext`에 `document_payload: dict | None`를 추가한다(구조적으로 깔끔)

3) **Quality gate 정책(accepted/rejected 기준)**
- 범위(reference) 누락 항목을:
  - A. 포함(단, `assessment=unknown`)
  - B. 제외(LLM에 아예 안 보냄)
- unit UNKNOWN/None을:
  - A. 포함(단, 코드별 unit-필수 정책 적용)
  - B. 전부 제외(보수적)

4) **Deterministic 판정의 스코프(MVP 범위)**
- A. `status/direction`까지만(중증도는 unknown 고정)
- B. severity까지 구현(예: ref 대비 %로 mild/moderate/severe)

> ✅ 추천(형님이 빠르게 체감 보려면):
> - 멀티 문서: A 또는 C
> - LLM 입력: A(빠르게) → 추후 B로 리팩터
> - quality gate: reference 누락은 포함하되 `unknown`, unit은 code별 정책
> - 판정: A(우선), severity는 다음 단계

---

### 7.2 구현 산출물(Deliverables) — “무엇이 완료인지”를 더 구체화

- (D1) **LLM payload 생성 함수**
  - 입력: Step 13 `final_doc` (또는 merged docs)
  - 출력: 문서 배열(JSON) + (선택) quality summary

- (D2) **Quality gate(validator) 모듈 + 테스트**
  - `accepted_tests` / `rejected_tests(with reason)` / `quality_summary`
  - pytest로 최소 3~6개 케이스

- (D3) **Deterministic assessment 모듈 + 테스트**
  - tests → assessments
  - pytest로 정상/상/하/범위없음/단위없음 등

- (D4) **프롬프트/오케스트레이션 수정**
  - LLM이 판정을 생성하지 않도록 제한
  - LLM은 설명/요약/주의사항만 담당

- (D5) (선택) **UI 표시**
  - accepted/rejected 요약
  - “추가 확인 질문” 섹션(최대 3개)

---

### 7.3 수용 기준(Acceptance Criteria) — 자동/수동 체크

#### 기능
- [x] (AC1) 업로드→분석 시 LLM에 전달되는 문서 컨텍스트는 **표 문자열이 아닌 JSON**이다.
- [x] (AC2) LLM 입력 payload는 최상단이 항상 **배열(list)** 이다.
- [x] (AC3) quality gate에서 제외된 항목은 **LLM payload에 포함되지 않는다.**
- [x] (AC4) deterministic assessment 결과는 같은 입력에서 항상 동일하다.

#### 안전/일관성
- [x] (AC5) 프롬프트는 “직접 진단/처방 금지”를 유지한다.
- [x] (AC6) reference 누락/단위 불명 등 불확실성은 `unknown`으로 명시된다.

#### 테스트
- [ ] (AC7) `poetry run pytest`가 통과한다.
  - 주: 현재 레포에는 본 작업과 무관한 기존 실패 테스트가 존재함(예: `tests/test_ocr_real.py`, `tests/test_reference_data.py`).
  - 본 작업 범위 관련 테스트 스위트는 통과함: `tests/test_orchestration.py`, `tests/test_lab_validation.py`, `tests/test_assessment.py`.
- [ ] (AC8) (선택) `ruff`/mypy가 기존 기준을 깨지 않는다(프로젝트 설정에 따름).

---

### 7.4 파일별 변경 포인트(어디를 손댈지)

- Phase 1 (payload)
  - `app/Home.py`: `format_document_context()`를 JSON payload 기반으로 변경(또는 새 함수 추가)
  - `src/services/orchestration/models.py`: (옵션) `document_payload` 필드 추가
  - `src/services/orchestration/lab_analysis_responder.py`: (옵션) payload 직렬화/전달 방식 변경

- Phase 2 (validator)
  - `src/services/lab_extraction/validation.py`: 신규
  - `tests/`: `test_lab_validation.py`(신규) 등

- Phase 3 (assessment)
  - `src/services/lab_extraction/assessment.py`(또는 domain 적절 위치): 신규
  - `tests/`: `test_assessment.py`(신규)

- Phase 4 (질문 템플릿)
  - `src/prompts/lab_analysis.py` 또는 별도 “질문 템플릿” 모듈
  - `app/Home.py` 또는 responder에서 섹션 고정 출력

---

### 7.5 리스크/롤백 플랜(간단)

- 리스크: JSON payload로 바꾸면 토큰량이 변하고, 프롬프트가 기대하는 출력 형식과 충돌할 수 있음
  - 대응: Phase 1에서 프롬프트도 함께 “입력은 JSON”으로 맞추고, 출력은 우선 기존 구조 유지
- 롤백: `format_document_context()`만 되돌리면 즉시 이전 동작(표 문자열)로 복귀 가능

---

### 7.6 다음 액션(형님이 저에게 지시할 때 추천 순서)

1) Phase 1 옵션 결정(7.1의 Decisions)
2) Phase 1 구현 + 스모크(AC1~AC2)
3) Phase 2 validator 구현 + 테스트(AC3, AC7)
4) Phase 3 assessment 구현 + 프롬프트 제한(AC4~AC6)
5) Phase 4 질문 템플릿(선택)

---

## 8) 정책 결정(형님 결정 반영)

### 8.1 LLM payload 필터링 정책(확정)

**목표:** LLM에는 “정확히 인식된 정규화 데이터”만 전달한다.

- ✅ **tests 포함 조건(accepted)**
  - `code`가 비어있지 않음
  - `value`가 숫자
  - `unit`이 **존재하며**, `UNKNOWN`/빈 문자열이 아님
  - reference range가 **존재함**
    - 여기서 “존재”의 정의: `reference_min`과 `reference_max`가 **둘 다 숫자**

- ❌ **tests 제외 조건(rejected)**
  - `unit`이 `None`/빈 문자열/`UNKNOWN`이면 제외
  - `reference_min` 또는 `reference_max`가 누락되면 제외

> 구현 위치 제안(권장):
> - **LLM payload 생성 직전(validator 단계)** 에서 제외하는 것이 가장 안전함
>   - 이유: Step 13(final_doc)은 추출기의 “최종 결과”로 보존해 두고,
>     LLM 입력 정책은 별도의 quality gate로 관리해야 디버깅/회귀 추적이 쉬움
> - 구현 위치 대안: `LabTableExtractor._apply_step12_filters()` 또는 `_to_final_json()`에서 제거
>   - 단점: 디버그/QA(왜 빠졌는지) 추적이 어려워지고, 추출기의 “원본 최종 결과”가 손실될 수 있음

---

### 8.2 멀티 문서 정책(A/B/C) — 현재 앱 구조에서의 의미

현재 앱(`app/Home.py`)은 업로드된 여러 파일/여러 페이지를 처리한 뒤, 결과를 `st.session_state.ocr_structured`에 **단일 dict**로 저장합니다. 즉, 기본 동작은 “여러 입력을 하나로 병합한 단일 doc”입니다.

그래서 A/B/C는 ‘데이터를 어떤 단위로 문서 리스트로 만들 것인가’의 정책입니다.

#### A. 당장 `[doc]`(단일 원소 배열)로 시작 (MVP 우선)
- 의미: 현재 `ocr_structured`(단일 dict)를 그대로 사용하되,
  LLM 입력 계약을 맞추기 위해 **무조건 배열로 감싼다**.
  - payload = `[ filtered_doc ]`
- 장점: 구현 변경 최소. 지금 바로 적용 가능.
- 단점: 파일이 여러 개여도 LLM은 “1개의 문서”로만 인식(날짜/문서별 구분 약함)

#### B. 업로드 파일 단위로 `[doc1, doc2, ...]` 생성
- 의미: 업로드된 각 파일(또는 각 PDF)마다 **doc을 따로 추출**하고,
  최종 payload를 파일 단위로 리스트 구성.
  - payload = `[ doc_from_file1, doc_from_file2, ... ]`
- 구현상 필요 변경: 현재는 `ocr_structured`를 병합해 1개로 저장하므로,
  “파일별 structured 결과 리스트”를 세션에 따로 저장해야 함.
- 장점: 파일 단위 비교/추세가 쉬움.
- 단점: 구현 변경이 A보다 큼.

#### C. 병합 로직(LabReportExtractor.merge_extractions) 기준으로 문서 분리 유지
- 의미: 파일/페이지 단위로 여러 doc을 만든 뒤,
  `merge_extractions`가 판단한 결과(예: 날짜/헤더 shape 기준)대로
  **동일 문서만 병합**하고, 서로 다른 문서는 리스트로 유지.
  - payload = `merge_envelope.data.merged`를 기반으로 `[doc1, doc2, ...]`
- 장점: "실제 같은 검사지는 합치고, 다른 검사지는 분리"라는 실사용에 가장 가깝다.
- 단점: B와 마찬가지로 ‘초기 doc 리스트’를 들고 있어야 하므로 구현 변경이 필요.

> ✅ 형님이 지금 선택한 MVP 기본값(추천):
> - 멀티 문서 정책은 **A로 시작**(payload는 항상 `[doc]`)
> - 이후 필요해지면 C로 확장(merge_extractions 결과를 payload에 반영)

---

## 9) 장기 계획(프레임워크 도입 이후)까지 고려한 설계 가이드

형님이 말한 목표는 **"검사결과를 일자별로 저장 → 나중에 아주 오래전 결과도 참조하는 개인화 상담"** 입니다.
이를 위해 지금 단계에서 가장 중요한 건:

1) **LLM 입력 계약을 장기 저장 가능한 형태로 고정**(스키마 안정성)
2) 지금은 MVP로 단순하게 시작하되, 나중에 **문서 분리/저장/조회**로 확장 가능하게 “메타 필드”를 준비

### 9.1 저장/조회까지 염두한 최소 메타데이터(권장)

MVP에선 안 써도 되지만, 아래 필드가 있으면 향후 저장/조회/버전 관리가 쉬워집니다.

- `document_id` (선택): 한 문서를 식별하는 ID(예: UUID)
- `source_id` (선택): 업로드 파일명/해시/페이지 정보 등 원천 추적용
- `schema_version` (선택): 예: `"lab_report_v1"`

예시(payload 원소 1개):
```jsonc
{
  "schema_version": "lab_report_v1",
  "document_id": "...",
  "source_id": "2026-01-03_upload_001.pdf#p1",
  "inspection_date": "YYYY-MM-DD",
  "tests": [ ... ]
}
```

> 지금 Phase 1에서는 payload를 `[doc]`로 시작하되,  
> Phase 2(validator) 단계에서 `source_id` 같은 메타를 “붙일 수 있게” 구조를 열어두는 걸 권장합니다.

### 9.2 향후 개인화 컨텍스트(장기 히스토리)로 확장하는 방법

프레임워크 도입 이후의 이상적인 흐름(개념)은 다음과 같습니다.

1) 업로드/OCR/구조화 → **검증된 payload 생성**
2) `inspection_date` 기준으로 사용자(고양이)별 저장
3) 상담 시:
   - 최근 N회 + 이상치가 있었던 과거 key 날짜를 요약해서 LLM 컨텍스트로 제공

이때 LLM에 넣는 히스토리 컨텍스트는 “전체 raw tests”를 다 넣기보다:
- (권장) **요약 테이블(주요 항목의 시간 추세)**
- (추가) 최근 1~2회분의 상세 tests
처럼 토큰 예산을 관리하는 방식이 안정적입니다.

### 9.3 멀티 문서 정책의 장기 관점 결론

- 지금(MVP): **A. `[doc]`로 시작**
  - 빠르게 payload 계약을 고정하고, 품질 gate를 먼저 완성
- 확장(저장/조회 시작 시점): **C. merge_extractions 기반으로 문서 분리 유지**
  - "같은 검사지는 합치고, 다른 검사지는 분리"가 자동화되어
    날짜별 문서 저장과 궁합이 좋음

---

## 10) MVP 기본 결정(형님 결정 반영)

- 멀티 문서 정책: **A. `[doc]` 단일 원소 배열로 시작**
- LLM 입력 채널: **A. `document_context`에 JSON 문자열로 전달(변경 최소)**
- payload 필터 정책: **unit UNKNOWN/None/빈값 또는 ref range(min/max) 누락이면 tests에서 제외**
