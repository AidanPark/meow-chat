from __future__ import annotations

# 필요한 타입/클래스 임포트
from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar

from pydantic import BaseModel, Field

# Stage, TData, TMeta 타입 변수 정의
Stage = Literal['preprocess', 'ocr', 'line_group', 'extract', 'merge', 'dedup']
TData = TypeVar('TData')
TMeta = TypeVar('TMeta')
# 파이프라인 각 단계(OCR/추출/병합 등)별 데이터와 메타데이터를 일관되고 타입 안전하게 관리하는 모델 정의 파일
#
# 주요 역할:
# - OCR, 추출, 병합 등 파이프라인 단계별 결과를 Envelope 패턴으로 감싸서 데이터 흐름을 통일
# - 각 단계별 데이터와 메타데이터를 Pydantic 기반으로 타입 안전하게 관리
# - 타입 별칭 및 __all__로 외부 import 시 필요한 심볼만 노출

class Envelope(BaseModel, Generic[TData, TMeta]):
    # 파이프라인 단계별 데이터와 메타데이터를 감싸는 공통 Envelope 모델
    # - stage: 처리 단계명
    # - data: 단계별 데이터
    # - meta: 단계별 메타데이터
    # - version: 스키마 버전
    stage: Stage
    data: TData
    meta: TMeta
    version: str = '1.0'


# ---------- OCR ----------
class OCRData(BaseModel):
    # OCR 단계 결과 데이터(items)
    items: List[Dict[str, Any]] = Field(default_factory=list)


class OCRMeta(BaseModel):
    # OCR 단계 결과 메타데이터(아이템 수, 소스 타입, 언어, 엔진 등)
    items: Optional[int] = None
    source: Optional[Literal['bytes', 'nparray', 'path']] = None
    lang: Optional[str] = None
    engine: Optional[str] = None


# ---------- Extraction ----------
class ExtractionMeta(BaseModel):
    # 추출 단계 결과 메타데이터(테스트/라인 수 등)
    tests: Optional[int] = None
    lines: Optional[int] = None


# ---------- Merge ----------
class MergeData(BaseModel):
    # 병합 단계 결과 데이터(merged 리스트)
    merged: List[Dict[str, Any]] = Field(default_factory=list)


class MergeMeta(BaseModel):
    # 병합 단계 결과 메타데이터(병합/중복제거 관련 수치)
    pruned_empty: int = 0
    merged_len: int = 0
    before_dedup: int = 0
    after_dedup: int = 0


# ---------- Type Aliases ----------
OCRResultEnvelope = Envelope[OCRData, OCRMeta]
ExtractionEnvelope = Envelope[Dict[str, Any], ExtractionMeta]
MergeEnvelope = Envelope[MergeData, MergeMeta]

__all__ = [
    'Stage',
    'Envelope',
    'OCRData', 'OCRMeta', 'OCRResultEnvelope',
    'ExtractionMeta', 'ExtractionEnvelope',
    'MergeData', 'MergeMeta', 'MergeEnvelope',
]
