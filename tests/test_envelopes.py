"""Envelope 모델 테스트

Step 2.1: OCRResultEnvelope, OCRItem, OCRData, OCRMeta 등 Pydantic 모델 검증
"""

import pytest
from typing import Dict, Any

from src.models.envelopes import (
    Stage,
    Envelope,
    OCRItem,
    OCRData,
    OCRMeta,
    OCRResultEnvelope,
    ExtractionMeta,
    ExtractionEnvelope,
    MergeData,
    MergeMeta,
    MergeEnvelope,
)


class TestOCRItem:
    """OCRItem 모델 테스트"""

    def test_create_ocr_item(self):
        """OCRItem 생성"""
        item = OCRItem(
            rec_texts=["WBC", "12.5", "K/L"],
            rec_scores=[0.95, 0.92, 0.88],
            dt_polys=[
                [[10, 100], [50, 100], [50, 120], [10, 120]],
                [[60, 100], [100, 100], [100, 120], [60, 120]],
                [[110, 100], [150, 100], [150, 120], [110, 120]],
            ]
        )
        assert item.rec_texts == ["WBC", "12.5", "K/L"]
        assert item.rec_scores == [0.95, 0.92, 0.88]
        assert len(item.dt_polys) == 3

    def test_ocr_item_len(self):
        """OCRItem __len__"""
        item = OCRItem(
            rec_texts=["A", "B", "C", "D"],
            rec_scores=[0.9, 0.9, 0.9, 0.9],
            dt_polys=[[[0, 0], [1, 0], [1, 1], [0, 1]]] * 4
        )
        assert len(item) == 4

    def test_ocr_item_empty(self):
        """빈 OCRItem 생성"""
        item = OCRItem()
        assert item.rec_texts == []
        assert item.rec_scores == []
        assert item.dt_polys == []
        assert item.rec_polys is None
        assert len(item) == 0

    def test_ocr_item_with_rec_polys(self):
        """rec_polys 포함 OCRItem"""
        item = OCRItem(
            rec_texts=["WBC"],
            rec_scores=[0.95],
            dt_polys=[[[10, 100], [50, 100], [50, 120], [10, 120]]],
            rec_polys=[[[12, 102], [48, 102], [48, 118], [12, 118]]]
        )
        assert item.rec_polys is not None
        assert len(item.rec_polys) == 1

    def test_ocr_item_to_dict(self):
        """OCRItem to_dict() 레거시 호환"""
        item = OCRItem(
            rec_texts=["WBC"],
            rec_scores=[0.95],
            dt_polys=[[[10, 100], [50, 100], [50, 120], [10, 120]]]
        )
        d = item.to_dict()
        assert d['rec_texts'] == ["WBC"]
        assert d['rec_scores'] == [0.95]
        assert 'dt_polys' in d
        assert 'rec_polys' not in d  # None이면 포함 안함

    def test_ocr_item_to_dict_with_rec_polys(self):
        """rec_polys 포함 시 to_dict()"""
        item = OCRItem(
            rec_texts=["WBC"],
            rec_scores=[0.95],
            dt_polys=[[[10, 100], [50, 100], [50, 120], [10, 120]]],
            rec_polys=[[[12, 102], [48, 102], [48, 118], [12, 118]]]
        )
        d = item.to_dict()
        assert 'rec_polys' in d


class TestOCRData:
    """OCRData 모델 테스트"""

    def test_create_ocr_data(self):
        """OCRData 생성"""
        item = OCRItem(
            rec_texts=["WBC", "12.5"],
            rec_scores=[0.95, 0.92],
            dt_polys=[[[0, 0], [1, 0], [1, 1], [0, 1]]] * 2
        )
        data = OCRData(items=[item])
        assert len(data.items) == 1
        assert data.items[0].rec_texts == ["WBC", "12.5"]

    def test_ocr_data_empty(self):
        """빈 OCRData"""
        data = OCRData()
        assert data.items == []

    def test_ocr_data_multiple_items(self):
        """다중 아이템 (다중 페이지)"""
        item1 = OCRItem(rec_texts=["Page1"], rec_scores=[0.9], dt_polys=[[]])
        item2 = OCRItem(rec_texts=["Page2"], rec_scores=[0.9], dt_polys=[[]])
        data = OCRData(items=[item1, item2])
        assert len(data.items) == 2


class TestOCRMeta:
    """OCRMeta 모델 테스트"""

    def test_create_ocr_meta(self):
        """OCRMeta 생성"""
        meta = OCRMeta(
            items=10,
            source='nparray',
            lang='korean',
            engine='EasyOCR'
        )
        assert meta.items == 10
        assert meta.source == 'nparray'
        assert meta.lang == 'korean'
        assert meta.engine == 'EasyOCR'

    def test_ocr_meta_defaults(self):
        """OCRMeta 기본값"""
        meta = OCRMeta()
        assert meta.items is None
        assert meta.source is None
        assert meta.lang is None
        assert meta.engine is None

    def test_ocr_meta_source_literal(self):
        """OCRMeta source 리터럴 타입"""
        for source in ['bytes', 'nparray', 'path']:
            meta = OCRMeta(source=source)
            assert meta.source == source


class TestOCRResultEnvelope:
    """OCRResultEnvelope 통합 테스트"""

    def test_create_envelope(self):
        """OCRResultEnvelope 생성"""
        item = OCRItem(
            rec_texts=["WBC", "12.5", "K/L"],
            rec_scores=[0.95, 0.92, 0.88],
            dt_polys=[[[0, 0], [1, 0], [1, 1], [0, 1]]] * 3
        )
        envelope = OCRResultEnvelope(
            stage='ocr',
            data=OCRData(items=[item]),
            meta=OCRMeta(items=3, lang='korean', engine='EasyOCR')
        )

        assert envelope.stage == 'ocr'
        assert envelope.version == '1.0'
        assert len(envelope.data.items) == 1
        assert envelope.data.items[0].rec_texts[0] == "WBC"
        assert envelope.meta.engine == 'EasyOCR'

    def test_envelope_json_serialization(self):
        """JSON 직렬화/역직렬화"""
        item = OCRItem(
            rec_texts=["WBC"],
            rec_scores=[0.95],
            dt_polys=[[[10, 100], [50, 100], [50, 120], [10, 120]]]
        )
        envelope = OCRResultEnvelope(
            stage='ocr',
            data=OCRData(items=[item]),
            meta=OCRMeta(items=1, engine='EasyOCR')
        )

        # 직렬화
        json_str = envelope.model_dump_json()
        assert 'WBC' in json_str
        assert 'EasyOCR' in json_str

        # 역직렬화
        restored = OCRResultEnvelope.model_validate_json(json_str)
        assert restored.data.items[0].rec_texts[0] == "WBC"

    def test_envelope_dict_conversion(self):
        """딕셔너리 변환"""
        item = OCRItem(
            rec_texts=["RBC"],
            rec_scores=[0.90],
            dt_polys=[[[0, 0], [1, 0], [1, 1], [0, 1]]]
        )
        envelope = OCRResultEnvelope(
            stage='ocr',
            data=OCRData(items=[item]),
            meta=OCRMeta(items=1)
        )

        d = envelope.model_dump()
        assert d['stage'] == 'ocr'
        assert d['data']['items'][0]['rec_texts'] == ['RBC']


class TestLinePreprocessorCompatibility:
    """line_preprocessor 호환성 테스트

    line_preprocessor는 다음 형태로 OCR 결과에 접근:
    - ocr_result.get('rec_texts') 또는 getattr(ocr_result, 'rec_texts')
    - ocr_result.get('rec_scores')
    - ocr_result.get('dt_polys')
    """

    def test_ocr_item_attribute_access(self):
        """OCRItem 속성 접근 (getattr 호환)"""
        item = OCRItem(
            rec_texts=["WBC", "12.5"],
            rec_scores=[0.95, 0.92],
            dt_polys=[[[0, 0], [1, 0], [1, 1], [0, 1]]] * 2
        )

        # getattr 방식 접근
        rec_texts = getattr(item, 'rec_texts', None)
        rec_scores = getattr(item, 'rec_scores', None)
        dt_polys = getattr(item, 'dt_polys', None)

        assert rec_texts == ["WBC", "12.5"]
        assert rec_scores == [0.95, 0.92]
        assert dt_polys is not None

    def test_ocr_item_dict_access(self):
        """OCRItem 딕셔너리 접근 (to_dict 후)"""
        item = OCRItem(
            rec_texts=["WBC", "12.5"],
            rec_scores=[0.95, 0.92],
            dt_polys=[[[0, 0], [1, 0], [1, 1], [0, 1]]] * 2
        )

        # to_dict() 후 dict 방식 접근
        d = item.to_dict()
        rec_texts = d.get('rec_texts')
        rec_scores = d.get('rec_scores')
        dt_polys = d.get('dt_polys')

        assert rec_texts == ["WBC", "12.5"]
        assert rec_scores == [0.95, 0.92]
        assert dt_polys is not None

    def test_envelope_to_legacy_format(self):
        """Envelope에서 레거시 형식으로 변환"""
        item = OCRItem(
            rec_texts=["WBC", "12.5", "K/L"],
            rec_scores=[0.95, 0.92, 0.88],
            dt_polys=[
                [[10, 100], [50, 100], [50, 120], [10, 120]],
                [[60, 100], [100, 100], [100, 120], [60, 120]],
                [[110, 100], [150, 100], [150, 120], [110, 120]],
            ]
        )
        envelope = OCRResultEnvelope(
            stage='ocr',
            data=OCRData(items=[item]),
            meta=OCRMeta(items=3)
        )

        # line_preprocessor가 기대하는 형식으로 변환
        ocr_result = envelope.data.items[0]  # 첫 번째 페이지

        # getattr 방식 접근 가능
        assert getattr(ocr_result, 'rec_texts', None) is not None
        assert len(ocr_result.rec_texts) == 3
        assert ocr_result.rec_texts[0] == "WBC"


class TestExtractionEnvelope:
    """ExtractionEnvelope 테스트"""

    def test_create_extraction_envelope(self):
        """ExtractionEnvelope 생성"""
        envelope = ExtractionEnvelope(
            stage='extract',
            data={'results': [{'code': 'WBC', 'value': '12.5'}]},
            meta=ExtractionMeta(tests=1, lines=5)
        )
        assert envelope.stage == 'extract'
        assert envelope.meta.tests == 1


class TestMergeEnvelope:
    """MergeEnvelope 테스트"""

    def test_create_merge_envelope(self):
        """MergeEnvelope 생성"""
        envelope = MergeEnvelope(
            stage='merge',
            data=MergeData(merged=[{'code': 'WBC', 'value': '12.5'}]),
            meta=MergeMeta(merged_len=1, before_dedup=2, after_dedup=1)
        )
        assert envelope.stage == 'merge'
        assert envelope.meta.merged_len == 1
        assert len(envelope.data.merged) == 1

