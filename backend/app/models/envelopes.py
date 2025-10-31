from __future__ import annotations

from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar
from pydantic import BaseModel, Field

Stage = Literal['preprocess', 'ocr', 'line_group', 'extract', 'merge', 'dedup']

TData = TypeVar('TData')
TMeta = TypeVar('TMeta')


class Envelope(BaseModel, Generic[TData, TMeta]):
    """Generic envelope used across the pipeline.

    Fields:
      - stage: processing stage name
      - data: stage-specific payload
      - meta: stage-specific metadata
      - version: schema version string
    """
    stage: Stage
    data: TData
    meta: TMeta
    version: str = '1.0'


# ---------- OCR ----------
class OCRData(BaseModel):
    items: List[Dict[str, Any]] = Field(default_factory=list)


class OCRMeta(BaseModel):
    items: Optional[int] = None
    source: Optional[Literal['bytes', 'nparray', 'path']] = None
    lang: Optional[str] = None
    engine: Optional[str] = None


# ---------- Extraction ----------
class ExtractionMeta(BaseModel):
    tests: Optional[int] = None
    lines: Optional[int] = None


# ---------- Merge ----------
class MergeData(BaseModel):
    merged: List[Dict[str, Any]] = Field(default_factory=list)


class MergeMeta(BaseModel):
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
