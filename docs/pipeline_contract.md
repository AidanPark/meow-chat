# OCR 파이프라인 계약(Pydantic v2)

이 문서는 OCR 파이프라인의 표준 계약을 정의합니다. 모든 단계는 Pydantic v2 모델 인스턴스를 사용합니다. 직렬화는 경계 지점(API, 로그, UI)에서만 수행하십시오.

- ocr_to_extraction(OCRResultEnvelope) → ExtractionEnvelope
- merge_extractions(list[dict]) → MergeEnvelope
- 참고: bytes → OCRResultEnvelope 흐름은 현재 외부 공개 함수명(image_to_ocr)으로 제공되지 않습니다. MCP 서버 도구(Extract Lab Report) 또는 로컬 DI 조합으로 동일 흐름을 구성할 수 있습니다(아래 "권장 접근" 참고).
- 스트리밍 변형은 진행 이벤트(dict)를 산출하고, 최종적으로 비스트리밍 함수와 동일한 모델을 반환합니다.

## Envelope 기본 규약

각 단계는 일관된 최상위 필드를 갖는 envelope를 반환합니다.

- stage: str — 실제 코드 기준 사용되는 단계 예시는 다음과 같습니다: "preprocess", "ocr", "line_group", "extract", "merge", "dedup". (핵심 단계는 ocr/extract/merge이며, line_group/dedup는 주로 진행 이벤트에 등장합니다.)
- version: str — envelope 스키마의 시맨틱 버전
- data: 단계별 페이로드
- meta: 단계별 보조 메타데이터

## OCRResultEnvelope

목적: PaddleOCR + 전처리의 구조화 OCR 결과.

- stage: "ocr"
- version: 문자열(예: "1.0")
- data
  - items: list — OCR 토큰 항목의 리스트(dict 또는 타입드 모델)
    - 전형적인 토큰 필드: text, 박스/사각형 좌표, confidence, 라인/워드 그룹, language 등
- meta
  - source: str — 입력 출처 정보(예: "bytes", "path:<...>")
  - lang: str — OCR 언어(예: "korean")
  - engine: str — OCR 엔진 식별자/버전
  - items: int? — 아이템 개수(환경에 따라 있을 수 있음)

주의

- OCR 결과가 없으면 items는 빈 리스트여야 하며(None이 아님).
- 소비자는 PaddleOCR의 원시 튜플에 의존하지 말고 항상 `env.data.items`를 통해 읽어야 합니다.

## ExtractionEnvelope

목적: OCR 라인으로부터의 표 구조 추출 결과.

- stage: "extract"
- version: 문자열(예: "1.0")
- data (dict)
  - tests: list[dict]
    - 각 항목은 대개 다음 필드 포함: name, code, value, unit, reference_range, flag, raw_line 등
  - 보고서 상단에 흔히 있는 선택적 메타 유사 필드(가능 시):
    - hospital_name, client_name, patient_name, header_shape, inspection_date 등
- meta
  - tests: int — 추출된 검사 항목 수(가능 시)
  - lines: int — 고려된 전처리 라인 수(가능 시)

주의

- 추출 실패 또는 무결과 시, `tests`는 빈 리스트입니다.
- `env.data`는 스키마 변경 없이 필드 추가를 허용하기 위해 평범한 dict로 유지합니다.

## MergeEnvelope

목적: 다수의 추출 dict를 결정적 규칙으로 병합.

- stage: "merge"
- version: 문자열(예: "1.0")
- data
  - merged: list[dict] — 최종 병합된 결과 리스트(예: 추출 합본)
- meta
  - pruned_empty: int — 비어 있는 추출 항목이 몇 개 제거되었는지
  - merged_len: int — 병합 후 길이
  - before_dedup: int — 코드/단위 중복 제거 전 개수
  - after_dedup: int — 중복 제거 후 개수

주의

- 중복 제거는 (code, unit)을 키로 하며 최초 발생을 보존합니다.
- 연속 병합 규칙: 이전 항목에 inspection_date가 비어 있지 않고, 다음 항목이 inspection_date만 비어 있으며(그 외 메타가 동일) 테스트 내용이 연속되는 경우, 새 항목 추가 대신 tests를 이어붙입니다.

## 스트리밍 이벤트

스트림 변형은 UI/로깅을 위한 진행 이벤트를 dict로 산출합니다. 이벤트 필드:

- stage: str — envelope stage와 동일(예: "ocr", "line_group", "extract", "dedup", "merge")
- status: str — 예: "start", "progress", "end" 또는 커스텀 마커
- ts: str — ISO-8601 타임스탬프
- message?: str — 선택적 사람이 읽기 쉬운 메모
- progress?: float — 선택적 진행률 추정치 [0, 1]
- result?: Model — 하위 결과가 준비된 경우 선택적 모델 인스턴스
- json?: str — 편의를 위한 선택적 사전 직렬화 JSON
- extra...: any — 구현별 세부(예: 타이밍, 크기)

클라이언트는 미문서화 키에 의존하지 마십시오. 제공되면 `stage`, `status`, `ts`, 그리고 `result` 또는 `json` 중 하나를 우선 사용하십시오.

## 함수 계약 및 권장 접근

### 권장 접근 A: MCP 서버 도구(one-shot)

- LabReport MCP 서버의 `extract_lab_report(paths: Sequence[str])` 도구를 호출하면 내부에서 전처리→OCR→라인 그룹핑→추출→중복제거→병합까지 수행하고 최종 `MergeEnvelope(JSON)`을 반환합니다.
- 경계에서는 JSON 문자열이 반환되며, 내부 파이프라인은 Pydantic 모델을 사용합니다.

### 권장 접근 B: 로컬 DI 조합

- `app.core.deps`의 DI 헬퍼로 전처리기와 OCR 서비스를 취득해 bytes→OCRResultEnvelope 흐름을 구성한 뒤, 아래 함수들을 호출합니다.
  - ocr_to_extraction(OCRResultEnvelope) → ExtractionEnvelope(stage="extract")
  - merge_extractions(list[dict]) → MergeEnvelope

### ocr_to_extraction

- 입력: OCRResultEnvelope
- 출력: ExtractionEnvelope
- 오류 모드:
  - 잘못된 입력(모델 아님): TypeError 발생
  - 추출 실패: `data={"tests": []}`와 가능한 한 최선의 meta로 감싼 envelope 반환

### merge_extractions

- 입력: list[dict] — 추출 dict 리스트(envelope 아님)
- 출력: MergeEnvelope
- 오류 모드:
  - 입력 내 비-dict 항목은 무시
  - 누락된 `tests`는 빈 리스트로 간주

## 사용 예시

Python 사용(로컬 DI)

```python
from app.core import deps

# 1) bytes → OCRResultEnvelope (전처리 + OCR)
with open("tests/notebooks/ocr/assets/images/20241121_0.png", "rb") as f:
  b = f.read()

pre = deps.get_image_preprocessor()
ocr_service = deps.get_ocr_service()

processed = pre.process_bytes(b, debug=False)  # 필요 시 전처리
ocr_env = ocr_service.run_ocr_from_bytes(processed)

# 2) OCR → 추출 → 병합
extractor = deps.get_lab_report_extractor()
extract_env = extractor.ocr_to_extraction(ocr_env)
merged_env = extractor.merge_extractions([extract_env.data])

print(merged_env.model_dump_json(indent=2, ensure_ascii=False))
```

스트리밍 사용(추출/병합 단계)

```python
def on_progress(evt: dict):
    stage = evt.get("stage")
    status = evt.get("status")
    print(f"[{stage}] {status}")

# 예시: extractor.ocr_to_extraction_stream(ocr_env) 또는 extractor.merge_extractions_stream(docs)
```

MCP 서버(one-shot) 사용

```python
# LabReport MCP 서버의 extract_lab_report(paths=[...])
# 반환: MergeEnvelope의 JSON 문자열
# 내부에서 전처리→OCR→라인 그룹핑→추출→중복제거→병합이 수행됩니다.
```

## 마이그레이션 가이드

- 레거시 list/dict 반환은 제거되었습니다. 항상 Pydantic 모델 인스턴스를 소비/생산하십시오.
- 직렬화는 경계에서만 `model_dump()`/`model_dump_json()`을 사용하십시오. 파이프라인 내부에서는 모델을 그대로 유지하십시오.
- OCR 토큰 접근은 `ocr_env.data.items`로 이동했습니다.
- 병합 단계는 추출 dict 리스트를 입력으로 받습니다: 각 항목에 `extract_env.data`를 전달하십시오.
- 단계명 업데이트: "extraction" → "extract". 진행 이벤트에는 "line_group", "dedup"도 등장할 수 있습니다.
- bytes → OCRResultEnvelope 공개 함수(`image_to_ocr`)는 현재 제공되지 않습니다. MCP 도구(one-shot) 또는 로컬 DI 조합을 사용하십시오.

## 검증 및 호환성

- Pydantic v2가 `.model_dump()`/`.model_dump_json()` API에 필요합니다.
- 정확한 Pydantic 버전이 불명확한 환경에서는, 출력 시 try/except를 두고 `getattr(merged_env, 'model_dump', ...)()`로 폴백하는 것을 권장합니다.
