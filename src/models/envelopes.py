"""파이프라인 Envelope 모델

파이프라인 각 단계(OCR/추출/병합 등)별 데이터와 메타데이터를
일관되고 타입 안전하게 관리하는 Pydantic 모델 정의.
"""
from __future__ import annotations

from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar, Union
from typing_extensions import TypeAlias

from pydantic import BaseModel, Field


# =============================================================================
# 기본 타입 정의
# =============================================================================

Stage: TypeAlias = Literal['preprocess', 'ocr', 'line_group', 'extract', 'merge', 'dedup']
"""파이프라인 처리 단계"""

TData = TypeVar('TData')
TMeta = TypeVar('TMeta')


class Envelope(BaseModel, Generic[TData, TMeta]):
    """파이프라인 단계별 데이터와 메타데이터를 감싸는 공통 Envelope 모델"""
    stage: Stage
    data: TData
    meta: TMeta
    version: str = '1.0'


# =============================================================================
# OCR 단계 모델
# =============================================================================

class OCRItem(BaseModel):
    """단일 이미지/페이지의 OCR 결과"""
    rec_texts: List[str] = Field(default_factory=list, description="인식된 텍스트 리스트")
    rec_scores: List[float] = Field(default_factory=list, description="인식 신뢰도 리스트")
    dt_polys: List[List[List[float]]] = Field(default_factory=list, description="텍스트 감지 영역 폴리곤")
    rec_polys: Optional[List[List[List[float]]]] = Field(default=None, description="텍스트 인식 영역 폴리곤")

    def __len__(self) -> int:
        return len(self.rec_texts)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'rec_texts': self.rec_texts,
            'rec_scores': self.rec_scores,
            'dt_polys': self.dt_polys,
        }
        if self.rec_polys is not None:
            result['rec_polys'] = self.rec_polys
        return result


class OCRData(BaseModel):
    """OCR 단계 결과 데이터"""
    items: List[OCRItem] = Field(default_factory=list, description="OCR 결과 아이템 리스트")


class OCRMeta(BaseModel):
    """OCR 단계 결과 메타데이터"""
    items: Optional[int] = Field(default=None, description="총 인식된 텍스트 개수")
    source: Optional[Literal['bytes', 'nparray', 'path']] = Field(default=None, description="입력 소스 타입")
    lang: Optional[str] = Field(default=None, description="OCR 인식 언어")
    engine: Optional[str] = Field(default=None, description="사용된 OCR 엔진명")


# =============================================================================
# Extraction 단계 모델
# =============================================================================

class ExtractionMeta(BaseModel):
    """추출 단계 결과 메타데이터"""
    tests: Optional[int] = Field(default=None, description="추출된 검사 항목 수")
    lines: Optional[int] = Field(default=None, description="처리된 라인 수")


# =============================================================================
# Merge 단계 모델
# =============================================================================

class MergeData(BaseModel):
    """병합 단계 결과 데이터"""
    merged: List[Dict[str, Any]] = Field(default_factory=list, description="병합된 결과 리스트")


class MergeMeta(BaseModel):
    """병합 단계 결과 메타데이터"""
    pruned_empty: int = Field(default=0, description="제거된 빈 항목 수")
    merged_len: int = Field(default=0, description="병합 후 항목 수")
    before_dedup: int = Field(default=0, description="중복 제거 전 항목 수")
    after_dedup: int = Field(default=0, description="중복 제거 후 항목 수")


# =============================================================================
# 타입 별칭 (Type Aliases)
# =============================================================================

OCRResultEnvelope = Envelope[OCRData, OCRMeta]
ExtractionEnvelope = Envelope[Dict[str, Any], ExtractionMeta]
MergeEnvelope = Envelope[MergeData, MergeMeta]


__all__ = [
    'Stage',
    'Envelope',
    'OCRItem',
    'OCRData',
    'OCRMeta',
    'OCRResultEnvelope',
    'ExtractionMeta',
    'ExtractionEnvelope',
    'MergeData',
    'MergeMeta',
    'MergeEnvelope',
]

