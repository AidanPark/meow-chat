from __future__ import annotations
from app.models.envelopes import (
    Envelope,
    ExtractionEnvelope,
    ExtractionMeta,
    MergeData,
    MergeEnvelope,
    MergeMeta,
    OCRResultEnvelope,
)


from typing import Any, Callable, Dict, List, Optional
import time
import asyncio

Event = Dict[str, Any]
ProgressCB = Optional[Callable[[Event], None]]

class LabReportExtractor:
    """
    건강검진(혈액 검사) 리포트를 위한 후처리 파이프라인.

    1) LangGraph/Core OCR 서버에서 반환한 OCRResultEnvelope → 추출(ocr_to_extraction)
    2) 여러 추출 결과를 병합하여 최종 MergeEnvelope 생성(merge_extractions)

    이미지 OCR 자체는 별도(core) 서버에서 처리하며, 이 클래스는 추출/병합 단계만 담당한다.
    의존성(line_preproc, extractor)은 app.core.deps에서 주입한다.
    """

    def __init__(
        self,
        *,
        line_preproc=None,
        extractor=None,
        progress_cb: ProgressCB = None,
    ) -> None:
        if line_preproc is None or extractor is None:
            from app.core.deps import (
                get_line_preprocessor,
                get_lab_table_extractor
            )

            if line_preproc is None:
                line_preproc = get_line_preprocessor()
            if extractor is None:
                extractor = get_lab_table_extractor()

        self.line_preproc = line_preproc
        self.extractor = extractor
        self._progress_cb = progress_cb

    # ---------- DI 편의 생성자 ----------
    @classmethod
    def create_with_deps(
        cls,
        *,
        progress_cb: ProgressCB = None,
    ) -> "LabReportExtractor":
        """중앙 DI를 통해 의존성을 주입하여 LabReportExtractor 인스턴스를 생성합니다.

        - 외부에서 개별 컴포넌트를 전달하지 않아도 되는 간편 생성자입니다.
        - 테스트나 커스터마이징이 필요하면 본 생성자 대신 __init__에 명시 주입하세요.
        """
        from app.core.deps import (
            get_line_preprocessor,
            get_lab_table_extractor
        )

        return cls(
            line_preproc=get_line_preprocessor(),
            extractor=get_lab_table_extractor(),
            progress_cb=progress_cb,
        )

    # ---------- 내부 유틸 ----------
    @staticmethod
    def _ts() -> float:
        return time.time()

    def _emit(self, event: Event, progress_cb: ProgressCB = None) -> None:
        cb = progress_cb or self._progress_cb
        if cb:
            try:
                cb(event)
            except Exception:
                # 콜백 오류는 파이프라인을 중단시키지 않음
                pass

    # ---------- OCR 결과 -> 추출 dict ----------
    def ocr_to_extraction(self, ocr_result: Any, *, progress_cb: ProgressCB = None) -> Envelope[Dict[str, Any], ExtractionMeta]:
        if isinstance(ocr_result, (dict, str)):
            try:
                ocr_result = OCRResultEnvelope.model_validate(ocr_result) if isinstance(ocr_result, dict) else OCRResultEnvelope.model_validate_json(ocr_result)
            except Exception:
                return Envelope[Dict[str, Any], ExtractionMeta](stage='extract', data={}, meta=ExtractionMeta(tests=0)) # type: ignore
        if not (hasattr(ocr_result, 'data') and hasattr(ocr_result, 'meta')):
            return Envelope[Dict[str, Any], ExtractionMeta](stage='extract', data={}, meta=ExtractionMeta(tests=0)) # type: ignore
        self._emit({'stage': 'line_group', 'status': 'start', 'ts': self._ts()}, progress_cb)
        # 모델(envelope)만 지원
        _data = getattr(ocr_result, 'data', None)
        _items = getattr(_data, 'items', None)
        items = _items if isinstance(_items, list) else None
        lined = self.line_preproc.extract_and_group_lines(items[0] if items and len(items) > 0 else None)
        meta = {'lines': len(lined) if hasattr(lined, '__len__') else None}
        self._emit({'stage': 'line_group', 'status': 'end', 'ts': self._ts(), **meta}, progress_cb)

        self._emit({'stage': 'extract', 'status': 'start', 'ts': self._ts()}, progress_cb)
        extraction = self.extractor.extract(lined)
        tests_len = None
        try:
            tests = extraction.get('tests') if isinstance(extraction, dict) else None
            tests_len = len(tests) if isinstance(tests, list) else None
        except Exception:
            pass
        self._emit({'stage': 'extract', 'status': 'end', 'ts': self._ts(), 'tests': tests_len}, progress_cb)
        from app.models.envelopes import Envelope, ExtractionMeta
        env = Envelope[Dict[str, Any], ExtractionMeta](
            stage='extract',
            data=extraction if isinstance(extraction, dict) else {},
            meta=ExtractionMeta(tests=tests_len, lines=meta.get('lines')),
        )
        return env

    def ocr_to_extraction_stream(self, ocr_result: Any):
        from app.models.envelopes import Envelope, ExtractionMeta
        if not (hasattr(ocr_result, 'data') and hasattr(ocr_result, 'meta')):
            yield {
                'stage': 'extract',
                'status': 'end',
                'ts': self._ts(),
                'result': Envelope[Dict[str, Any], ExtractionMeta](stage='extract', data={}, meta=ExtractionMeta(tests=0)),
            }
            return
        # line_group start
        evt = {'stage': 'line_group', 'status': 'start', 'ts': self._ts()}
        self._emit(evt)
        yield evt
        # prepare items
        _data = getattr(ocr_result, 'data', None)
        _items = getattr(_data, 'items', None)
        items = _items if isinstance(_items, list) else None
        lined = self.line_preproc.extract_and_group_lines(items[0] if items and len(items) > 0 else None)
        evt = {
            'stage': 'line_group',
            'status': 'end',
            'ts': self._ts(),
            'lines': len(lined) if hasattr(lined, '__len__') else None,
        }
        self._emit(evt)
        yield evt

        # extract start
        evt = {'stage': 'extract', 'status': 'start', 'ts': self._ts()}
        self._emit(evt)
        yield evt
        extraction = self.extractor.extract(lined)
        tests_len = None
        try:
            tests = extraction.get('tests') if isinstance(extraction, dict) else None
            tests_len = len(tests) if isinstance(tests, list) else None
        except Exception:
            pass
        out = Envelope[Dict[str, Any], ExtractionMeta](
            stage='extract',
            data=extraction if isinstance(extraction, dict) else {},
            meta=ExtractionMeta(tests=tests_len, lines=evt.get('lines') if isinstance(evt, dict) else None),
        )
        evt = {'stage': 'extract', 'status': 'end', 'ts': self._ts(), 'tests': tests_len, 'result': out}
        self._emit(evt)
        yield evt

    async def ocr_to_extraction_async(self, ocr_result: Any, *, progress_cb: ProgressCB = None) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: self.ocr_to_extraction(ocr_result, progress_cb=progress_cb))

    # ---------- 복수 추출 결과 병합 ----------
    @staticmethod
    def _is_empty_tests(item: dict) -> bool:
        tests = item.get('tests')
        return not isinstance(tests, list) or len(tests) == 0

    @staticmethod
    def _empty_date(item: dict) -> bool:
        d = item.get('inspection_date')
        if d is None:
            return True
        if isinstance(d, str) and d.strip() == '':
            return True
        return False

    @staticmethod
    def _non_empty_date(item: dict) -> bool:
        return not LabReportExtractor._empty_date(item)

    @staticmethod
    def _norm_blank(v):
        if v is None:
            return ''
        try:
            s = str(v).strip()
        except Exception:
            s = ''
        return s

    @staticmethod
    def _meta_equal(a: dict, b: dict) -> bool:
        keys = ['hospital_name', 'client_name', 'patient_name', 'header_shape']
        return all(LabReportExtractor._norm_blank(a.get(k)) == LabReportExtractor._norm_blank(b.get(k)) for k in keys)

    @staticmethod
    def _dedup_tests_by_code_unit(tests: list) -> list:
        if not isinstance(tests, list):
            return []
        seen = set()
        out = []
        for t in tests:
            if not isinstance(t, dict):
                continue
            key = (
                LabReportExtractor._norm_blank(t.get('code')),
                LabReportExtractor._norm_blank(t.get('unit')),
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(t)
        return out

    def merge_extractions(self, results: List[Dict[str, Any]], *, progress_cb: ProgressCB = None) -> MergeEnvelope:
        self._emit({'stage': 'merge', 'status': 'start', 'ts': self._ts(), 'count': len(results)}, progress_cb)
        _filtered = [r for r in results if not self._is_empty_tests(r)]
        pruned = len(results) - len(_filtered)

        _merged: List[Dict[str, Any]] = []
        for cur in _filtered:
            if not _merged:
                _merged.append(dict(cur))
                continue
            prev = _merged[-1]
            if self._non_empty_date(prev) and self._empty_date(cur) and self._meta_equal(prev, cur):
                prev_tests = prev.get('tests')
                if not isinstance(prev_tests, list):
                    prev_tests = []
                    prev['tests'] = prev_tests
                cur_tests = cur.get('tests') or []
                if isinstance(cur_tests, list):
                    prev_tests.extend(cur_tests)
            else:
                _merged.append(dict(cur))

        # 중복 제거 진행 상황 전달
        before_dedup = sum(len(i.get('tests') or []) for i in _merged)
        for item in _merged:
            item['tests'] = self._dedup_tests_by_code_unit(item.get('tests', []))
        after_dedup = sum(len(i.get('tests') or []) for i in _merged)
        self._emit({'stage': 'dedup', 'status': 'end', 'ts': self._ts(), 'before': before_dedup, 'after': after_dedup}, progress_cb)

        from app.models.envelopes import MergeData, MergeMeta, MergeEnvelope
        out = MergeEnvelope(
            stage='merge',
            data=MergeData(merged=_merged),
            meta=MergeMeta(
                pruned_empty=pruned,
                merged_len=len(_merged),
                before_dedup=before_dedup,
                after_dedup=after_dedup,
            ),
        )
        self._emit({'stage': 'merge', 'status': 'end', 'ts': self._ts(), 'pruned_empty': pruned, 'merged_len': len(_merged)}, progress_cb)
        return out

    def merge_extractions_stream(self, results: List[Dict[str, Any]]):
        evt = {'stage': 'merge', 'status': 'start', 'ts': self._ts(), 'count': len(results)}
        self._emit(evt)
        yield evt
        _filtered = [r for r in results if not self._is_empty_tests(r)]
        pruned = len(results) - len(_filtered)

        _merged: List[Dict[str, Any]] = []
        for cur in _filtered:
            if not _merged:
                _merged.append(dict(cur))
                continue
            prev = _merged[-1]
            if self._non_empty_date(prev) and self._empty_date(cur) and self._meta_equal(prev, cur):
                prev_tests = prev.get('tests')
                if not isinstance(prev_tests, list):
                    prev_tests = []
                    prev['tests'] = prev_tests
                cur_tests = cur.get('tests') or []
                if isinstance(cur_tests, list):
                    prev_tests.extend(cur_tests)
            else:
                _merged.append(dict(cur))

        before_dedup = sum(len(i.get('tests') or []) for i in _merged)
        for item in _merged:
            item['tests'] = self._dedup_tests_by_code_unit(item.get('tests', []))
        after_dedup = sum(len(i.get('tests') or []) for i in _merged)
        evt = {'stage': 'dedup', 'status': 'end', 'ts': self._ts(), 'before': before_dedup, 'after': after_dedup}
        self._emit(evt)
        yield evt

        from app.models.envelopes import MergeData, MergeMeta, MergeEnvelope
        out = MergeEnvelope(
            stage='merge',
            data=MergeData(merged=_merged),
            meta=MergeMeta(
                pruned_empty=pruned,
                merged_len=len(_merged),
                before_dedup=before_dedup,
                after_dedup=after_dedup,
            ),
        )
        evt = {'stage': 'merge', 'status': 'end', 'ts': self._ts(), 'pruned_empty': pruned, 'merged_len': len(_merged), 'result': out}
        self._emit(evt)
        yield evt


def create_default_lab_report_extractor(
    *,
    progress_cb: ProgressCB = None,
) -> LabReportExtractor:
    """기본 설정으로 LabReportExtractor를 생성하는 헬퍼."""
    return LabReportExtractor(progress_cb=progress_cb)
