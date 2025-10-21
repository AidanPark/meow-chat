# 반려동물 건강검진 데이터 추출 파이프라인 설계서

본 문서는 OCR로 추출한 텍스트와 기하(geometry) 정보를 이용해 반려동물 건강검진 결과지를 표준 JSON으로 변환하는 전 과정(규칙 기반 + LLM 보조)을 단계별로 설명합니다. 각 Step에서 수행되는 작업, 핵심 규칙, 디버그 포인트, 그리고 전체 흐름이 달성하려는 목적을 정리했습니다.


## 목표와 성과물

- 목적: 다양한 양식의 검사결과지(테이블 헤더/열 순서/라벨 변형/노이즈)로부터 안정적으로 구조화 데이터를 추출합니다.
- 최종 성과물(JSON 스키마):

```jsonc
{
	"hospital_name": "OOOOOOO",        // optional
	"client_name": "OOOOOOO",          // optional
	"patient_name": "OOOOOOO",         // optional
	"inspection_date": "YYYY-MM-DD",   // optional
	"tests": [                          // required (비어있지 않을 때 유효)
		{ "code": "RBC", "unit": "M/µL", "reference_min": 6.54, "reference_max": 12.2, "value": 6.79 },
		{ "code": "ALT", "unit": "%",   "reference_min": null, "reference_max": null, "value": 23 }
	]
}
```

참고: 단위 정규화 정책은 CBC 절대수(10^3 계열) → K/µL, RBC(10^6 계열) → M/µL로 일원화합니다. “µ/μ/u” 변형과 슬래시 누락(KµL, MµL 등)도 안전하게 해석합니다.


## 전체 파이프라인 개요

1) 이미지 전처리 → 2) OCR → 3) 라인 그룹핑/값·단위 분리 → 4) 테이블 바디 시작 검출 → 5) 헤더 확정/추론(LLM 백업) → 6) 상단 메타데이터 추출 → 7) 테이블 Filling(UNKNOWN 채움) → 8) 행 길이 정규화 → 9) Reference 분리 → 10) Unit/Result 정규화 → 11) 최종 필터링 → 12) 최종 JSON + QA 요약

의도: 상류 단계에서 구조를 최대한 안정화하고, 위험한 추론은 지연/제한하여 최종 정확도를 높입니다.


## 입력/출력 계약(Contract)

- 입력: 문서 이미지 1장(또는 바이트), OCR 결과(텍스트+박스+신뢰도)
- 출력: 상기 JSON 스키마. tests 배열이 비어있지 않으면 유효로 간주합니다.
- 실패 모드: 바디 시작 미검출, 헤더 정책 미달 등. 이 경우 디버그 로그만 남기고 결과는 빈 tests로 반환될 수 있습니다.


## Step 1. 빈 결과 초기화

목적: 일관된 컨테이너를 먼저 만들고, 이후 단계가 필요한 필드만 채우게 합니다.

- 생성 키: hospital_name, client_name, patient_name, inspection_date, tests([])
- 유효성: tests가 비어있지 않으면 최소 유효


## Step 2. 이미지 전처리 (PaddleOCR 친화)

목적: OCR 적합도를 높이고 테이블 라인/텍스트 선명도를 개선합니다.

주요 단계(권장):
- 투명도 플래튼, 모드 정규화, 최소 해상도 확보(롱엣지 ≥ 1920), 반사 감쇠, 약한 대비 개선
- 색 텍스트 흑화(있을 때), 그레이스케일, 조건부 디워프/데스큐, 테이블 라인 강화, 적정 스케일, 보수적 샤프닝

품질 게이트(권장): 전처리 전후 빠른 메트릭(Tesseract 등)으로 토큰 수/신뢰도 개선이 없으면 원본 유지(롤백).


## Step 3. PaddleOCR 수행

목적: 문서 내 텍스트와 박스를 추출해 후속 라인 그룹핑에 사용할 원시 데이터를 얻습니다.

- 예시 초기화: lang="korean" 등. 서버급 모델 조합 사용 가능.
- 출력은 내부 `PaddleOCRService.extract_and_group_lines()`로 전달됩니다.


## Step 4. 라인 정렬 및 값/단위 분리

목적: OCR 토큰을 라인 단위로 정렬하고, “값+단위”가 한 토큰에 붙어있으면 안전하게 분리합니다.

세부 하위 단계:

### 4.1 `_extract_tokens_with_geometry`
- 텍스트별 confidence와 박스 좌표(y_top/bottom/center, x_left/right, raw_h)를 수집합니다.
- 출력: 토큰 리스트(list[dict]).

### 4.2 `_assign_line_indices_by_y`
- 유사 y 밴드 토큰들을 같은 `line_index`로 묶습니다.
- 출력: 각 토큰에 `line_index`가 추가된 리스트.

### 4.3 `_group_tokens_by_line`
- `line_index` 기준 2차원 배열로 그룹핑하여 라인 단위 데이터로 변환합니다.
- 출력: list[list[token]].

### 4.4 `_split_line_tokens_preserve_fields`
- “값+단위” 결합 텍스트를 분리하되, 원본 geometry는 보존합니다.
- 사용 규칙(매칭 시 분리):

```regex
^\s*([-+]?\d+(?:[.,]\d+)?)\s+(.+?)\s*$                 # 공백 있는 경우
^\s*([-+]?\d+(?:[.,]\d+)?)([A-Za-zµμ%‰/][\w%‰/µμ]*)\s*$  # 공백 없는 경우
```

- 제외 조건: 범위 구분자(-, –, ~) 포함, 12자 초과 장문 단위, 숫자+H/L/N 1글자 접미("12.3H")는 단위로 보지 않음
- 1차(선택) 단위 정규화: `normalize_units_first_pass=True`일 때 전역 렉시콘으로 안전 범위 내 정규화 수행. 원문은 `raw_unit`에 보존, 정규형은 `unit_canonical`.

### 4.5 값 경량 정규화 주석(H/L/N 접미)
- 공백 없는 `^([-+]?\d+(?:\.\d+)?)([HLN])$`만 경량 주석: raw_value, value_num, value_flag, value_norm_stage
- 단위 후보와 충돌 방지 위해 split된 단위 토큰은 제외

### 4.6 상태 토큰 제거(NORMAL/LOW/HIGH)
- 라인 내 데이터 셀에 쓰이지 않는 상태 라벨을 제거해 구조 안정성 확보
- 제거 대상: NORMAL/LOW/HIGH(대소문 무시) “정확 일치”만, 부분 문자열은 보존


## Step 5. 테이블 바디 시작 검출 및 바디 필터링

목적: 실제 데이터 바디의 시작 라인을 견고하게 찾고, 이후 노이즈 라인을 제거합니다.

- 첫 토큰을 코드 사전으로 `resolve_code()` 해석하여 최초 적중 라인을 바디 시작으로 고정
- 바디 시작 이후 라인 중 첫 토큰이 코드로 해석되지 않으면 바디에서 제거
- 채택 라인의 첫 토큰 텍스트는 canonical 코드로 교체해 일관성 확보
- OCR 혼동 완화: 0↔O 보정(보수적 폴백)

디버그: `debug_step5(...)` 바디 시작 인덱스, 프리뷰, 제거 라인과 사유를 출력


## Step 6. 헤더 추출(검증 → 규칙 추론 → LLM 백업)

목적: 바디 위 구간에서 신뢰 가능한 헤더를 확정하고, 부족하면 규칙/LLM으로 보완합니다.

절차:
1) 헤더 후보 검출: 바디 시작 위쪽을 역방향 스캔하여 헤더 키워드 3개 이상 매칭 시 유효
2) 정책 유효성 점검: Name/Unit/Result/Reference/Min/Max 간 충돌·중복 제거, 통과 시 source="ocr"
3) 규칙 추론: 열 경계(1D 클러스터링) → 타입 점수화(코드 적중, 범위 패턴, 유닛 매칭 등)로 라벨링, 성공 시 source="inferred"
4) LLM 백업: 정책 미달 시 대표 라인 1~3개를 입력으로 JSON 형태의 역할 인덱스 요청, 성공 시 source="llm"

디버그: `debug_step6(...)` 헤더 라인, 역할 매핑, source, 정책 유효 여부 출력


## Step 7. 상단 메타데이터 추출

목적: 표 상단 영역에서 검사일/병원명/보호자/환자명을 보수적으로 추출합니다.

- 검사일: 다양한 날짜 포맷 인식 → ISO-8601로 정규화. 키워드 가중치와 근접도 점수로 1개 선택.
- 병원명: “~병원/Animal Hospital/Clinic” 접미 패턴 선호, 주소/연락처/URL/장문 제외 규칙.
- 보호자/의뢰인: 키워드 인접 1~3 토큰 결합(과도/숫자/날짜 유사 차단).
- 환자/동물명: 키워드 오른쪽 x-gap 기반 결합(최대 1~3 토큰, 숫자/날짜 유사 차단).

디버그: `debug_step7(intermediates, show_top_k=K)` 후보 상위 K와 최종 선택 출력


## Step 8. 테이블 Filling (UNKNOWN 채우기)

목적: 규칙 기반으로 안전하게 누락 칸을 메워 “행 단위 테이블”을 안정화합니다.

- Interim 행 구성: name/reference/result/unit 4열 우선, 원본 토큰과 라인을 `_src_tokens`, `_src_line`에 보존
- 타입 검증 후 보정: Result 숫자형만, Reference 범위 패턴만 유효
- 기하 기반 보정(빈 칸일 때만): 숫자형/유닛 후보 스캔 → x_center 근접 기준으로 채움
- 최종적으로 채우지 못한 칸은 문자열 "UNKNOWN"으로 표기

디버그: `debug_step8(intermediates)` 정렬된 행 프리뷰 출력


## Step 9. 행 길이 정규화(뒤에서 자르기)

목적: 헤더 기준 열 개수 K에 맞게 각 행의 셀 수를 강제하여 구조적 일관성을 확보합니다.

- K = max(col_index)+1 또는 첫 행 길이
- 길이가 K보다 크면 뒤에서 잘라 `_row_fix = "truncate_tail"`와 `_dropped_extra` 기록

디버그: `debug_step9(intermediates)` → Name | Reference | Result | Unit | _fix


## Step 10. Reference 분리

목적: Reference에 결합된 범위를 안전하게 Min/Max로 분해합니다.

- 이미 Min/Max가 채워진 문서는 보존
- Reference가 "UNKNOWN"이면 Min/Max도 "UNKNOWN" 채움(`_origin = "ref_unknown"`)
- 안전 정규식 매칭 시 분해: `^\s*([+-]?\d+(?:[.,]\d+)?)\s*[\-–~]\s*([+-]?\d+(?:[.,]\d+)?)\s*$` → `_origin = "ref_split"`

디버그: `debug_step10(intermediates)` → Name | Min | Max | Result | Unit


## Step 11. Unit/Result 정규화

목적: 단위를 canonical 표기로 통일하고, 결과/참조치 숫자값을 순수 숫자 문자열로 강제합니다.

- Unit: 전역 렉시콘으로 해석 가능할 때만 `unit_canonical` 채움(원문 보존)
- Result/Min/Max: 콤마/중점→점, ± 허용, H/L/N 제거 등으로 숫자 문자열을 *_norm에 저장

디버그: `debug_step11(intermediates)` → Name | Result | result_norm | Unit | unit_canonical | Min | min_norm | Max | max_norm


## Step 12. 최종 필터링 (UNKNOWN/신뢰도/중복)

목적: 보수적 규칙으로 최종 `tests`를 정제하고, 제외 항목을 사유와 함께 점검합니다.

- UNKNOWN value 제거 → reason=unknown_value
- Confidence gate(휴리스틱)로 낮은 신뢰도 제거 → reason=low_confidence
- 동일 코드 중복은 마지막만 보존 → reason=duplicated_code_kept_last

디버그: `debug_step12(intermediates)` → 제외된 tests만 표로 출력(code | unit | reference_min | reference_max | value | value_conf | reason)


## Step 13. 최종 JSON 및 QA 요약

목적: 최종 JSON과 기본 QA 지표로 결과 품질을 빠르게 확인합니다.

- 상단 메타(hospital/client/patient/inspection_date) 출력
- tests 테이블: code | value | unit | reference_min | reference_max | value_conf
- QA 요약: 잘린 행 수, unit/result 정규화 커버리지 등

디버그: `debug_step13(intermediates)` 전체 최종 요약 출력


## 단위 정규화 정책(요약)

- 10^3/µL 계열 → K/µL로 일원화: `10^3/µL`, `10³/µL`, `x10^3/uL`, `k/ul`, `KµL` 등 변형 모두 허용
- 10^6/µL 계열 → M/µL로 일원화: `10^6/µL`, `10⁶/µL`, `x10^6/uL`, `m/ul`, `MµL` 등 변형 모두 허용
- µ/μ/u, L/l/ℓ 변형 허용. 슬래시 누락(KµL, MµL)도 동일하게 canonical로 귀결
- RBC는 M/µL, WBC/PLT 등 절대수는 K/µL로 문서/참조데이터와 일관 유지


## 설계 의도와 기대 효과

- 상류 단계에서 구조(라인/헤더/바디)를 먼저 안정화하고, 위험한 추론은 최소화합니다.
- 단위/코드 렉시콘으로 OCR 변형(철자, 대소문, 구분자 누락, 특수문자)을 견고하게 흡수합니다.
- 디버그 훅(debug_step5~13)으로 문제 구간을 빠르게 진단/개선할 수 있습니다.


## 튜닝 포인트(발췌)

- LinePreprocessor Settings: order, alpha, normalize_units_first_pass, 상태 토큰 제거 on/off(현재 기본 on)
- 상단 메타 추출: name_concat_* 파라미터(최대 토큰수, 최소/최대 gap, 날짜 유사 차단 등)
- LLM 백업: 정책 미달 시에만 사용, 대표 라인 샘플 공유로 일관성 확보


## 한계와 추후 과제

- 표가 아닌 자유양식 문서, 테이블이 다단/복합 레이아웃일 때는 추가 규칙/모델 보완 필요
- 정성 결과(pos/neg 등) 처리 정책을 별도 단계로 도입 가능
- 코드/단위 허용 집합 확장(예: 10^9/L 계열) 및 교차 검증 자동화


---
문서 상태: 본 문서는 `notebooks/ocr/paddleocr_test3.ipynb`의 실행 흐름과 디버그 훅을 기반으로 유지/보수됩니다. 단위 표기 정책(K/µL, M/µL 등)과 참조 데이터가 업데이트되면 본 문서도 함께 갱신합니다.