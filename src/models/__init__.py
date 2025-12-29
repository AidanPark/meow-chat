"""데이터 모델 패키지

파이프라인 각 단계별 데이터와 메타데이터를 관리하는 Pydantic 모델을 제공합니다.

주요 모델:
- Envelope: 파이프라인 단계별 데이터 래퍼 (Generic)
- OCRItem, OCRData, OCRMeta, OCRResultEnvelope: OCR 결과
- ExtractionEnvelope, MergeEnvelope: 추출/병합 단계 결과
"""

from .envelopes import (
    # 기본 타입
    Stage,
    Envelope,
    # OCR
    OCRItem,
    OCRData,
    OCRMeta,
    OCRResultEnvelope,
    # Extraction
    ExtractionMeta,
    ExtractionEnvelope,
    # Merge
    MergeData,
    MergeMeta,
    MergeEnvelope,
)

__all__ = [
    "Stage",
    "Envelope",
    "OCRItem",
    "OCRData",
    "OCRMeta",
    "OCRResultEnvelope",
    "ExtractionMeta",
    "ExtractionEnvelope",
    "MergeData",
    "MergeMeta",
    "MergeEnvelope",
]

