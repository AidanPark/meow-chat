# OCR Pipeline Contract (Pydantic v2)

This document defines the standard contracts for the OCR pipeline. All stages return Pydantic v2 model instances. Serialize to JSON only at boundaries (APIs, logs, UI).

- image_to_ocr(bytes) → OCRResultEnvelope
- ocr_to_extraction(OCRResultEnvelope) → ExtractionEnvelope
- merge_extractions(list[dict]) → MergeEnvelope
- Stream variants yield progress events (dict) and eventually return the same model as the non-stream function.

## Envelope Base

Each stage returns an envelope with consistent top-level fields.

- stage: str — one of "ocr", "extraction", "merge"
- version: str — semantic version of the envelope schema
- data: stage-specific payload
- meta: stage-specific auxiliary metadata

## OCRResultEnvelope

Purpose: Structured OCR result from PaddleOCR + preprocessing.

- stage: "ocr"
- version: string, e.g., "1.0"
- data
  - items: list — list of OCR token entries (dict or Typed model).
    - Typical token fields may include: text, box/quad coordinates, confidence, line/word grouping, language.
- meta
  - source: str — origin info (e.g., "bytes", "path:<...>")
  - lang: str — OCR language (e.g., "korean")
  - engine: str — OCR engine identifier/version

Notes

- If OCR detects nothing, items is an empty list (not None).
- Consumers should not rely on PaddleOCR raw tuples; always read through `env.data.items`.

## ExtractionEnvelope

Purpose: Structured table extraction result from OCR lines.

- stage: "extraction"
- version: string, e.g., "1.0"
- data (dict)
  - tests: list[dict]
    - Each test usually includes fields such as: name, code, value, unit, reference_range, flag, raw_line, etc.
  - Optional meta-like fields commonly present in reports (if available):
    - hospital_name, client_name, patient_name, header_shape, inspection_date, etc.
- meta
  - tests_len: int — number of tests extracted (if available)
  - lines_count: int — number of preprocessed lines considered (if available)

Notes

- When extraction fails or yields nothing, `tests` is an empty list.
- `env.data` remains a plain dict to allow flexible field additions without schema churn.

## MergeEnvelope

Purpose: Merge multiple extraction dicts with deterministic rules.

- stage: "merge"
- version: string, e.g., "1.0"
- data
  - merged: list[dict] — final merged list of results (e.g., merged extractions)
- meta
  - pruned_empty: int — how many empty-extraction items were dropped
  - merged_len: int — final length after merge
  - before_dedup: int — item count before code/unit de-duplication
  - after_dedup: int — item count after de-duplication

Notes

- De-duplication uses (code, unit) as the key and preserves first occurrence.
- Consecutive merge rule: if previous item has a non-empty inspection_date and the next has empty inspection_date but identical meta (excluding date), tests are concatenated instead of appending a new item.

## Streaming Events

Stream variants yield progress events as dicts for UI/logging. Event fields:

- stage: str — same as envelope stage (e.g., "ocr")
- status: str — e.g., "start", "progress", "end", or custom markers
- ts: str — ISO-8601 timestamp
- message?: str — optional human-readable note
- progress?: float — optional progress estimate in [0, 1]
- result?: Model — optional model instance when a sub-result is available
- json?: str — optional pre-serialized JSON for convenience
- extra...: any — implementation-specific details (e.g., timing, sizes)

Clients should not depend on non-documented keys. Prefer `stage`, `status`, `ts`, and one of `result` or `json` when provided.

## Function Contracts

### image_to_ocr

- Input: bytes
- Options: do_preprocess (bool), preprocess_kwargs (dict)
- Output: OCRResultEnvelope
- Error modes:
  - On invalid image bytes: raises an exception (caller should handle)
  - On OCR failure: returns an envelope with `data.items=[]` and best-effort meta

### ocr_to_extraction

- Input: OCRResultEnvelope
- Output: ExtractionEnvelope
- Error modes:
  - On invalid input (not a model): raises a TypeError
  - On extraction failure: returns an envelope with `data={"tests": []}` and best-effort meta

### merge_extractions

- Input: list[dict] — list of extraction dicts (not envelopes)
- Output: MergeEnvelope
- Error modes:
  - Non-dict items in input are ignored
  - Missing `tests` treated as empty list

## Usage Examples

Python usage

```python
import os
from app.services.analysis import OCRPipelineManager

manager = OCRPipelineManager(
    lang="korean",
    debug=True,
    api_key=os.getenv("OPENAI_API_KEY"),
    llm_model="gpt-4.1-mini",
)

with open("tests/notebooks/ocr/assets/images/20241121_0.png", "rb") as f:
    b = f.read()

ocr_env = manager.image_to_ocr(b, do_preprocess=True)
extract_env = manager.ocr_to_extraction(ocr_env)
merged_env = manager.merge_extractions([extract_env.data])

print(merged_env.model_dump_json(indent=2, ensure_ascii=False))
```

Streaming usage

```python
def on_progress(evt: dict):
    stage = evt.get("stage")
    status = evt.get("status")
    print(f"[{stage}] {status}")

# Example: iterate over image_to_ocr_stream(...) in manager implementation
```

## Migration Guide

- Legacy list/dict returns are removed. Always consume and produce Pydantic model instances.
- Use `model_dump()` and `model_dump_json()` at boundaries only. Keep models intact within the pipeline.
- OCR token access moved to `ocr_env.data.items`.
- Merge step accepts a list of extraction dicts: pass `extract_env.data` for each item.

## Validation & Compatibility

- Pydantic v2 is required for `.model_dump()`/`.model_dump_json()` APIs.
- If running in environments where exact Pydantic version is unknown, guard printing with a try/except and fall back to `getattr(merged_env, 'model_dump', ...)()`.
