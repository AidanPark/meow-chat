from __future__ import annotations
from app.models.envelopes import Envelope, ExtractionMeta, MergeEnvelope

from typing import Any, Callable, Dict, List, Optional
import json
import time
import asyncio

Event = Dict[str, Any]
ProgressCB = Optional[Callable[[Event], None]]


class OCRPipelineManager:
    """
    3단계 OCR 파이프라인 매니저:
    1) image_to_ocr(bytes) -> dict
    2) ocr_to_extraction(ocr_result_dict) -> dict
    3) merge_extractions(list[dict]) -> dict

    - 스트리밍/콜백 지원: 각 단계의 진행 상황을 이벤트(dict)로 외부에 알림
      이벤트 공통 필드 예: {
        'stage': 'preprocess' | 'ocr' | 'line_group' | 'extract' | 'merge' | 'dedup',
        'status': 'start' | 'progress' | 'end',
        'ts': <epoch_seconds>,
        ... (추가 메타데이터)
      }

    의존성은 생성자 주입으로 전달합니다. 값이 None이면 중앙 DI 프로바이더(app.core.deps)를 사용해 채웁니다.
    - preprocessor: ImagePreprocessor (기본: deps.get_image_preprocessor())
    - ocr_service: PaddleOCRService (기본: deps.get_ocr_service())
    - line_preproc: LinePreprocessor (기본: deps.get_line_preprocessor())
    - extractor: LabTableExtractor (기본: deps.get_extractor())
    """

    def __init__(
        self,
        *,
        preprocessor=None,
        ocr_service=None,
        line_preproc=None,
        extractor=None,
        do_preprocess_default: bool = True,
        progress_cb: ProgressCB = None,
        # 기본 구성 자동 생성 옵션
        lang: str = "korean",
        ip_settings: Optional[dict] = None,
        lp_settings: Optional[dict] = None,
        use_llm: bool = True,
        llm_model: str = "gpt-4.1-mini",
        api_key: Optional[str] = None,
        debug: bool = False,
    ) -> None:
        """
        OCRPipelineManager 생성자.

        - 의존성을 직접 주입하거나(None을 전달하면) 기본 구성을 자동으로 생성합니다.
        - 자동 생성 시 옵션(lang, debug, ip_settings, lp_settings, use_llm, llm_model, api_key)으로 세부 조정 가능.
        """

        # 필요 시 중앙 DI 프로바이더로 기본 구성 요소 주입 (lazy import)
        if preprocessor is None or ocr_service is None or line_preproc is None or extractor is None:
            try:
                # 중앙 DI: FastAPI 스타일 provider 사용
                from app.core.deps import (
                    get_image_preprocessor,
                    get_ocr_service,
                    get_line_preprocessor,
                    get_extractor,
                )

                if preprocessor is None:
                    preprocessor = get_image_preprocessor()
                if ocr_service is None:
                    ocr_service = get_ocr_service()
                if line_preproc is None:
                    line_preproc = get_line_preprocessor()
                if extractor is None:
                    extractor = get_extractor()
            except Exception:
                # DI 모듈 불가 시 기존 lazy 생성으로 폴백
                from app.services.analysis.image_preprocessor import ImagePreprocessor, Settings as IPSettings
                from app.services.ocr.paddle_ocr_service import PaddleOCRService
                from app.services.analysis.line_preprocessor import LinePreprocessor, Settings as LPSettings
                from app.services.analysis.reference.unit_lexicon import get_unit_lexicon
                import app.services.analysis.reference.code_lexicon as cl
                import app.services.analysis.lab_table_extractor as lte

                if preprocessor is None:
                    ip_kwargs = {"debug": debug}
                    if ip_settings:
                        ip_kwargs.update(ip_settings)
                    preprocessor = ImagePreprocessor(IPSettings(**ip_kwargs))

                if ocr_service is None:
                    ocr_service = PaddleOCRService(lang=lang)

                if line_preproc is None:
                    unit_lex = get_unit_lexicon()
                    lp_defaults = {
                        "order": "x_left",
                        "alpha": 0.7,
                        "debug": debug,
                        "normalize_units_first_pass": True,
                    }
                    if lp_settings:
                        lp_defaults.update(lp_settings)
                    line_preproc = LinePreprocessor(LPSettings(**lp_defaults), unit_lexicon=unit_lex)

                if extractor is None:
                    code_lexicon = cl.get_code_lexicon()
                    extractor = lte.LabTableExtractor(
                        settings=lte.Settings(use_llm=use_llm, debug=debug),
                        lexicon=code_lexicon,
                        resolver=cl.resolve_code,
                        api_key=api_key,
                        llm_model=llm_model,
                    )

        self.preprocessor = preprocessor
        self.ocr_service = ocr_service
        self.line_preproc = line_preproc
        self.extractor = extractor
        self.do_preprocess_default = do_preprocess_default
        self._progress_cb = progress_cb

    # ---------- DI 편의 생성자 ----------
    @classmethod
    def create_with_deps(
        cls,
        *,
        do_preprocess_default: bool = True,
        progress_cb: ProgressCB = None,
    ) -> "OCRPipelineManager":
        """중앙 DI 프로바이더(app.core.deps)를 통해 의존성을 내부에서 주입하여 매니저를 생성합니다.

        - 외부에서 개별 컴포넌트를 전달하지 않아도 되는 간편 생성자입니다.
        - 테스트나 커스터마이징이 필요하면 본 생성자 대신 __init__에 명시 주입하세요.
        """
        from app.core.deps import (
            get_image_preprocessor,
            get_ocr_service,
            get_line_preprocessor,
            get_extractor,
        )

        return cls(
            preprocessor=get_image_preprocessor(),
            ocr_service=get_ocr_service(),
            line_preproc=get_line_preprocessor(),
            extractor=get_extractor(),
            do_preprocess_default=do_preprocess_default,
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

    # ---------- 1) 이미지(bytes) -> OCR 결과 ----------
    def image_to_ocr(
        self,
        image_bytes: bytes,
        *,
        do_preprocess: Optional[bool] = None,
        preprocess_kwargs: Optional[dict] = None,
        progress_cb: ProgressCB = None,
    ) -> Any:
        """이미지 bytes를 받아(선택적 전처리 포함) 표준 dict를 반환합니다."""
        use_pre = self.do_preprocess_default if do_preprocess is None else bool(do_preprocess)
        data = image_bytes

        if use_pre and self.preprocessor is not None:
            self._emit({'stage': 'preprocess', 'status': 'start', 'ts': self._ts()}, progress_cb)
            kwargs = preprocess_kwargs or {}
            data = self.preprocessor.process_bytes(data, **kwargs)
            meta = {'bytes': len(data) if data else 0}
            self._emit({'stage': 'preprocess', 'status': 'end', 'ts': self._ts(), **meta}, progress_cb)

        self._emit({'stage': 'ocr', 'status': 'start', 'ts': self._ts()}, progress_cb)
        ocr_result_raw = self.ocr_service.run_ocr_from_bytes(data)
        # Pydantic 모델(envelope)만 지원. None/비-모델이면 빈 모델 생성
        try:
            from app.models.envelopes import OCRData, OCRMeta, OCRResultEnvelope
            if isinstance(ocr_result_raw, OCRResultEnvelope.__class__):
                # Runtime check for model instance is tricky; trust attributes instead
                pass
        except Exception:
            pass
        if hasattr(ocr_result_raw, 'data') and hasattr(ocr_result_raw, 'meta'):
            ocr_result = ocr_result_raw
            try:
                _data = getattr(ocr_result, 'data', None)
                _items = getattr(_data, 'items', None)
                items_len = len(_items) if _items else 0
            except Exception:
                items_len = 0
        else:
            from app.models.envelopes import OCRData, OCRMeta, OCRResultEnvelope
            ocr_result = OCRResultEnvelope(stage='ocr', data=OCRData(items=[]), meta=OCRMeta(items=0))
            items_len = 0
        self._emit({'stage': 'ocr', 'status': 'end', 'ts': self._ts(), 'items': items_len}, progress_cb)
        return ocr_result

    def image_to_ocr_stream(
        self,
        image_bytes: bytes,
        *,
        do_preprocess: Optional[bool] = None,
        preprocess_kwargs: Optional[dict] = None,
    ):
        """이벤트를 yield하는 제너레이터 버전("stream"). 마지막 이벤트에 result 포함."""
        use_pre = self.do_preprocess_default if do_preprocess is None else bool(do_preprocess)
        data = image_bytes

        if use_pre and self.preprocessor is not None:
            evt = {'stage': 'preprocess', 'status': 'start', 'ts': self._ts()}
            self._emit(evt)
            yield evt
            kwargs = preprocess_kwargs or {}
            data = self.preprocessor.process_bytes(data, **kwargs)
            evt = {'stage': 'preprocess', 'status': 'end', 'ts': self._ts(), 'bytes': len(data) if data else 0}
            self._emit(evt)
            yield evt

        evt = {'stage': 'ocr', 'status': 'start', 'ts': self._ts()}
        self._emit(evt)
        yield evt
        ocr_result_raw = self.ocr_service.run_ocr_from_bytes(data)
        if hasattr(ocr_result_raw, 'data') and hasattr(ocr_result_raw, 'meta'):
            ocr_result = ocr_result_raw
            try:
                _data = getattr(ocr_result, 'data', None)
                _items = getattr(_data, 'items', None)
                items_len = len(_items) if _items else 0
            except Exception:
                items_len = 0
        else:
            from app.models.envelopes import OCRData, OCRMeta, OCRResultEnvelope
            ocr_result = OCRResultEnvelope(stage='ocr', data=OCRData(items=[]), meta=OCRMeta(items=0))
            items_len = 0
        evt = {'stage': 'ocr', 'status': 'end', 'ts': self._ts(), 'items': items_len, 'result': ocr_result}
        self._emit(evt)
        yield evt

    async def image_to_ocr_async(
        self,
        image_bytes: bytes,
        *,
        do_preprocess: Optional[bool] = None,
        preprocess_kwargs: Optional[dict] = None,
        progress_cb: ProgressCB = None,
    ) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.image_to_ocr(
                image_bytes,
                do_preprocess=do_preprocess,
                preprocess_kwargs=preprocess_kwargs,
                progress_cb=progress_cb,
            ),
        )

    # ---------- 2) OCR 결과 -> 추출 dict ----------
    def ocr_to_extraction(self, ocr_result: Any, *, progress_cb: ProgressCB = None) -> Envelope[Dict[str, Any], ExtractionMeta]:
        from app.models.envelopes import Envelope, ExtractionMeta
        # 모델만 허용, 아니면 빈 모델 반환
        if not (hasattr(ocr_result, 'data') and hasattr(ocr_result, 'meta')):
            return Envelope[Dict[str, Any], ExtractionMeta](stage='extract', data={}, meta=ExtractionMeta(tests=0))
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

    # ---------- 3) 복수 추출 결과 병합 -> JSON ----------
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
        return not OCRPipelineManager._empty_date(item)

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
        return all(OCRPipelineManager._norm_blank(a.get(k)) == OCRPipelineManager._norm_blank(b.get(k)) for k in keys)

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
                OCRPipelineManager._norm_blank(t.get('code')),
                OCRPipelineManager._norm_blank(t.get('unit')),
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


def create_default_ocr_pipeline_manager(
    *,
    lang: str = "korean",
    ip_settings: Optional[dict] = None,
    lp_settings: Optional[dict] = None,
    use_llm: bool = True,
    llm_model: str = "gpt-4.1-mini",
    api_key: Optional[str] = None,
    debug: bool = False,
    progress_cb: ProgressCB = None,
) -> OCRPipelineManager:
    """
    호환성 유지를 위한 래퍼. 권장: OCRPipelineManager 생성자에 직접 옵션을 전달하세요.
    """
    return OCRPipelineManager(
        do_preprocess_default=True,
        progress_cb=progress_cb,
        lang=lang,
        ip_settings=ip_settings,
        lp_settings=lp_settings,
        use_llm=use_llm,
        llm_model=llm_model,
        api_key=api_key,
        debug=debug,
    )
