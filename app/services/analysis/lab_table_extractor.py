"""
반려동물 검사결과지(랩 리포트) 전용 테이블 추출기.

이 모듈은 PaddleOCRService가 생성한 라인 배열을 입력으로 받아, 규칙 기반으로
정규화된 JSON 구조로 변환하기 위한 높은 응집도의 클래스를 제공합니다.
이 클래스는 규칙, 검사코드 사전 사용, 헤더 검출, 열 경계(밴드) 추론,
메타데이터 추출 등의 도메인 로직을 한 곳에 캡슐화합니다.

참고
----
- 현재는 최소 골격 상태이며, 공개 API/설정/메서드 시그니처만 포함합니다.
- 실제 구현은 노트북 주도 개발 방식으로 단계별(5단계 → 13단계) 채워 넣습니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Callable
import logging
import re
from statistics import median
from functools import lru_cache
import os
import threading

# 선택적 OpenAI 클라이언트 (설치되지 않았을 수 있음)
try:  # pragma: no cover
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

try:
    # 검사코드 사전 모듈은 아래 헬퍼들을 제공합니다.
    from .reference.code_lexicon import get_code_lexicon
except Exception:  # pragma: no cover - allow import even before module is present in some envs
    get_code_lexicon = None  # type: ignore

# 코드 정규화/해석 모듈 (unit_normalizer와 동일한 분리 스타일)
try:
    from .code_normalizer import resolve_code_with_fallback as _resolve_code_norm
except Exception:  # pragma: no cover
    _resolve_code_norm = None  # type: ignore

# 단일 정규화 모듈 사용 (파편화 해결)
try:
    from .unit_normalizer import normalize_unit_simple
except Exception:  # pragma: no cover
    normalize_unit_simple = None  # type: ignore


# 가독성을 위한 타입 별칭
Line = Any  # 일반적으로 한 라인은 list[dict|str] 형태이나, 전/후처리에 따라 변형될 수 있음
Lines = List[Line]
DocumentResult = Dict[str, Any]
Intermediates = Dict[str, Any]


@dataclass
class Settings:
    """LabTableExtractor 설정값.

    사이트/병원/장비별로 조정 가능한 임계치와 도메인 휴리스틱을 보관합니다.
    """

    # 헤더 검출 관련 설정
    role_min_distinct_hits: int = 3
    header_search_up_lines: int = 3
    header_search_down_lines: int = 3

    # 제어 플래그
    use_llm: bool = False
    debug: bool = False
    canonicalize_codes: bool = True
    # LLM 동시성 제어 옵션
    enable_llm_lock: bool = True
    llm_max_concurrency: int = 2

    # 헤더 추론 보수 임계치 설정 (Step 7)
    min_rows_for_inference: int = 8
    short_table_threshold_bonus: float = 0.05
    unit_threshold: float = 0.70
    reference_threshold: float = 0.50
    result_threshold: float = 0.60
    max_date_ratio_for_result: float = 0.10
    # 결과 보강(강제) 휴리스틱
    fallback_result_min_ratio: float = 0.45
    prefer_result_left_of_unit_bonus: float = 0.05
    fallback_consider_neighbors: int = 1

    # 밴드 배정 전략
    # - band_assignment_mode: "hybrid"(기본) | "include" | "nearest"
    #   * hybrid   : 밴드 내부 포함(L <= xc < R) 우선, 미포함 토큰은 최근접 중심으로 배정
    #   * include  : 밴드 내부 포함 방식만 사용(폴백 없음)
    #   * nearest  : 항상 최근접 중심(샘플 열 x-중앙값)으로만 배정, 밴드 포함 여부는 무시
    band_assignment_mode: str = "nearest"

    # 헤더-바디 일치율 게이트 설정 (OCR 헤더 신뢰성 검사)
    header_alignment_overall_threshold: float = 0.65
    header_alignment_preview_rows: int = 20

    # 헤더 키워드 세트 (역할명 -> 동의어 목록). 비교는 소문자 기준 권장.
    header_synonyms: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "name": ["name", "검사항목", "항목", "항목명", "검사명", "test", "parameter"],
            "result": [
                "result",
                "결과",
                "결과값",
                "결과치",
                "측정값",
                "측정치",
                "값",
                "value",
                "수치",
            ],
            "unit": ["unit", "단위"],
            "reference": [
                "reference",
                "참고치",
                "참고범위",
                "참조치",
                "참조범위",
                "정상범위",
                "정상치",
                "기준치",
                "ref",
                "range",
                "ref. range",
                "ref.range",
            ],
            "min": ["min", "최소", "최저", "하한", "하한치", "lo", "lower"],
            "max": ["max", "최대", "최고", "상한", "상한치", "hi", "upper"],
            "date": ["date", "검사일", "검사일자", "채혈일", "일자", "yyy", "mm", "dd"],
        }
    )

    # 역할별 (선택) 정규식 패턴 (예: 날짜 형식)
    header_regex: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "date": [
                r"\b\d{4}[-./]\d{1,2}[-./]\d{1,2}\b",
                r"\b\d{2}[-./]\d{1,2}[-./]\d{1,2}\b",
            ]
        }
    )

    # 메타데이터: 이름 결합 시 기하 기반 간격 제한(라벨 오른쪽 값 수집 시 사용)
    # - 한 줄 내 토큰 간 gap의 중앙값을 구해, 그 배수를 넘는 큰 간격이 나오면 다른 필드로 간주하고 결합을 중단
    # - 너무 작은 해상도에서의 오탐을 막기 위해 최소 px 임계도 병행 적용
    name_concat_max_gap_multiplier: float = 1.8  # 중앙값 gap의 최대 허용 배수
    name_concat_min_gap_px: int = 16             # 최소 허용 gap(px)
    name_concat_max_tokens: int = 3              # 라벨 우측에서 결합할 최대 토큰 수(이름은 보통 1~2개)
    name_block_long_numeric_len: int = 6         # 이 길이 이상의 순수 숫자 토큰이 오면 중단 (ID 등)
    name_stop_on_date_like: bool = True          # 날짜 유사 토큰이 나오면 결합 중단


class LabTableExtractor:
    """랩 테이블에 대해 5–12단계를 오케스트레이션하는 규칙 우선 추출기.

    공개 진입점
    -----------
    extract_from_lines(lines, return_intermediates=False)
        OCR 라인 배열을 입력으로 받아 정규화된 JSON으로 변환합니다.

    의존성
    ------
    - lexicon: 검사 항목 코드를 해석하기 위한 사전
    - logger: 선택적 로거 (기본은 모듈 로거)
    - api_key: 선택적 OpenAI API 키 (백업 추론용 LLM 활성화)
    """

    # 클래스 전역 LLM 동시성 제어자 (lazy-init)
    _LLM_SEMAPHORE: Optional[threading.Semaphore] = None
    _LLM_SEMAPHORE_MAX: Optional[int] = None

    def __init__(
        self,
        settings: Optional[Settings] = None,
        *,
        lexicon: Optional[Dict[str, Any]] = None,
        resolver: Optional[Callable[[str, Dict[str, Any]], Optional[str]]] = None,
        logger: Optional[logging.Logger] = None,
        api_key: Optional[str] = None,
        llm_model: Optional[str] = None,
    ) -> None:
        self.settings = settings or Settings()
        self.logger = logger or logging.getLogger(__name__)
        # LLM 클라이언트는 내부에서 관리한다.
        self.llm_model = llm_model or "gpt-4.1-mini"
        self.llm = None
        # 우선순위: 전달된 api_key > 환경변수 OPENAI_API_KEY
        self.llm_api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if self.llm_api_key and OpenAI is not None:
            try:
                self.llm = OpenAI(api_key=self.llm_api_key)  # type: ignore[call-arg]
            except Exception:
                # 클라이언트 초기화 실패 시, LLM 기능은 비활성화
                self.logger.warning("OpenAI 클라이언트 초기화 실패: LLM 기능 비활성화")
                self.llm = None
        self._ext_resolver = resolver

        # LLM 동시성 제어 - 인스턴스 락 및 클래스 전역 세마포어
        try:
            self._llm_lock = threading.RLock() if bool(getattr(self.settings, "enable_llm_lock", True)) else None
        except Exception:
            self._llm_lock = None
        # 클래스 전역 세마포어의 lazy-init 및 재설정
        try:
            if getattr(self.settings, "use_llm", False):
                m = int(getattr(self.settings, "llm_max_concurrency", 2) or 0)
                if m > 0:
                    cls = self.__class__
                    # 기존 값과 다르면 재생성
                    if getattr(cls, "_LLM_SEMAPHORE", None) is None or getattr(cls, "_LLM_SEMAPHORE_MAX", None) != m:
                        cls._LLM_SEMAPHORE = threading.Semaphore(m)
                        cls._LLM_SEMAPHORE_MAX = m
        except Exception:
            # 동시성 제어는 옵션이므로 실패해도 전체 파이프라인을 막지 않는다
            pass

        # 사전은 가능한 경우 지연 초기화합니다.
        if lexicon is not None:
            self.lexicon = lexicon
        else:
            if get_code_lexicon is not None:
                try:
                    self.lexicon = get_code_lexicon()
                except Exception:  # pragma: no cover
                    self.logger.debug("검사항목 사전 생성 실패: 빈 사전 사용")
                    self.lexicon = {}
            else:
                self.lexicon = {}

    # -----------------------
    # Public Orchestration API
    # -----------------------
    def extract_from_lines(
        self, lines: Lines, return_intermediates: bool = False
    ) -> DocumentResult | Tuple[DocumentResult, Intermediates]:
        """엔드투엔드 추출 (현재 6단계까지 적용).

        매개변수
        --------
        lines: list
            OCR에서 그룹핑된 라인 배열 (각 라인은 토큰 dict/문자열의 배열)
        return_intermediates: bool
            True면 디버깅용 중간 산출물도 함께 반환

        반환값
        ------
        DocumentResult 또는 (DocumentResult, Intermediates)
        """
        doc = self._init_doc_result()

        # 전체 문서 라인에 대한 첫 토큰 코드 해석 스캔(디버그용)
        # - debug_step5에서 "문서 전체"의 코드 인식 실패 라인을 보여주기 위해 사용
        code_resolve_scan_all: List[Tuple[int, str, Optional[str], str]] = []
        try:
            for i, l in enumerate(lines):
                ftxt = self._first_token_text(l)
                rcode = self._resolve_code(ftxt) if ftxt else None
                preview = self._line_join_texts(l)
                code_resolve_scan_all.append((i, ftxt, rcode, preview))
        except Exception:
            code_resolve_scan_all = []

    # -----------------------
    # Step 5) 테이블 바디 시작 검출 및 바디 필터링
        # - 라인의 첫 토큰이 검사코드로 해석되는 첫 라인이 바디 시작
        # - 바디 시작 이후, 검사코드로 해석되지 않는 라인은 바디에서 제외
        # - canonicalize_codes=True 인 경우, 첫 토큰을 정규화된 코드로 제자리 치환
        # -----------------------
        debug_preview: List[Tuple[int, str, Optional[str]]] = []
        if self.settings.debug and return_intermediates:
            for i, l in enumerate(lines[:40]):
                f = self._first_token_text(l)
                debug_preview.append((i, f, self._resolve_code(f) if f else None))
        body_start = self._find_table_body_start(lines)
        body_lines: Lines = []
        dropped: List[Tuple[int, str, str]] = []
        if body_start is not None:
            body_lines, dropped = self._filter_body_by_codes(lines, body_start)
        else:
            # 바디 시작 미검출: 이후 단계는 수행하지 않음
            if return_intermediates:
                return doc, {
                    "settings": self.settings,
                    "body_start": None,
                    "body_lines_count": 0,
                    "dropped": dropped,
                    "debug_preview": debug_preview,
                    "code_resolve_scan_all": code_resolve_scan_all,
                    "message": "바디 시작 미검출",
                }
            return doc

    # -----------------------
    # Step 6) 테이블 헤더 라인 검증
        # - 기본 후보: 바디 시작 바로 위 라인
        # - 설정값에 따라 위/아래로 소폭 탐색하며, 동의어/정규식 매칭 점수가 가장 높은 라인을 채택
        # - 유효성: 서로 다른 역할(role)의 적중 수가 role_min_distinct_hits 이상
        # -----------------------
        header_idx: Optional[int] = None
        header_roles: Any = {}
        header_line: Optional[Line] = None
        header_source: str = "none"  # 'ocr' | 'inferred' | 'llm' | 'none'

        try:
            header_idx, header_roles = self._detect_and_validate_header(lines, body_start)
            if header_idx is not None and 0 <= header_idx < len(lines):
                header_line = lines[header_idx]
        except NotImplementedError:
            # 아직 미구현인 경우에도 인터페이스는 유지
            header_idx, header_roles, header_line = None, {}, None
        except Exception:
            header_idx, header_roles, header_line = None, {}, None

        # 헤더 유효성 판정 (OCR 기반)
        ocr_header_valid = False
        try:
            if header_roles:
                # dict 기반 가정 제거: 임시로 dict로 온 경우 대비
                if isinstance(header_roles, dict):
                    distinct_ocr = len([r for r in header_roles.keys() if header_roles.get(r)])
                else:
                    # 표준화 전이므로 보수적으로 True/False만 산정
                    distinct_ocr = 1
                ocr_header_valid = distinct_ocr >= int(self.settings.role_min_distinct_hits)
        except Exception:
            ocr_header_valid = False

        pre_llm_roles: Optional[Dict[str, Any]] = None
        pre_llm_policy_valid: Optional[bool] = None
        llm_trigger_cause: Optional[str] = None  # 'policy_invalid' | 'no_rule_header'
        llm_input_sample: Optional[List[List[str]]] = None
        inferred_input_sample: Optional[List[List[str]]] = None

        if ocr_header_valid:
            header_source = "ocr"
        else:
            # 헤더가 없는 경우: 규칙 기반 헤더 추론
            try:
                inferred_roles, inferred_sample = self._infer_header_if_missing(body_lines)
            except NotImplementedError:
                inferred_roles, inferred_sample = {}, []
            except Exception:
                inferred_roles, inferred_sample = {}, []

            if inferred_roles:
                pre_llm_roles = inferred_roles
                header_roles = inferred_roles
                header_idx = None
                header_line = None
                header_source = "inferred"
                inferred_input_sample = inferred_sample or []
                # 정책 기준으로 신뢰 불가하고 LLM 사용이 켜져 있으면 백업 시도
                try:
                    policy_ok = self._is_policy_valid(header_roles)
                except Exception:
                    policy_ok = False
                pre_llm_policy_valid = bool(policy_ok)
                if not policy_ok and getattr(self.settings, "use_llm", False) and getattr(self, "llm", None):
                    try:
                        llm_roles, llm_sample = self._infer_header_with_llm(lines, body_lines)
                        if llm_roles:
                            header_roles = llm_roles
                            header_source = "llm"
                            llm_trigger_cause = "policy_invalid"
                            llm_input_sample = llm_sample or []
                    except Exception:
                        pass
            else:
                # 선택적 LLM 훅 (기본 비활성화)
                if getattr(self.settings, "use_llm", False) and getattr(self, "llm", None):
                    try:
                        llm_roles, llm_sample = self._infer_header_with_llm(lines, body_lines)
                        if llm_roles:
                            header_roles = llm_roles
                            header_source = "llm"
                            llm_trigger_cause = "no_rule_header"
                            llm_input_sample = llm_sample or []
                    except Exception:
                        pass

        # 헤더 표준화: 이후 단계에서는 표준 구조(list[dict])만 사용
        try:
            header_roles = self._standardize_header_roles_struct(header_roles)
        except Exception:
            header_roles = []

        # 헤더-바디 일치율 게이트: OCR 헤더가 바디 타입 분포와 안 맞으면 규칙 추론으로 전환
        header_alignment: Dict[str, Any] = {}
        if header_source == "ocr" and header_roles and body_lines:
            try:
                score_overall, detail = self._evaluate_header_body_alignment(header_roles, body_lines,
                                                                             max_rows=int(self.settings.header_alignment_preview_rows))
                header_alignment = {
                    "score_overall": score_overall,
                    "details": detail,
                    "threshold": float(self.settings.header_alignment_overall_threshold),
                    "fallback_to_inferred": False,
                }
                if score_overall < float(self.settings.header_alignment_overall_threshold):
                    # 기록 후 규칙 기반으로 전환 시도
                    pre_roles = header_roles
                    pre_source = header_source
                    try:
                        inferred_roles, inferred_sample = self._infer_header_if_missing(body_lines)
                    except Exception:
                        inferred_roles, inferred_sample = {}, []
                    if inferred_roles:
                        header_roles = self._standardize_header_roles_struct(inferred_roles)
                        header_source = "inferred"
                        header_alignment["fallback_to_inferred"] = True
                        inferred_input_sample = inferred_sample or inferred_input_sample or []
                        pre_llm_roles = pre_roles if pre_llm_roles is None else pre_llm_roles
                        pre_llm_policy_valid = self._is_policy_valid(pre_roles)
                        llm_trigger_cause = llm_trigger_cause  # no change
                    else:
                        # 전환 실패 시 그대로 유지하되 정보만 남김
                        header_alignment["fallback_to_inferred"] = False
            except Exception:
                # 평가 실패 시 게이트 생략
                pass

        # 7) 메타데이터 추출 (헤더-이상 상단영역). 바디가 있어야 시행.
        meta: Dict[str, Any] = {}
        meta_dbg: Dict[str, Any] = {}
        try:
            if body_start is not None:
                meta, meta_dbg = self._extract_metadata_above_body(lines, header_idx, body_start)
                # 문서 결과에도 채워둠 (불확실 시 None 유지)
                doc.update({
                    k: v for k, v in meta.items() if k in ("hospital_name", "client_name", "patient_name", "inspection_date")
                })
        except Exception:
            meta_dbg = {"meta_error": True}

        # 8) Geometry-only Interim/Filling
        # - 헤더 의미론을 사용하지 않고, 바디의 토큰 x-좌표만으로 열 밴드를 추정합니다.
        # - 각 라인에서 밴드에 해당하는 값이 비어 있으면 'unknown'으로 채웁니다.
        interim_rows: List[Dict[str, Any]] = []
        filled_rows: List[Dict[str, Any]] = []
        try:
            if body_lines:
                # Header-anchored, pure-geometry interim builder returns rows and debug info
                build_result = self._build_interim_table(body_lines, header_roles)
                if isinstance(build_result, tuple):
                    interim_rows, step8_dbg = build_result
                else:
                    interim_rows, step8_dbg = build_result, {"sample_count": None}

                # 샘플 수 0개면 실패 처리: 유효하지 않은 문서로 간주하고 조기 반환
                if isinstance(step8_dbg, dict) and step8_dbg.get("sample_count") == 0:
                    if return_intermediates:
                        intermediates: Intermediates = {
                            "settings": self.settings,
                            "body_start": body_start,
                            "body_lines_count": len(body_lines),
                            "body_lines": body_lines,
                            "dropped": dropped,
                            "debug_preview": debug_preview,
                            "code_resolve_scan_all": code_resolve_scan_all,
                            # step 6
                            "header_index": header_idx,
                            "header_line": header_line,
                            "header_roles": header_roles,
                            "header_source": header_source,
                            "header_alignment": header_alignment,
                            # step 7 meta (가능한 범위만 보존)
                            "meta_candidates": meta_dbg.get("candidates") if isinstance(meta_dbg, dict) else None,
                            "meta_scanned_count": meta_dbg.get("scanned_count") if isinstance(meta_dbg, dict) else None,
                            "meta_region_end_index": meta_dbg.get("end_index") if isinstance(meta_dbg, dict) else None,
                            # step 8 실패 정보
                            "interim_rows": [],
                            "filled_rows": [],
                            "step8_debug": step8_dbg,
                            "step8_failed": "no_band_samples",
                            "message": "Step 8: 샘플 0개로 실패(유효하지 않은 문서)"
                        }
                        return doc, intermediates
                    return doc

                filled_rows = self._fill_unknowns(interim_rows, lines, body_lines, header_roles)
        except Exception:
            # 실패 시 비워둠(디버그 용이)
            interim_rows, filled_rows = [], []

        # 9) 라인-열 길이 정규화 (뒤에서 잘라 맞춤)
        # - 헤더 역할(col_index) 기준 열 개수보다 많은 셀이 있는 행은 꼬리쪽을 제거하여 맞춘다.
        step9_rows: List[Dict[str, Any]] = []
        try:
            if filled_rows:
                step9_rows = self._truncate_to_header_columns(filled_rows, header_roles)
            else:
                step9_rows = []
        except Exception:
            step9_rows = filled_rows or []

        # 10) Reference → Min/Max 분리 (가능한 경우)
        step10_rows: List[Dict[str, Any]] = []
        try:
            if step9_rows:
                step10_rows = self._split_reference_range(step9_rows)
            else:
                step10_rows = []
        except Exception:
            step10_rows = step9_rows or []

        # 11) Unit/Result 정규화
        step11_rows: List[Dict[str, Any]] = []
        try:
            if step10_rows:
                step11_rows = self._normalize_unit_and_result(step10_rows)
            else:
                step11_rows = []
        except Exception:
            step11_rows = step10_rows or []

        # 12) Final JSON shaping and validation
        final_doc: DocumentResult = {}
        qa_summary: Dict[str, Any] = {}
        try:
            final_doc = self._to_final_json(meta, step11_rows)
            # Step 12: UNKNOWN 제거, confidence 필터, 코드 중복 제거(하단 우선)
            try:
                final_doc, step12_stats = self._apply_step12_filters(final_doc, header_roles)
            except Exception:
                step12_stats = {
                    "removed_unknown": None,
                    "removed_low_conf": None,
                    "dedup_removed": None,
                    "conf_threshold": 0.94,
                }
            # 간단한 QA: 잘린 행 수, unit 정규화 커버리지, result 숫자화 커버리지 + step12 요약
            n_rows = len(step11_rows)
            truncated = sum(1 for r in step9_rows if isinstance(r, dict) and r.get("_row_fix") == "truncate_tail") if step9_rows else 0
            unit_canon_cnt = sum(1 for r in step11_rows if isinstance(r, dict) and r.get("unit_canonical"))
            result_norm_cnt = sum(1 for r in step11_rows if isinstance(r, dict) and r.get("result_norm"))
            qa_summary = {
                "rows": n_rows,
                "truncated_rows": truncated,
                "unit_canonical_coverage": (unit_canon_cnt, n_rows),
                "result_norm_coverage": (result_norm_cnt, n_rows),
                "step12_removed_unknown": step12_stats.get("removed_unknown"),
                "step12_removed_low_conf": step12_stats.get("removed_low_conf"),
                "step12_dedup_removed": step12_stats.get("dedup_removed"),
                "step12_conf_threshold": step12_stats.get("conf_threshold"),
            }
        except Exception:
            final_doc = doc

        if return_intermediates:
            intermediates: Intermediates = {
                "settings": self.settings,
                "body_start": body_start,
                "body_lines_count": len(body_lines),
                "body_lines": body_lines,
                "dropped": dropped,
                "debug_preview": debug_preview,
                # 전체 문서 코드 해석 스캔 결과(라인 인덱스, 첫 토큰, 해석 코드, 라인 프리뷰)
                "code_resolve_scan_all": code_resolve_scan_all,
                # step 6
                "header_index": header_idx,
                "header_line": header_line,
                "header_roles": header_roles,
                # LLM 사용 시 디버깅을 위해 규칙 기반(LLM 이전) 결과와 사유 보존
                "inferred_roles_before_llm": pre_llm_roles,
                "pre_llm_policy_valid": pre_llm_policy_valid,
                "llm_triggered": header_source == "llm",
                "llm_trigger_cause": llm_trigger_cause,
                "llm_input_sample": llm_input_sample,
                "inferred_input_sample": inferred_input_sample,
                # 두 가지 기준을 함께 제공: (1) 개수룰, (2) 정책룰. 기본 header_valid는 정책룰을 따름
                "header_valid_distinct_rule": (lambda _m: (len(_m) >= int(self.settings.role_min_distinct_hits)))(self._roles_to_mapping(header_roles)),
                "header_valid": (lambda _m: (bool(_m.get("name")) and bool(_m.get("unit")) and bool(_m.get("result")) and
                                              bool(_m.get("reference") or (_m.get("min") and _m.get("max"))) and
                                              bool((_m.get("unit") or {}).get("meets_threshold", True)) and
                                              bool((_m.get("result") or {}).get("meets_threshold", True)) and
                                              bool((_m.get("reference") or {}).get("meets_threshold", True) or (_m.get("min") and _m.get("max")))))(self._roles_to_mapping(header_roles)),
                "header_source": header_source,
                "header_alignment": header_alignment,
                # step 7 meta
                "meta_candidates": meta_dbg.get("candidates") if isinstance(meta_dbg, dict) else None,
                "meta_scanned_count": meta_dbg.get("scanned_count") if isinstance(meta_dbg, dict) else None,
                "meta_region_end_index": meta_dbg.get("end_index") if isinstance(meta_dbg, dict) else None,
                # step 8 interim/filling
                "interim_rows": interim_rows,
                "filled_rows": filled_rows,
                # step 8 debug (샘플/중심 등)
                "step8_debug": locals().get("step8_dbg"),
                # step 9 truncate to header columns
                "step9_rows": step9_rows,
                # step 10 split reference
                "step10_rows": step10_rows,
                # step 11 normalize unit/result
                "step11_rows": step11_rows,
                # step 12 final
                "final_doc": final_doc,
                "step12_stats": step12_stats,
                "qa_summary": qa_summary,
            }
            return final_doc, intermediates
        # 반환 인터미디엇이 아닌 경우에도 메타데이터는 채워둔다.
        return final_doc or doc

    def extract(self, lines: Lines) -> DocumentResult:
        """Convenience API: Run extract_from_lines and return a schema-shaped final JSON.

        Guarantees the following on return, even if intermediate steps fail:
        - Always returns a dict with keys: hospital_name, client_name, patient_name, inspection_date, tests
        - If metadata detection fails, meta fields are empty strings ""
        - If data detection fails, tests is an empty list []

        Parameters
        ----------
        lines: list
            OCR-grouped lines to process

        Returns
        -------
        DocumentResult
            { "hospital_name": str, "client_name": str, "patient_name": str, "inspection_date": str, "tests": [ ... ] }
        """
        # 1) Execute the main pipeline with intermediates for robustness
        final_doc: DocumentResult = {}
        intermediates: Intermediates | Dict[str, Any] = {}
        try:
            result = self.extract_from_lines(lines, return_intermediates=True)
            # Expected form: (final_doc, intermediates)
            if isinstance(result, tuple) and len(result) == 2:
                final_doc, intermediates = result  # type: ignore[assignment]
            elif isinstance(result, dict):
                final_doc = result
            else:
                final_doc = {}
        except Exception:
            final_doc = {}
            intermediates = {}

        # 2) Prefer the pipeline's final_doc; fallback to intermediates' snapshot
        if not isinstance(final_doc, dict) or not final_doc:
            try:
                if isinstance(intermediates, dict):
                    maybe = intermediates.get("final_doc")
                    if isinstance(maybe, dict):
                        final_doc = maybe
            except Exception:
                final_doc = {}

        # 3) Shape the output, coercing meta defaults and ensuring tests list exists
        out: DocumentResult = {
            "hospital_name": "",
            "client_name": "",
            "patient_name": "",
            "inspection_date": "",
            "tests": [],
        }

        def _str_or_empty(v: Any) -> str:
            try:
                if v is None:
                    return ""
                s = str(v)
                return s if s is not None else ""
            except Exception:
                return ""

        if isinstance(final_doc, dict):
            out["hospital_name"] = _str_or_empty(final_doc.get("hospital_name"))
            out["client_name"] = _str_or_empty(final_doc.get("client_name"))
            out["patient_name"] = _str_or_empty(final_doc.get("patient_name"))
            out["inspection_date"] = _str_or_empty(final_doc.get("inspection_date"))

            raw_tests = final_doc.get("tests")
            if isinstance(raw_tests, list):
                shaped_tests: List[Dict[str, Any]] = []
                for t in raw_tests:
                    if not isinstance(t, dict):
                        continue
                    shaped_tests.append({
                        "code": t.get("code"),
                        "unit": t.get("unit"),
                        "reference_min": t.get("reference_min"),
                        "reference_max": t.get("reference_max"),
                        "value": t.get("value"),
                    })
                out["tests"] = shaped_tests

        return out

    # -----------------------
    # Minimal utilities
    # -----------------------
    @staticmethod
    def _token_text(tok: Any) -> str:
        if isinstance(tok, dict):
            return str(tok.get("text", ""))
        return str(tok)

    @classmethod
    def _first_token_text(cls, line: Line) -> str:
        if isinstance(line, (list, tuple)) and len(line) > 0:
            return cls._token_text(line[0])
        if isinstance(line, dict):
            return cls._token_text(line)
        return ""

    @classmethod
    def _line_join_texts(cls, line: Line, sep: str = " | ") -> str:
        if isinstance(line, (list, tuple)):
            return sep.join([cls._token_text(t) for t in line])
        return cls._token_text(line)

    @staticmethod
    def _replace_first_token_text_inplace(line: Line, new_text: str) -> None:
        try:
            if isinstance(line, (list, tuple)) and len(line) > 0:
                first = line[0]
                if isinstance(first, dict):
                    first["text"] = new_text
                else:
                    line[0] = new_text  # type: ignore[index]
            elif isinstance(line, dict):
                line["text"] = new_text
        except Exception:
            # 예외 케이스(노이즈 타입)에도 관대하게 처리
            pass

    @staticmethod
    def _with_canonical_first_token(line: Line, new_text: str) -> Line:
        """Return a shallow-cloned line whose 첫 토큰 텍스트만 교체한다.

        원본 line 객체는 수정되지 않는다."""
        try:
            if isinstance(line, (list, tuple)):
                cloned: List[Any] = []
                for idx, tok in enumerate(line):
                    if idx == 0:
                        if isinstance(tok, dict):
                            new_tok = dict(tok)
                            new_tok["text"] = new_text
                        else:
                            new_tok = new_text
                    else:
                        new_tok = dict(tok) if isinstance(tok, dict) else tok
                    cloned.append(new_tok)
                return cloned
            if isinstance(line, dict):
                new_line = dict(line)
                new_line["text"] = new_text
                return new_line
        except Exception:
            # 복제 과정에서 문제가 생기면 원본을 그대로 반환해 추후 단계에서 처리
            pass
        return line

    # -----------------------
    # Header roles standardization helpers
    # -----------------------
    @staticmethod
    def _standardize_header_roles_struct(header_roles: Any) -> List[Dict[str, Any]]:
        """Normalize various header_roles shapes into a standard list of dicts:
        [ { 'role': str, 'col_index': int, ... }, ... ] sorted by col_index.

        Accepts:
        - dict role -> info(dict with col_index)
        - dict index(int) -> role(str)
        - already-standard list of dicts
        Returns an empty list on invalid input.
        """
        out: List[Dict[str, Any]] = []
        try:
            # Already a list of dicts
            if isinstance(header_roles, list) and all(isinstance(x, dict) for x in header_roles):
                for x in header_roles:
                    role = str(x.get("role", "")).strip() if isinstance(x, dict) else ""
                    ci = x.get("col_index") if isinstance(x, dict) else None
                    if role and isinstance(ci, int):
                        # preserve extra fields
                        out.append(dict(x))
                # sort by col_index
                out.sort(key=lambda z: int(z.get("col_index", 0)))
                return out
            # role -> info
            if isinstance(header_roles, dict) and header_roles:
                # detect dict[int->str]
                if all(isinstance(k, int) for k in header_roles.keys()) and all(isinstance(v, str) for v in header_roles.values()):
                    for idx, role in header_roles.items():
                        out.append({"role": role, "col_index": int(idx)})
                    out.sort(key=lambda z: int(z.get("col_index", 0)))
                    return out
                # dict[str->dict]
                if all(isinstance(k, str) for k in header_roles.keys()):
                    for role, info in header_roles.items():
                        if not isinstance(info, dict):
                            continue
                        if "col_index" not in info:
                            continue
                        ci = info.get("col_index")
                        if not isinstance(ci, int):
                            try:
                                ci = int(ci)  # type: ignore[assignment]
                            except Exception:
                                continue
                        merged = dict(info)
                        merged.setdefault("role", role)
                        merged["col_index"] = int(ci)
                        out.append(merged)
                    out.sort(key=lambda z: int(z.get("col_index", 0)))
                    return out
        except Exception:
            pass
        return []

    @staticmethod
    def _roles_to_mapping(header_roles: Any) -> Dict[str, Dict[str, Any]]:
        """Build a role->info mapping from the standard list or legacy dict.
        Ensures info contains 'col_index' int and 'role'.
        """
        try:
            if isinstance(header_roles, list) and all(isinstance(x, dict) for x in header_roles):
                m: Dict[str, Dict[str, Any]] = {}
                for x in header_roles:
                    role = str(x.get("role", "")).strip()
                    if not role:
                        continue
                    ci = x.get("col_index")
                    if not isinstance(ci, int):
                        try:
                            ci = int(ci)  # type: ignore[assignment]
                        except Exception:
                            continue
                    info = dict(x)
                    info["role"] = role
                    info["col_index"] = int(ci)
                    m[role] = info
                return m
            if isinstance(header_roles, dict) and header_roles:
                # dict[str->dict] preferred
                if all(isinstance(k, str) for k in header_roles.keys()):
                    m = {}
                    for role, info in header_roles.items():
                        if not isinstance(info, dict):
                            continue
                        ci = info.get("col_index")
                        if not isinstance(ci, int):
                            try:
                                ci = int(ci)  # type: ignore[assignment]
                            except Exception:
                                continue
                        merged = dict(info)
                        merged.setdefault("role", role)
                        merged["col_index"] = int(ci)
                        m[role] = merged
                    return m
                # dict[int->str]
                if all(isinstance(k, int) for k in header_roles.keys()) and all(isinstance(v, str) for v in header_roles.values()):
                    return {v: {"role": v, "col_index": int(k)} for k, v in header_roles.items()}
        except Exception:
            pass
        return {}

    # -----------------------
    # 코드 해석기 (모듈 위임)
    # -----------------------
    def _resolve_code(self, text: str) -> Optional[str]:
        """검사코드 텍스트를 사전 기준으로 해석해 표준 코드 문자열을 반환.

        구현은 분리된 code_normalizer 모듈에 위임한다.
        """
        if _resolve_code_norm is None:
            return None
        try:
            return _resolve_code_norm(text, self.lexicon, ext_resolver=self._ext_resolver)
        except Exception:
            return None

    # -----------------------
    # Planned pipeline steps (stubs)
    # -----------------------
    def _init_doc_result(self) -> DocumentResult:
        """초기 결과 컨테이너를 생성한다(hospital/client/patient/date/tests)."""
        return {
            "hospital_name": None,
            "client_name": None,
            "patient_name": None,
            "inspection_date": None,
            "tests": [],
        }

    def _find_table_body_start(self, lines: Lines) -> Optional[int]:
        """위에서부터 스캔하여 첫 토큰이 "검사항목 코드"로 해석되는 첫 라인의 인덱스를 찾는다.

        반환값:
          - int: 바디 시작 라인 인덱스
          - None: 미검출
        """
        # 사전/리졸버가 없으면 동작 불가 -> None 반환
        if not self.lexicon:
            return None

        for idx, line in enumerate(lines):
            first = self._first_token_text(line)
            if not first:
                continue
            code = self._resolve_code(first)
            if code:
                return idx
        return None

    def _filter_body_by_codes(
        self, lines: Lines, start_idx: int
    ) -> Tuple[Lines, List[Tuple[int, str, str]]]:
        """start_idx 이후 라인에서 첫 토큰이 검사코드로 해석되는 라인만 남긴다.

        동작:
          - 해석 성공 시, settings.canonicalize_codes=True이면 첫 토큰 텍스트를 해석된 코드로 치환
          - 해석 실패 라인은 dropped 목록에 (라인인덱스, 첫토큰텍스트, 라인전체텍스트)로 기록

        반환:
          - (body_lines, dropped_debug)
        """
        body: Lines = []
        dropped: List[Tuple[int, str, str]] = []

        if not self.lexicon:
            return body, dropped

        for idx in range(start_idx, len(lines)):
            line = lines[idx]
            first = self._first_token_text(line)
            code = self._resolve_code(first) if first else None

            if code:
                if self.settings.canonicalize_codes:
                    canonical_line = self._with_canonical_first_token(line, code)
                    body.append(canonical_line)
                else:
                    body.append(line)
            else:
                dropped.append((idx, first, self._line_join_texts(line)))

        return body, dropped

    def _detect_and_validate_header(
        self, lines: Lines, body_start_idx: int = -1
    ) -> Tuple[Optional[int], Dict[str, Any]]:
        """바디 시작 인근에서 헤더 라인을 검출하고 역할 키워드 적중으로 유효성 확인.

        전략:
        - 기본 후보는 body_start_idx - 1 이지만, 설정값에 따라 위/아래로 소폭 탐색
        - 각 후보 라인에 대해 role 동의어/정규식 적중을 집계하고, 상이한 역할 수가 가장 큰 라인을 채택
        - 유효 조건: 상이한 역할 수 >= role_min_distinct_hits

        반환값
        ------
        (header_index, header_roles)
            header_roles: 역할 → 근거/매핑 정보(dict)
        """
        # 기본값(-1) 또는 범위를 벗어난 경우, 바디 시작을 자동 탐지하여 사용
        if body_start_idx is None or body_start_idx < 0 or body_start_idx >= len(lines):
            try:
                auto_body = self._find_table_body_start(lines)
            except Exception:
                auto_body = None
            if auto_body is None:
                return None, {}
            body_start_idx = auto_body

        # 후보 인덱스 생성: 바디 시작 바로 위에서부터 문서 상단(0)까지 전 범위를 역순 탐색
        candidates: List[int] = [i for i in range(body_start_idx - 1, -1, -1)]

        best_idx: Optional[int] = None
        best_roles: Dict[str, Any] = {}
        best_count: int = -1

        for idx in candidates:
            roles, distinct = self._score_header_candidate(lines[idx])
            if distinct > best_count:
                best_count = distinct
                best_idx = idx
                best_roles = roles

        # 특수 규칙: 결과(result) 라벨이 없고 날짜(date) 라벨만 있는 문서의 헤더
        # 일부 양식은 결과 열의 헤더가 실제 날짜 문자열(예: '25-01-10')로 찍혀 있음.
        # 이 경우 date 역할을 result 역할로 재해석합니다.
        if isinstance(best_roles, dict) and best_roles and "result" not in best_roles and "date" in best_roles:
            try:
                date_info = best_roles.get("date")
                if isinstance(date_info, dict):
                    info = dict(date_info)
                    hits = list(info.get("hits") or [])
                    if "date-as-result" not in hits:
                        hits.append("date-as-result")
                    info["hits"] = hits
                    # 동일 열 인덱스를 사용하여 result로 승격
                    best_roles["result"] = info
                    # 원래 date 태그는 제거하여 중복 역할 방지
                    best_roles.pop("date", None)
            except Exception:
                # 조용히 무시 (원래 역할 유지)
                pass

        if best_idx is None or best_count < int(self.settings.role_min_distinct_hits):
            return None, {}
        return best_idx, best_roles

    def _is_policy_valid(self, roles: Dict[str, Any]) -> bool:
        """헤더 역할 조합이 정책상 유효한지(name+unit+result, reference 또는 min/max) 검사한다."""
        try:
            if not roles:
                return False
            has_name = bool(roles.get("name"))
            has_unit = bool(roles.get("unit"))
            has_result = bool(roles.get("result"))
            has_reference_like = bool(roles.get("reference") or (roles.get("min") and roles.get("max")))

            # 임계 통과 여부도 고려(없으면 True로 간주)
            unit_ok = bool((roles.get("unit") or {}).get("meets_threshold", True))
            result_ok = bool((roles.get("result") or {}).get("meets_threshold", True))
            ref_ok = bool((roles.get("reference") or {}).get("meets_threshold", True) or (roles.get("min") and roles.get("max")))

            return has_name and has_unit and has_result and has_reference_like and unit_ok and result_ok and ref_ok
        except Exception:
            return False

    def _score_header_candidate(self, line: Line) -> Tuple[Dict[str, Any], int]:
        """후보 라인에서 역할 동의어/정규식 적중을 계산해 역할 매핑과 상이한 역할 수를 반환."""
        # 토큰 텍스트 수집 및 정규화
        tokens: List[str] = []
        if isinstance(line, (list, tuple)):
            for t in line:
                try:
                    s = self._token_text(t)
                    if s:
                        tokens.append(s)
                except Exception:
                    continue
        else:
            s = self._token_text(line)
            if s:
                tokens.append(s)

        def norm(s: str) -> str:
            s = s.lower().strip()
            s = re.sub(r"\s+", " ", s)
            # 기호를 공백으로 치환하여 'ref. range'와 'ref range'를 동일시
            s = re.sub(r"[._:/\\-]+", " ", s)
            s = re.sub(r"\s+", " ", s).strip()
            return s

        norm_tokens = [norm(s) for s in tokens if s and s.strip()]

        # 동의어/정규식 사전 정규화
        synonyms = self.settings.header_synonyms or {}
        regex_map = self.settings.header_regex or {}

        roles: Dict[str, Any] = {}
        distinct_hits = 0

        for role, words in synonyms.items():
            hit_idx: Optional[int] = None
            hit_label: Optional[str] = None
            hit_word: Optional[str] = None

            word_norms = [norm(w) for w in words]

            # 동의어 매칭
            for i, tok in enumerate(norm_tokens):
                for w in word_norms:
                    # 완전 일치 또는 부분 포함 허용(너무 느슨해지지 않도록 길이 제약)
                    if tok == w or (len(w) >= 3 and w in tok):
                        hit_idx = i
                        hit_label = tokens[i]
                        hit_word = words[word_norms.index(w)]
                        break
                if hit_idx is not None:
                    break

            # 정규식 매칭(선택)
            if hit_idx is None and role in regex_map:
                pats = regex_map.get(role, [])
                for i, tok_raw in enumerate(tokens):
                    for p in pats:
                        try:
                            if re.search(p, tok_raw):
                                hit_idx = i
                                hit_label = tok_raw
                                hit_word = p
                                break
                        except re.error:
                            continue
                    if hit_idx is not None:
                        break

            if hit_idx is not None:
                distinct_hits += 1
                roles[role] = {
                    "label": hit_label,
                    "hits": [hit_word] if hit_word else [],
                    "col_index": hit_idx,
                    "tokens": [tokens[hit_idx]],
                    "confidence": 1.0,
                }

        return roles, distinct_hits

    # -----------------------
    # Shared sample selection helpers (used by rule and LLM)
    # -----------------------
    def _rows_from_body(self, body_lines: Lines) -> List[List[str]]:
        """바디 라인에서 텍스트만 추출한 2D 배열(rows)을 만든다."""
        rows: List[List[str]] = []
        for line in body_lines:
            try:
                row: List[str] = []
                if isinstance(line, (list, tuple)):
                    for t in line:
                        row.append(self._token_text(t))
                else:
                    row.append(self._token_text(line))
                # 공백/빈 토큰 제거
                row = [r for r in row if isinstance(r, str) and r.strip()]
                rows.append(row)
            except Exception:
                continue
        return rows

    def _select_representative_sample(self, body_lines: Lines) -> List[List[str]]:
        """LLM과 동일한 기준으로 대표 샘플 행을 선택.

                기본 원칙은 유지하되, 바디 라인의 "reference range" 타입 비율로 K를 엄격히 결정합니다.

                - K 결정 규칙(엄격):
                    - 범위 토큰(a-b/–/~)을 가진 라인 비율 >= threshold → K=4 (Name | Reference | Result | Unit)
                    - 범위 라인 비율 == 0 → K=5 (Name | Min | Max | Result | Unit)
                    - 그 외(0 < 비율 < threshold) → 실패로 간주(빈 리스트 반환)
                    - threshold는 settings.sample_reference_ratio_threshold가 있으면 사용, 없으면 0.3
                - 후보 필터:
                    - 첫 토큰이 코드로 해석 가능(resolve_code)
                    - 이후 열에 유닛/숫자 또는 범위가 최소 하나 존재
                    - 과도한 열(>6) 제외, 첫 토큰 중복 제외
                - 샘플은 헤더컬럼 갯수(K)와 동일한 토큰 갯수를 가진 라인으로만 구성
                - 유효 샘플이 하나도 없으면 실패(빈 리스트)
        """
        rows_all = self._rows_from_body(body_lines)
        if not rows_all:
            return []

        lengths = [len(r) for r in rows_all]

        num_re = re.compile(r"^[+-]?\d+(?:[.,]\d+)?(?:[HhLlNn])?$")
        range_re = re.compile(r"^[+-]?\d+(?:[.,]\d+)?\s*[-–~]\s*[+-]?\d+(?:[.,]\d+)?$")
        unit_re = re.compile(
            r"^(?:%|‰|g/dl|mg/dl|u/l|iu/l|mmol/l|meq/l|fL|fl|pg|ng/ml|k/µl|k/μl|k/u?l|m/µl|m/μl|m/u?l|10\^?\d+/(?:l|ul|µl|μl))$",
            re.IGNORECASE,
        )

        def _norm_num(s: str) -> str:
            return s.strip().replace("·", ".").replace(",", ".")

        # 1) reference-range 라인 비율로 K 가정(4 vs 5)
        try:
            thr = float(getattr(self.settings, "sample_reference_ratio_threshold", 0.3))
        except Exception:
            thr = 0.3

        range_like_count = 0
        valid_row_count = 0
        for row in rows_all:
            try:
                tail = row[1:]
            except Exception:
                tail = []
            # tail 내에 범위 토큰이 하나라도 있으면 range-like로 카운트
            has_range_token = any(range_re.match(_norm_num(s)) for s in tail)
            # 유효 행으로 카운트: 최소 3열 이상(코드 + 2개 이상)
            if len(row) >= 3:
                valid_row_count += 1
                if has_range_token:
                    range_like_count += 1

        range_ratio = (range_like_count / valid_row_count) if valid_row_count > 0 else 0.0
        if range_ratio >= thr:
            assumed_k = 4
        elif range_like_count == 0:
            assumed_k = 5
        else:
            # 애매 구간: 실패 처리
            return []

        # 2) 길이==assumed_k 행에서 샘플 선별
        def _filter_plausible(cands: List[List[str]]) -> List[List[str]]:
            plausible: List[List[str]] = []
            for row in cands:
                if len(row) > 6:
                    continue
                try:
                    if row.count(row[0]) > 1:
                        continue
                except Exception:
                    pass
                # 코드 확인
                has_code = False
                try:
                    has_code = bool(self._resolve_code(row[0]))
                except Exception:
                    has_code = False
                if not has_code:
                    continue
                # 유닛/숫자/범위 존재 검사
                try:
                    tail = row[1:]
                except Exception:
                    tail = []
                has_unit = any(unit_re.match(_norm_num(s)) or ("%" in s and len(_norm_num(s)) <= 4) for s in tail)
                has_range = any(range_re.match(_norm_num(s)) for s in tail)
                has_num = any(num_re.match(_norm_num(s)) for s in tail)
                if not has_unit:
                    continue
                if not (has_range or has_num):
                    continue
                plausible.append(row)
            return plausible

        chosen: List[List[str]] = []
        # 2-a) 우선 길이==assumed_k인 행들만 후보로
        len_k_candidates = [row for row in rows_all if len(row) == assumed_k]
        chosen = _filter_plausible(len_k_candidates)

        # 2-b) 샘플이 없으면 실패 처리
        if not chosen:
            return []

        return chosen[:20]

    # -----------------------
    # Shared compiled patterns
    # -----------------------
    @lru_cache(maxsize=1)
    def _get_unit_pattern_re(self) -> re.Pattern[str]:
        """흔한 단위 패턴(보수적) 정규식을 컴파일하여 반환한다."""
        return re.compile(
            r"^(?:%|‰|g/dl|mg/dl|u/l|iu/l|mmol/l|meq/l|fL|fl|pg|ng/ml|k/µl|k/μl|k/u?l|m/µl|m/μl|m/u?l|10\^?\d+/(?:l|ul|µl|μl))$",
            re.IGNORECASE,
        )

    def _infer_header_if_missing(self, body_lines: Lines) -> Tuple[Dict[str, Any], List[List[str]]]:
        """바디만으로 열 역할을 추론하는 규칙 기반 로직.

        접근 요약:
        - 열 인덱스별로 토큰 유형 비율을 계산(숫자, 범위, 단위, 날짜, 기타)
        - name=0 가정(5단계에서 코드 표준화됨)
        - unit: 유닛 패턴 매칭률 최대 열
        - reference: 범위 패턴 매칭률 최대 열
        - result: 숫자 비율이 높고 unit/reference가 아닌 열 중 최우선(가능하면 unit 좌측)
        - 최소 역할 수(설정 임계치) 미만이면 빈 dict 반환(abstain)
        """
        if not body_lines:
            return {}, []

        # 토큰 텍스트 추출 유틸
        def text_at(line: Line, j: int) -> str:
            try:
                if isinstance(line, (list, tuple)) and len(line) > j:
                    tok = line[j]
                    if isinstance(tok, dict):
                        return str(tok.get("text", ""))
                    return str(tok)
            except Exception:
                pass
            return ""

        # 정규화/판정 유틸
        def norm_num(s: str) -> str:
            return s.strip().replace("·", ".").replace(",", ".")

        num_re = re.compile(r"^[+-]?\d+(?:[.,]\d+)?(?:[HhLlNn])?$")
        range_re = re.compile(r"^[+-]?\d+(?:[.,]\d+)?\s*[-–~]\s*[+-]?\d+(?:[.,]\d+)?$")
        # 흔한 단위 패턴(보수적): %, g/dL, mg/dL, U/L, K/µL, M/µL, fL, pg, mmol/L, mEq/L, 10^x/L 등
        unit_re = self._get_unit_pattern_re()
        date_res: List[re.Pattern[str]] = []
        try:
            for p in (self.settings.header_regex or {}).get("date", []):
                try:
                    date_res.append(re.compile(p))
                except re.error:
                    continue
        except Exception:
            pass

        # 규칙 기반도 LLM과 동일한 샘플 선정 로직을 사용
        # 엄격 규칙: 샘플 선정 실패 시 헤더 추론 자체를 실패로 간주
        sample_rows = self._select_representative_sample(body_lines)
        if not sample_rows:
            return {}, []

        # 통계 집계 소스: 샘플만 사용(일관성 확보)
        rows_source: List[List[str]] = sample_rows

        # 열 개수 추정: rows_source에서 가장 긴 행의 길이
        max_cols = 0
        for row in rows_source:
            try:
                max_cols = max(max_cols, len(row))
            except Exception:
                continue
        if max_cols <= 1:
            return {}, sample_rows

        # 통계 수집
        stats: List[Dict[str, float]] = [
            {"rows": 0, "num": 0, "range": 0, "unit": 0, "date": 0, "nonempty": 0}
            for _ in range(max_cols)
        ]

        sample_lines = 0
        for row in rows_source:
            sample_lines += 1
            for j in range(max_cols):
                try:
                    s = row[j] if j < len(row) else ""
                except Exception:
                    s = ""
                if not isinstance(s, str):
                    try:
                        s = str(s)
                    except Exception:
                        s = ""
                s2 = s.strip()
                if not s2:
                    continue
                stats[j]["rows"] += 1
                stats[j]["nonempty"] += 1
                sn = norm_num(s2)
                if num_re.match(sn):
                    stats[j]["num"] += 1
                if range_re.match(sn):
                    stats[j]["range"] += 1
                if unit_re.match(sn) or ("%" in sn and len(sn) <= 4):
                    stats[j]["unit"] += 1
                for dr in date_res:
                    try:
                        if dr.search(sn):
                            stats[j]["date"] += 1
                            break
                    except Exception:
                        continue

        # 역할 결정
        roles: Dict[str, Any] = {}

        # 1) name 열: 0 인덱스로 가정(5단계에서 코드 정규화 완료)
        if max_cols >= 1:
            roles["name"] = {
                "label": "inferred",
                "hits": ["code-lexicon"],
                "col_index": 0,
                "tokens": [],
                "confidence": 1.0,
            }

        # 열 별 비율 계산 함수
        def ratio(j: int, key: str) -> float:
            r = stats[j]["rows"] or stats[j]["nonempty"] or 0.0
            if r <= 0:
                return 0.0
            return float(stats[j][key]) / float(r)

        # 2) unit 열 후보
        unit_idx = None
        unit_score = 0.0
        for j in range(1, max_cols):
            score = ratio(j, "unit")
            if score > unit_score or (abs(score - unit_score) <= 1e-6 and unit_idx is not None and j > unit_idx):
                unit_score = score
                unit_idx = j
        # 보수 임계치 적용
        unit_thresh = float(self.settings.unit_threshold)
        if sample_lines < int(self.settings.min_rows_for_inference):
            unit_thresh += float(self.settings.short_table_threshold_bonus)
        if unit_idx is not None:
            roles["unit"] = {
                "label": "inferred",
                "hits": ["unit-pattern"],
                "col_index": unit_idx,
                "tokens": [],
                "confidence": round(unit_score, 3),
                "meets_threshold": bool(unit_score >= unit_thresh),
            }
            if unit_score < unit_thresh:
                # 임계 미달이어도 열 인덱스는 유지하여 역할이 사라지지 않게 함
                pass

        # 3) reference 열 후보(범위)
        ref_idx = None
        ref_score = 0.0
        for j in range(1, max_cols):
            score = ratio(j, "range")
            if score > ref_score:
                ref_score = score
                ref_idx = j
        ref_thresh = float(self.settings.reference_threshold)
        if sample_lines < int(self.settings.min_rows_for_inference):
            ref_thresh += float(self.settings.short_table_threshold_bonus)
        if ref_idx is not None and (unit_idx is None or ref_idx != unit_idx):
            roles["reference"] = {
                "label": "inferred",
                "hits": ["range-pattern"],
                "col_index": ref_idx,
                "tokens": [],
                "confidence": round(ref_score, 3),
                "meets_threshold": bool(ref_score >= ref_thresh),
            }

        # 4) result 열 후보(숫자)
        result_idx = None
        result_score = 0.0
        for j in range(1, max_cols):
            if j == unit_idx or j == ref_idx:
                continue
            score = ratio(j, "num")
            # 가산: unit이 있는 경우 unit 좌측에 위치하면 +0.05 보너스
            if unit_idx is not None and j == unit_idx - 1:
                score += float(getattr(self.settings, "prefer_result_left_of_unit_bonus", 0.05))
            # 날짜 비율이 높은 열은 패널티
            score -= 0.5 * ratio(j, "date")
            if score > result_score or (abs(score - result_score) <= 1e-6 and result_idx is not None and j > result_idx):
                result_score = score
                result_idx = j
        res_thresh = float(self.settings.result_threshold)
        if sample_lines < int(self.settings.min_rows_for_inference):
            res_thresh += float(self.settings.short_table_threshold_bonus)
        # 날짜 비율 상한 게이트
        date_ratio_at_result = ratio(result_idx, "date") if result_idx is not None else 1.0
        max_date_ratio = float(self.settings.max_date_ratio_for_result)
        if result_idx is not None:
            roles["result"] = {
                "label": "inferred",
                "hits": ["numeric-pattern"],
                "col_index": result_idx,
                "tokens": [],
                "confidence": round(result_score, 3),
                "meets_threshold": bool(result_score >= res_thresh and date_ratio_at_result <= max_date_ratio),
            }

        # 4-1) 결과(role=result) 미선정 시 보수적 강제 선택(가능한 경우)
        if "result" not in roles and unit_idx is not None:
            # unit 주변 열들을 살펴보며 숫자 비율이 충분하고 날짜 비율이 낮은 열을 결과로 보강
            consider = int(getattr(self.settings, "fallback_consider_neighbors", 1))
            min_ratio = float(getattr(self.settings, "fallback_result_min_ratio", 0.45))
            # 짧은 표는 임계 상향
            if sample_lines < int(self.settings.min_rows_for_inference):
                min_ratio += float(self.settings.short_table_threshold_bonus)
            candidates: List[Tuple[int, float]] = []
            for dj in range(-consider, consider + 1):
                if dj == 0:
                    continue
                j = unit_idx + dj
                if j <= 0 or j >= max_cols:
                    continue
                if j == ref_idx:
                    continue
                num_r = ratio(j, "num")
                date_r = ratio(j, "date")
                if num_r >= min_ratio and date_r <= max_date_ratio:
                    # 좌측 선호 보너스 동일 적용
                    bonus = 0.0
                    if j == unit_idx - 1:
                        bonus += float(getattr(self.settings, "prefer_result_left_of_unit_bonus", 0.05))
                    candidates.append((j, num_r + bonus))
            if candidates:
                # 점수가 높은 후보 우선, 동점 시 더 오른쪽(널 값 회피 가정)
                candidates.sort(key=lambda x: (x[1], x[0]))
                best_j, best_s = candidates[-1]
                roles["result"] = {
                    "label": "inferred",
                    "hits": ["numeric-pattern", "fallback-adjacent-to-unit"],
                    "col_index": best_j,
                    "tokens": [],
                    "confidence": round(best_s, 3),
                    "forced": True,
                    "meets_threshold": bool(best_s >= res_thresh),
                }

        # 최종 유효성 검사: 서로 다른 역할 수가 임계치 이상이어야 함
        # 최종 유효성 검사(정책): name + unit + result는 필수,
        # 그리고 reference 또는 (min/max) 중 하나 이상이 존재해야 신뢰 가능
        has_name = bool(roles.get("name"))
        has_unit = bool(roles.get("unit"))
        has_result = bool(roles.get("result"))
        has_reference_like = bool(roles.get("reference") or (roles.get("min") and roles.get("max")))

        # 정책 충족 여부는 반환과 분리: 역할은 항상 반환하고, 상위 레벨에서 header_valid로 보수 판단
        # 규칙 기반 입력 샘플 구성은 이미 sample_rows로 제한됨
        return roles, sample_rows

    def _infer_header_with_llm(self, lines: Lines, body_lines: Lines) -> Tuple[Dict[str, Any], List[List[str]]]:
        """선택적 LLM 기반 헤더 추론 훅.

        입력 바디 일부 샘플을 텍스트로 제시하고, 열 역할(name/result/reference/unit/min/max)의
        열 인덱스를 JSON으로 반환하도록 요청합니다. 결과는 규칙 추론과 동일한 roles 포맷으로 매핑합니다.
        """
        try:
            sample: List[List[str]] = []
            if not getattr(self.settings, "use_llm", False):
                return {}, sample
            if not getattr(self, "llm", None):
                return {}, sample

            # 공통 샘플 선택 로직 사용(엄격): 샘플 실패 시 LLM 추론도 실패 처리
            sample = self._select_representative_sample(body_lines)
            if not sample:
                return {}, []

            system_prompt = (
                "You are an expert at labeling table columns in veterinary lab reports. "
                "Given sample rows (array of token arrays), infer column roles among: "
                "name, result, unit, reference, min, max. Return a single JSON object mapping each role to an object "
                "with fields: {label:'llm', hits:['llm'], col_index:<int>, tokens:[], confidence:0.9, meets_threshold:true}. "
                "Rules: name is the first column with test codes; result is numeric values (may include H/L/N/High/Low/Normal suffix); "
                "unit is measurement units; reference is a range (a-b). If the document splits the range into two separate columns, use min and max instead of reference. "
                "Important: choose either 'reference' OR ('min' and 'max'); never output both forms at the same time. Do not assign the same column index to multiple roles. "
                "Output only the JSON object with no extra text."
            )
            user_prompt = {
                "sample_rows": sample,
                "notes": "Pick exactly one index per applicable role. Use reference OR (min and max), not both. Avoid duplicate indices across roles."
            }

            # OpenAI Chat Completions 호출 (락/세마포어 보호)
            try:
                payload = {
                    "model": getattr(self, "llm_model", "gpt-4.1-mini"),
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": str(user_prompt)},
                    ],
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                }

                content = ""
                # 클래스 전역 세마포어 및 인스턴스 락 획득
                sem = getattr(self.__class__, "_LLM_SEMAPHORE", None)
                lock = getattr(self, "_llm_lock", None) if bool(getattr(self.settings, "enable_llm_lock", True)) else None

                if sem is not None:
                    sem.acquire()
                try:
                    if lock is not None:
                        lock.acquire()
                    try:
                        # 가독성을 위해 명시적으로 호출; 미지원 시 AttributeError로 처리
                        try:
                            resp = self.llm.chat.completions.create(**payload)  # type: ignore[attr-defined]
                        except AttributeError:
                            return {}, sample

                        try:
                            choices = getattr(resp, "choices", None)
                            if isinstance(choices, list) and choices:
                                ch0 = choices[0]
                                msg = getattr(ch0, "message", None)
                                if msg is not None:
                                    c = getattr(msg, "content", None)
                                    if isinstance(c, str) and c:
                                        content = c
                                if not content and isinstance(ch0, dict):
                                    content = ch0.get("message", {}).get("content", "") or ch0.get("text", "")
                            if not content and isinstance(resp, dict):
                                content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
                        except Exception:
                            pass
                    finally:
                        if lock is not None:
                            try:
                                lock.release()
                            except Exception:
                                pass
                finally:
                    if sem is not None:
                        try:
                            sem.release()
                        except Exception:
                            pass

                if not content:
                    return {}, sample
            except Exception:
                # SDK 또는 호출 오류 시 조용히 중단
                return {}, sample

            import json as _json
            try:
                parsed = _json.loads(content or "{}")
            except Exception:
                return {}, sample

            # 파싱: 두 형태 모두 허용
            # 1) 권장 형태: role -> {label, hits, col_index, tokens, confidence, meets_threshold}
            # 2) 단순 형태: role -> index(int); 이 경우 아래에서 스키마로 승격
            allowed_roles = ["name", "result", "unit", "reference", "min", "max"]

            def _ensure_role_obj(val: Any) -> Optional[Dict[str, Any]]:
                # dict 스키마인 경우: 필수 필드 보강
                if isinstance(val, dict):
                    try:
                        ci = int(val.get("col_index", -1))
                    except Exception:
                        return None
                    if ci < 0:
                        return None
                    out = {
                        "label": val.get("label", "llm"),
                        "hits": val.get("hits", ["llm"]),
                        "col_index": ci,
                        "tokens": val.get("tokens", []),
                        "confidence": val.get("confidence", 0.9),
                        "meets_threshold": bool(val.get("meets_threshold", True)),
                    }
                    return out
                # 숫자/문자 인덱스인 경우: 스키마 생성
                try:
                    ci = int(val)
                except Exception:
                    return None
                if ci < 0:
                    return None
                return {
                    "label": "llm",
                    "hits": ["llm"],
                    "col_index": ci,
                    "tokens": [],
                    "confidence": 0.9,
                    "meets_threshold": True,
                }

            roles: Dict[str, Any] = {}
            if isinstance(parsed, dict):
                for role in allowed_roles:
                    if role in parsed:
                        r = _ensure_role_obj(parsed.get(role))
                        if r is not None:
                            roles[role] = r

            # 후처리: reference vs (min,max) 충돌 방지 및 중복 인덱스 제거
            try:
                ref_present = "reference" in roles
                min_present = "min" in roles
                max_present = "max" in roles
                if ref_present and (min_present or max_present):
                    if min_present and max_present:
                        try:
                            mi = int(roles["min"].get("col_index", -1))
                            ma = int(roles["max"].get("col_index", -1))
                        except Exception:
                            mi = ma = -1
                        # min/max가 유효하고 서로 다른 열이면 min/max만 유지, 아니면 reference만 유지
                        if mi >= 0 and ma >= 0 and mi != ma:
                            roles.pop("reference", None)
                        else:
                            roles.pop("min", None)
                            roles.pop("max", None)
                    else:
                        # 하나만 있으면 신뢰 낮음 → reference만 유지
                        roles.pop("min", None)
                        roles.pop("max", None)

                # 동일 열 인덱스에 중복 역할 방지: name→result→unit→reference→min→max 우선순으로 유지
                seen: Dict[int, str] = {}
                order = ["name", "result", "unit", "reference", "min", "max"]
                for role in order:
                    info = roles.get(role)
                    if not isinstance(info, dict):
                        continue
                    try:
                        ci = int(info.get("col_index", -1))
                    except Exception:
                        ci = -1
                    if ci < 0:
                        continue
                    if ci in seen:
                        roles.pop(role, None)
                    else:
                        seen[ci] = role
            except Exception:
                pass

            return roles, sample
        except Exception:
            return {}, []

    def _extract_metadata_above_body(
        self, lines: Lines, header_index: Optional[int], body_start_idx: int
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """바디 시작 위(헤더 포함) 영역에서 병원/의뢰인/환자/검사일 메타데이터를 규칙 기반으로 추출.

        정책
        ----
        - 바디 미검출 시 호출하지 않음 (상위에서 보장)
        - 스코프: [0 .. end_idx] where end_idx = max(0, body_start_idx-1)
          · 헤더가 있다면 자연스레 포함됨. 사이드메타(좌우)는 좌표가 없으므로 무시됨.
        - 보수적 파싱: 라벨 패턴이 뚜렷하고 값이 과도하게 길거나 숫자만이면 배제
        - 확신이 없으면 None으로 유지

        반환
        ----
        - meta: {hospital_name, client_name, patient_name, inspection_date}
        - debug: {candidates: {field: [..]}, scanned_count: int}
        """
        try:
            end_idx = max(0, int(body_start_idx) - 1)
        except Exception:
            end_idx = max(0, body_start_idx - 1)

        region = lines[0 : end_idx + 1]

        # 라벨 사전
        patient_labels = [
            "환자명",
            "환자",
            "반려동물",
            "동물명",
            "pet",
            "animal",
            "name",
            "동물이름",
            "patient",
        ]
        client_labels = [
            "의뢰인",
            "보호자",
            "owner",
            "client",
            "고객",
            "고객명",
            "의뢰",
        ]
        # 검사일 우선 라벨 (보고/출력일 등은 후순위)
        date_positive = [
            "검사일",
            "검사일자",
            "채혈",
            "채취",
            "collection",
            "collected",
            "采血",
            "採血",
        ]
        date_neutral = ["일자", "date"]
        date_negative = ["보고", "출력", "발행", "인쇄", "등록", "접수"]

        # 날짜 정규식: settings.header_regex에 정의된 것을 최우선 사용
        date_patterns: List[str] = []
        try:
            if isinstance(self.settings.header_regex, dict):
                date_patterns = list(self.settings.header_regex.get("date", []) or [])
        except Exception:
            date_patterns = []
        if not date_patterns:
            date_patterns = [
                r"\b\d{4}[-./]\d{1,2}[-./]\d{1,2}\b",
                r"\b\d{2}[-./]\d{1,2}[-./]\d{1,2}\b",
            ]

        def norm(s: str) -> str:
            return re.sub(r"\s+", " ", s).strip()

        def joined(line: Line) -> str:
            try:
                return self._line_join_texts(line, sep=" ")
            except Exception:
                return str(line)

        def _extract_after_label(text: str, label: str) -> Optional[str]:
            """라벨 오른쪽 값을 추출. 콜론/하이픈/공백 등 구분자 처리."""
            try:
                idx = text.lower().find(label.lower())
                if idx < 0:
                    return None
                tail = text[idx + len(label) :].lstrip()
                # 가장 흔한 구분자들
                m = re.match(r"^[:：\-~–—]\s*(.+)$", tail)
                if m:
                    return norm(m.group(1))
                # 구분자 없이 label value 형태
                # 예) "환자명 홍길동" -> label 다음 토큰부터
                parts = tail.split()
                if parts:
                    return norm(" ".join(parts))
            except Exception:
                return None
            return None

        def _tokenize_with_geometry(line: Line) -> List[Tuple[int, int, str]]:
            """한 라인을 좌표/텍스트로 정리: (x_left, x_right, text) 리스트.
            기하 정보가 불충분하면 빈 리스트.
            """
            out: List[Tuple[int, int, str]] = []
            try:
                if isinstance(line, (list, tuple)):
                    for t in line:
                        if not isinstance(t, dict):
                            continue
                        xl = t.get("x_left")
                        xr = t.get("x_right")
                        s = str(t.get("text", "") or "").strip()
                        if xl is None or xr is None or not s:
                            continue
                        try:
                            xl_i = int(round(float(xl)))
                            xr_i = int(round(float(xr)))
                        except Exception:
                            continue
                        if xr_i < xl_i:
                            xl_i, xr_i = xr_i, xl_i
                        out.append((xl_i, xr_i, s))
            except Exception:
                return []
            # x_left 기준 정렬
            out.sort(key=lambda x: x[0])
            return out

        def _median_gap(tokens: List[Tuple[int, int, str]]) -> int:
            gaps: List[int] = []
            for i in range(len(tokens) - 1):
                g = tokens[i + 1][0] - tokens[i][1]
                if g >= 0:
                    gaps.append(g)
            if not gaps:
                return 0
            try:
                return int(round(median(gaps)))
            except Exception:
                gaps.sort()
                mid = len(gaps) // 2
                return gaps[mid]

        def _is_date_like(s: str) -> bool:
            try:
                for pat in date_patterns:
                    if re.search(pat, s):
                        return True
            except Exception:
                pass
            # 숫자만 6자리 이상 (예: 20240111 등)도 날짜/ID 유사 취급
            if re.fullmatch(r"\d{6,}", s):
                return True
            return False

        def _prune_trailing_id_or_date(val: str) -> str:
            """추출된 이름 문자열에서 뒤쪽의 ID/날짜 유사 토큰을 제거."""
            v = norm(val)
            # 공백으로 토큰화하고 뒤에서부터 잘라냄
            parts = v.split()
            pruned: List[str] = []
            for tok in parts:
                # 길고 숫자 위주 토큰은 잘라내기 시작 신호
                if re.fullmatch(r"\d{6,}", tok):
                    break
                if self.settings.name_stop_on_date_like and _is_date_like(tok):
                    break
                pruned.append(tok)
            return norm(" ".join(pruned))

        def _extract_name_after_label_by_geometry(line: Line, label: str) -> Optional[str]:
            """라벨 토큰 오른쪽의 이름을 x-좌표 간격으로 보수적으로 결합.

            규칙:
            - 라벨 문자열을 포함한 토큰을 anchor로 찾고, 그 오른쪽 토큰부터 스캔
            - 토큰 간 gap이 임계(thresh)를 넘으면 결합 중단
            - 구분자(:, -, ~ 등) 토큰은 건너뛰되 gap 기준 갱신
            - 순수 숫자 길이>=name_block_long_numeric_len 또는 날짜 유사 토큰을 만나면 중단
            - 최대 name_concat_max_tokens 개까지만 결합
            """
            toks = _tokenize_with_geometry(line)
            if not toks:
                return None

            # 라벨 포함 토큰 인덱스 탐색 (소문자 비교)
            anchor_idx = -1
            lab_low = label.lower()
            for idx, (_xl, _xr, s) in enumerate(toks):
                if lab_low in s.lower():
                    anchor_idx = idx
                    break
            if anchor_idx < 0:
                return None

            med_gap = _median_gap(toks)
            gap_thresh = max(int(self.settings.name_concat_min_gap_px), int(round(self.settings.name_concat_max_gap_multiplier * float(med_gap or 0))))
            # med_gap이 0일 수 있으므로 최소 임계 보장
            gap_thresh = max(gap_thresh, int(self.settings.name_concat_min_gap_px))

            # anchor의 오른쪽부터 진행
            collected: List[str] = []
            prev_right = toks[anchor_idx][1]
            max_tokens = max(1, int(self.settings.name_concat_max_tokens))
            for j in range(anchor_idx + 1, len(toks)):
                xl, xr, s = toks[j]
                if not s:
                    continue
                # 흔한 구분자는 스킵하되, prev_right 갱신
                if s in (":", "：", "-", "~", "–", "—"):
                    prev_right = xr
                    continue
                gap = xl - prev_right
                if gap > gap_thresh:
                    break
                # 숫자/날짜 유사 토큰 확인
                if re.fullmatch(rf"\d{{{int(self.settings.name_block_long_numeric_len)},}}", s):
                    break
                if self.settings.name_stop_on_date_like and _is_date_like(s):
                    break
                collected.append(s)
                prev_right = xr
                if len(collected) >= max_tokens:
                    break

            val = norm(" ".join(collected))
            if not val:
                return None
            return _prune_trailing_id_or_date(val)

        def _looks_name(val: str) -> bool:
            v = norm(val)
            if not v:
                return False
            # 너무 길거나 대부분 숫자/특수문자면 배제
            if len(v) > 40:
                return False
            if re.fullmatch(r"[0-9\W_]+", v):
                return False
            # 성별/기타 토큰 혼입 줄이기
            if any(t in v.lower() for t in ["male", "female", "m/", "f/", "성별", "sex:"]):
                return False
            return True

        def _date_score_context(text_lower: str) -> float:
            score = 0.0
            for p in date_positive:
                if p.lower() in text_lower:
                    score += 2.0
            for p in date_neutral:
                if p.lower() in text_lower:
                    score += 0.5
            for n in date_negative:
                if n.lower() in text_lower:
                    score -= 1.5
            return score

        # 후보 수집기
        candidates: Dict[str, List[Dict[str, Any]]] = {
            "hospital_name": [],
            "client_name": [],
            "patient_name": [],
            "inspection_date": [],
        }

        # 병원명(무라벨) 탐지를 위한 정규식 준비
        kor_hosp_re = re.compile(r"""([가-힣A-Za-z0-9&'"()·\- ]{1,60}?(?:동물)?병원)\b""")
        eng_hosp_re = re.compile(
            r"""([A-Za-z0-9&' .\-]{2,80}?(?:Animal Hospital|Veterinary (?:Clinic|Hospital|Center|Centre)|Animal Medical Center|Pet Clinic|Vet Clinic|Animal Clinic))""",
            re.IGNORECASE,
        )
        import math
        negative_addr_tokens = [
            "tel", "fax", "전화", "mobile", "http", "www", "@", "e-mail", "email", "주소", "address", "도로명",
        ]

        # 테이블 헤더 라인 판별을 위한 보조 함수와 헤더 키워드 세트
        def _is_header_like(text: str) -> bool:
            t = norm(text).lower()
            header_tokens = [
                "name",
                "unit",
                "result",
                "reference",
                "min",
                "max",
                "ref range",
                "ref. range",
                "range",
                "parameter",
                "test",
                "value",
            ]
            cnt = 0
            for w in header_tokens:
                if w in t:
                    cnt += 1
            # 두 개 이상 발견되면 테이블 헤더스러운 라인으로 간주
            return cnt >= 2

        for i, line in enumerate(region):
            text = joined(line)
            low = text.lower()

            # 테이블 헤더 라인은 환자/의뢰인 이름 추출에서 제외 (사용자 요청)
            if header_index is not None and i == int(header_index):
                pass  # 병원명/날짜 후보는 아래 일반 규칙에 따라 계속 수집
            
            # 1) 환자명
            for lab in patient_labels:
                if lab.lower() in low:
                    # 1순위: 기하 기반 보수 결합, 2순위: 문자열 파싱
                    val = _extract_name_after_label_by_geometry(line, lab)
                    if not val:
                        val = _extract_after_label(text, lab)
                        if val:
                            val = _prune_trailing_id_or_date(val)
                    # header-like 라인이거나, 'name' 레이블로 추출했는데 값이 헤더 토큰으로 구성된 경우는 제외
                    if lab.lower() == "name":
                        if header_index is not None and i == int(header_index):
                            val = None
                        elif val and _is_header_like(text):
                            # 라인 자체가 헤더스러우면 제외
                            val = None
                        elif val and _is_header_like(val):
                            # 추출된 값이 'Unit Min Max Result' 등인 경우 제외
                            val = None
                    if val and _looks_name(val):
                        candidates["patient_name"].append({
                            "label": lab,
                            "value": val,
                            "score": 1.0,
                            "line_index": i,
                        })
                        break

            # 2) 병원명 (무라벨, 접미 패턴 기반)
            # 주소/연락처 라인은 과감히 배제
            if any(tok in low for tok in negative_addr_tokens):
                pass
            else:
                # 한국어: '...병원' 또는 '...동물병원'으로 끝나는 구
                for m in kor_hosp_re.finditer(text):
                    cand = norm(m.group(1))
                    if not cand or cand in ("병원", "동물병원"):
                        continue
                    # 이름성 판단: 접두부에 최소 한 글자 이상 존재
                    if len(cand) < 3 or len(cand) > 60:
                        continue
                    # 강한 접미 보너스 + 길이 약간 보너스 - 상단 가중치(초반일수록 가점)
                    suffix_bonus = 1.6 if cand.endswith("동물병원") else 1.2
                    len_bonus = min(len(cand) / 18.0, 1.0)
                    idx_bonus = -0.2 * math.log1p(float(i))
                    score = 1.0 + suffix_bonus + len_bonus + idx_bonus
                    candidates["hospital_name"].append({
                        "label": "suffix-kor",
                        "value": cand,
                        "score": round(score, 3),
                        "line_index": i,
                    })

                # 영어: '... Animal Hospital', '... Veterinary Clinic' 등
                for m in eng_hosp_re.finditer(text):
                    cand = norm(m.group(1))
                    if not cand:
                        continue
                    if len(cand) < 4 or len(cand) > 80:
                        continue
                    # 최소 하나의 알파벳 존재
                    if not re.search(r"[A-Za-z]", cand):
                        continue
                    # 접미에 따른 보너스
                    low_c = cand.lower()
                    if "animal hospital" in low_c:
                        suf = 1.4
                    elif "veterinary hospital" in low_c:
                        suf = 1.3
                    elif "veterinary clinic" in low_c:
                        suf = 1.1
                    elif "animal medical center" in low_c:
                        suf = 1.2
                    elif "vet clinic" in low_c or "pet clinic" in low_c or "animal clinic" in low_c:
                        suf = 0.9
                    else:
                        suf = 0.8
                    idx_bonus = -0.2 * math.log1p(float(i))
                    len_bonus = min(len(cand) / 20.0, 1.0)
                    score = 1.0 + suf + len_bonus + idx_bonus
                    candidates["hospital_name"].append({
                        "label": "suffix-eng",
                        "value": cand,
                        "score": round(score, 3),
                        "line_index": i,
                    })

            # 3) 의뢰인/보호자명
            for lab in client_labels:
                if lab.lower() in low:
                    # 1순위: 기하 기반 보수 결합, 2순위: 문자열 파싱
                    val = _extract_name_after_label_by_geometry(line, lab)
                    if not val:
                        val = _extract_after_label(text, lab)
                        if val:
                            val = _prune_trailing_id_or_date(val)
                    # 테이블 헤더 라인은 client_name 추출에서도 제외
                    if header_index is not None and i == int(header_index):
                        val = None
                    elif val and _is_header_like(text):
                        val = None
                    if val and _looks_name(val):
                        candidates["client_name"].append({
                            "label": lab,
                            "value": val,
                            "score": 0.9,
                            "line_index": i,
                        })
                        break

            # 4) 검사일(날짜)
            # 라벨 맥락 점수 + 패턴 매칭
            ds = _date_score_context(low)
            if ds > -0.5:  # 강한 음성 맥락이 아니면 검색
                for pat in date_patterns:
                    try:
                        m = re.search(pat, text)
                    except re.error:
                        continue
                    if m:
                        val = norm(m.group(0))
                        # 너무 짧은 2자리 년도는 가점 낮게
                        y4 = bool(re.match(r"^\d{4}[-./]\d{1,2}[-./]\d{1,2}$", val))
                        score = ds + (1.5 if y4 else 0.7)
                        candidates["inspection_date"].append({
                            "label": "date-pattern",
                            "value": val,
                            "score": score,
                            "line_index": i,
                        })
                        break

        # 선택: 각 필드 상위 점수 후보
        def pick_best(field: str) -> Optional[str]:
            items = candidates.get(field) or []
            if not items:
                return None
            # 최근(헤더 근처)일수록 약간 가중치: index가 클수록 +0.1*log1p
            import math

            def key_fn(it: Dict[str, Any]) -> float:
                base = float(it.get("score", 0.0))
                idx_weight = 0.0
                try:
                    idx_weight = 0.1 * math.log1p(float(it.get("line_index", 0)))
                except Exception:
                    idx_weight = 0.0
                return base + idx_weight

            best = max(items, key=key_fn)
            return norm(str(best.get("value", ""))) or None

        meta: Dict[str, Any] = {
            "hospital_name": pick_best("hospital_name"),
            "client_name": pick_best("client_name"),
            "patient_name": pick_best("patient_name"),
            "inspection_date": pick_best("inspection_date"),
        }

        debug = {
            "candidates": candidates,
            "scanned_count": len(region),
            "header_index": header_index,
            "end_index": end_idx,
        }
        return meta, debug

    # -----------------------
    # Header-Body alignment evaluation (OCR gate)
    # -----------------------
    def _evaluate_header_body_alignment(
        self,
        header_roles: Any,
        body_lines: Lines,
        *,
        max_rows: int = 20,
    ) -> Tuple[float, Dict[str, Any]]:
        """헤더 역할(col_index)과 바디 라인의 타입 분포 일치율을 계산한다.

        간단한 접근(보수적):
        - name: 첫 열(0)이라 가정, 스코어 계산에서 제외
        - result: 숫자 비율
        - unit: 단위 패턴 비율
        - reference: 범위(a-b/~/-) 비율
        - min/max: 숫자 비율

        각 역할별 일치도는 [0..1].
        전체 점수는 (result+unit + max(reference, (min+max)/2)) / 3 평균으로 계산.
        유효 열이 일부 없으면 존재하는 항목 평균.
        """
        try:
            roles_map = self._roles_to_mapping(header_roles)

            def _col(role: str) -> Optional[int]:
                try:
                    info = roles_map.get(role) or {}
                    if not isinstance(info, dict):
                        return None
                    return int(info.get("col_index", -1))
                except Exception:
                    return None

            idx_res = _col("result")
            idx_unit = _col("unit")
            idx_ref = _col("reference")
            idx_min = _col("min")
            idx_max = _col("max")

            # 패턴
            num_re = re.compile(r"^[+-]?\d+(?:[.,]\d+)?(?:[HhLlNn])?$")
            range_re = re.compile(r"^[+-]?\d+(?:[.,]\d+)?\s*[-–~]\s*[+-]?\d+(?:[.,]\d+)?$")
            unit_re = re.compile(
                r"^(?:%|‰|g/dl|mg/dl|u/l|iu/l|mmol/l|meq/l|fL|fl|pg|ng/ml|k/µl|k/μl|k/u?l|m/µl|m/μl|m/u?l|10\^?\d+/(?:l|ul|µl|μl))$",
                re.IGNORECASE,
            )

            def txt_at(line: Line, j: Optional[int]) -> str:
                if j is None or j < 0:
                    return ""
                try:
                    if isinstance(line, (list, tuple)) and j < len(line):
                        t = line[j]
                        return self._token_text(t)
                except Exception:
                    return ""
                return ""

            rows = body_lines[: max(0, int(max_rows))]
            n = max(1, len(rows))
            res_hits = unit_hits = ref_hits = min_hits = max_hits = 0
            res_considered = unit_considered = ref_considered = min_considered = max_considered = 0

            for line in rows:
                # result
                if idx_res is not None and idx_res >= 0:
                    s = txt_at(line, idx_res).strip().replace("·", ".")
                    if s:
                        res_considered += 1
                        if num_re.match(s):
                            res_hits += 1
                # unit
                if idx_unit is not None and idx_unit >= 0:
                    s = txt_at(line, idx_unit).strip()
                    if s:
                        unit_considered += 1
                        if unit_re.match(s) or ("%" in s and len(s) <= 4):
                            unit_hits += 1
                # reference (single)
                if idx_ref is not None and idx_ref >= 0:
                    s = txt_at(line, idx_ref).strip().replace("·", ".")
                    if s:
                        ref_considered += 1
                        if range_re.match(s):
                            ref_hits += 1
                # min/max
                if idx_min is not None and idx_min >= 0:
                    s = txt_at(line, idx_min).strip().replace("·", ".")
                    if s:
                        min_considered += 1
                        if num_re.match(s):
                            min_hits += 1
                if idx_max is not None and idx_max >= 0:
                    s = txt_at(line, idx_max).strip().replace("·", ".")
                    if s:
                        max_considered += 1
                        if num_re.match(s):
                            max_hits += 1

            def ratio(h: int, c: int) -> float:
                return (float(h) / float(c)) if c > 0 else 0.0

            r_res = ratio(res_hits, res_considered)
            r_unit = ratio(unit_hits, unit_considered)
            r_ref = ratio(ref_hits, ref_considered)
            r_min = ratio(min_hits, min_considered)
            r_max = ratio(max_hits, max_considered)

            components: List[float] = []
            detail = {
                "result": {"hits": res_hits, "considered": res_considered, "ratio": r_res, "col": idx_res},
                "unit": {"hits": unit_hits, "considered": unit_considered, "ratio": r_unit, "col": idx_unit},
                "reference": {"hits": ref_hits, "considered": ref_considered, "ratio": r_ref, "col": idx_ref},
                "min": {"hits": min_hits, "considered": min_considered, "ratio": r_min, "col": idx_min},
                "max": {"hits": max_hits, "considered": max_considered, "ratio": r_max, "col": idx_max},
            }

            if idx_res is not None and idx_res >= 0:
                components.append(r_res)
            if idx_unit is not None and idx_unit >= 0:
                components.append(r_unit)
            # reference-like: single ref vs min/max 평균
            ref_like = 0.0
            count_ref_like = 0
            if idx_ref is not None and idx_ref >= 0:
                ref_like += r_ref
                count_ref_like += 1
            if (idx_min is not None and idx_min >= 0) or (idx_max is not None and idx_max >= 0):
                # min/max 둘 다 있으면 평균, 하나만 있으면 그 하나의 비율
                vals = []
                if idx_min is not None and idx_min >= 0:
                    vals.append(r_min)
                if idx_max is not None and idx_max >= 0:
                    vals.append(r_max)
                if vals:
                    ref_like += sum(vals) / float(len(vals))
                    count_ref_like += 1
            if count_ref_like > 0:
                components.append(ref_like / float(count_ref_like))

            if not components:
                return 0.0, detail
            overall = sum(components) / float(len(components))
            return overall, detail
        except Exception:
            return 0.0, {}

    def _build_interim_table(
        self, body_lines: Lines, header_roles: Any
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Step 8(geometry-only): 헤더를 진실로 보고, 순수 기하 샘플(K개 토큰 라인)만으로 밴드를 형성.

        정책:
        - K = max(col_index)+1 (헤더 고정)
        - 샘플: 바디 라인 중 "기하 좌표가 있고 유효 토큰 수 == K" 인 라인들
        - 샘플 수 0 → 실패, 1 → 그 라인 중심 신뢰, 2+ → 인덱스별 중앙값 중심
        - 텍스트 타입 판정/추가 안전망 없음

        반환:
        - (interim_rows, dbg) 튜플
          · interim_rows: {'_cells': List[str], '_bands': List[(L,R)], '_line_idx': int}
          · dbg: {'K': int, 'sample_count': int, 'sample_body_indices': List[int], 'band_centers': List[int]}
        """
        from statistics import median
        # 0) K 산정(헤더 기반)
        K = None
        try:
            max_ci = -1
            roles_map = self._roles_to_mapping(header_roles)
            for info in roles_map.values():
                if isinstance(info, dict) and "col_index" in info:
                    ci = int(info.get("col_index", -1))
                    if ci > max_ci:
                        max_ci = ci
            if max_ci >= 0:
                K = max_ci + 1
        except Exception:
            K = None
        if not isinstance(K, int) or K <= 0:
            # 헤더가 없거나 비정상 — 본 전략 전제 밖. 빈 결과와 dbg 반환
            return [], {"K": None, "sample_count": 0, "sample_body_indices": [], "band_centers": []}

        # 1) 토큰 추출(기하 중심)
        def _tokens_with_centers(line: Line) -> List[Tuple[int, int, str, Any]]:
            out: List[Tuple[int, int, str, Any]] = []
            if isinstance(line, (list, tuple)):
                for t in line:
                    try:
                        if not isinstance(t, dict):
                            continue
                        xl = t.get("x_left"); xr = t.get("x_right")
                        if xl is None or xr is None:
                            continue
                        xl_i = int(round(float(xl))); xr_i = int(round(float(xr)))
                        if xr_i < xl_i:
                            xl_i, xr_i = xr_i, xl_i
                        c = int((xl_i + xr_i) // 2)
                        w = max(1, xr_i - xl_i)
                        s = str(t.get("text", "") or "").strip()
                        if not s:
                            continue
                        out.append((c, w, s, t))
                    except Exception:
                        continue
            return sorted(out, key=lambda x: x[0])

        # 2) 샘플 채취: 유효 토큰 수 == K
        sample_body_indices: List[int] = []
        sample_centers_by_idx: List[List[int]] = [[] for _ in range(K)]
        # 앞쪽 N개만 보되, 충분하지 않으면 더 볼 필요 없이 조건만 충족하는 라인만 채택
        sample_limit = int(getattr(self.settings, "header_alignment_preview_rows", 20)) or 20
        for i, line in enumerate(body_lines[: max(1, sample_limit)]):
            toks = _tokens_with_centers(line)
            if len(toks) == K:
                sample_body_indices.append(i)
                # 좌→우 정렬 가정: 이미 정렬됨, 인덱스별 중심 수집
                for j in range(K):
                    sample_centers_by_idx[j].append(int(toks[j][0]))

        sample_count = len(sample_body_indices)
        if sample_count == 0:
            return [], {"K": K, "sample_count": 0, "sample_body_indices": [], "band_centers": []}

        # 3) 밴드 중심 계산
        if sample_count == 1:
            band_centers = [sample_centers_by_idx[j][0] for j in range(K)]
        else:
            band_centers = [int(median(sample_centers_by_idx[j])) if sample_centers_by_idx[j] else 0 for j in range(K)]

        # 4) 경계 계산(인접 중심 중간값, 양끝 외삽)
        edges: List[int] = []
        if K == 1:
            c0 = band_centers[0]
            edges = [c0 - 1000, c0 + 1000]
        else:
            mids = [int((band_centers[i] + band_centers[i + 1]) // 2) for i in range(K - 1)]
            first_gap = band_centers[1] - band_centers[0]
            last_gap = band_centers[-1] - band_centers[-2]
            left_edge = band_centers[0] - max(20, int(round(first_gap / 2)))
            right_edge = band_centers[-1] + max(20, int(round(last_gap / 2)))
            edges = [left_edge] + mids + [right_edge]

        bands: List[Tuple[int, int]] = [(edges[i], edges[i + 1]) for i in range(len(edges) - 1)]

        # 5) 밴드 할당 함수(가장 가까운 중심)
        def _assign_to_bands(toks: List[Tuple[int, int, str, Any]], bands: List[Tuple[int, int]]) -> List[str]:
            K2 = len(bands)
            cells: List[List[str]] = [[] for _ in range(K2)]
            # 최근접 중심 판단 기준:
            # - 우선 샘플로부터 계산한 band_centers(열의 x-중심값)를 사용
            # - band_centers가 없거나 비정상인 경우에만 밴드 경계의 중간점으로 대체
            centers_local = [int((L + R) // 2) for (L, R) in bands]
            try:
                _centers_ref = list(band_centers) if isinstance(band_centers, list) and len(band_centers) == K2 else centers_local
            except Exception:
                _centers_ref = centers_local
            mode = str(getattr(self.settings, "band_assignment_mode", "hybrid") or "hybrid").lower()
            for (c, _w, s, _tok) in toks:
                if mode == "nearest":
                    # 항상 최근접 중심 배정
                    if K2 > 0:
                        nearest = min(range(K2), key=lambda ii: abs(c - _centers_ref[ii]))
                        cells[nearest].append(s)
                    continue

                # include-only 또는 hybrid 공통: 내부 포함 우선
                placed = False
                for idx, (L, R) in enumerate(bands):
                    if L <= c < R:
                        cells[idx].append(s)
                        placed = True
                        break
                if placed:
                    continue

                if mode == "hybrid":
                    # 외부는 최근접 중심(하위 옵션 제거: hybrid에서는 항상 적용)
                    if K2 > 0:
                        nearest = min(range(K2), key=lambda ii: abs(c - _centers_ref[ii]))
                        cells[nearest].append(s)
                # include-only 모드는 폴백 없이 미배정(빈 칸 → 이후 UNKNOWN 처리)
            return [" ".join(col).strip() for col in cells]

        # 6) 전체 라인 배정
        rows: List[Dict[str, Any]] = []
        for i, line in enumerate(body_lines):
            toks = _tokens_with_centers(line)
            cells = _assign_to_bands(toks, bands)
            rows.append({"_cells": cells, "_bands": bands, "_line_idx": i})

        dbg = {
            "K": K,
            "sample_count": sample_count,
            "sample_body_indices": sample_body_indices,
            "band_centers": band_centers,
        }
        return rows, dbg

    def _fill_unknowns(
        self,
        interim_rows: List[Dict[str, Any]],
        all_lines: Lines,
        body_lines: Lines,
        header_roles: Any,
    ) -> List[Dict[str, Any]]:
        """Step 8(geometry-only): 빈 셀을 'unknown'으로 채우고, 미리보기용 역할 키에 매핑.

        주의: 역할 매핑은 오직 표시 목적이며, 의미론적 해석을 하지 않습니다.
        헤더가 존재하면 col_index만 사용하여 해당 밴드 값을 대응시키고,
        헤더가 없으면 기본 순서(name, reference, result, unit)에 첫 4개 밴드를 대응합니다.
        """
        if not interim_rows:
            return []

        filled: List[Dict[str, Any]] = []

        # 역할→열 인덱스 맵(표시용)
        role_to_idx: Dict[str, int] = {}
        roles_map = self._roles_to_mapping(header_roles)
        header_present = bool(roles_map)
        if header_present:
            for role in ["name", "reference", "min", "max", "result", "unit"]:
                try:
                    info = roles_map.get(role)
                    if isinstance(info, dict) and "col_index" in info:
                        ci = int(info.get("col_index", -1))
                        if ci >= 0:
                            role_to_idx[role] = ci
                except Exception:
                    continue
        # 헤더가 없을 때만 기본 매핑 사용
        default_order = ["name", "reference", "result", "unit"]

        for row in interim_rows:
            cells = list(row.get("_cells") or [])
            if not isinstance(cells, list):
                cells = []
            # 빈 문자열을 'UNKNOWN'으로 채움
            cells_filled = [c if (isinstance(c, str) and c.strip()) else "UNKNOWN" for c in cells]

            out: Dict[str, Any] = {"_cells": cells_filled}
            # 원본 밴드/라인 인덱스 보존
            bands = row.get("_bands")
            if bands:
                out["_bands"] = bands
            line_idx = row.get("_line_idx")
            if isinstance(line_idx, int):
                out["_line_idx"] = line_idx
            src_tokens: Dict[str, Any] = {}

            if header_present:
                for role, idx in role_to_idx.items():
                    if 0 <= idx < len(cells_filled):
                        val = cells_filled[idx]
                        out[role] = val
                        # 디버그 미리보기는 min/max를 _src_tokens에서만 표시하므로 보조 입력 제공
                        if role in ("min", "max") and isinstance(val, str) and val:
                            src_tokens[role] = {"text": val, "_origin": "geom_banded"}
            else:
                # 기본 순서로 첫 4개만 매핑
                for i, role in enumerate(default_order):
                    if i < len(cells_filled):
                        val = cells_filled[i]
                        out[role] = val
                        if role in ("min", "max") and isinstance(val, str) and val:
                            src_tokens[role] = {"text": val, "_origin": "geom_banded"}

            # 선택된 result 값에 대해, 실제 토큰(_src_tokens['result'])을 Step 8 시점에 고정 저장
            try:
                res_info = roles_map.get("result") if isinstance(roles_map, dict) else None
                res_col = int(res_info.get("col_index", -1)) if isinstance(res_info, dict) else -1
                _res_val = out.get("result")
                has_result_val = (isinstance(_res_val, str) and _res_val.strip().lower() != "unknown")
                # 밴드/라인 정보가 있어야 안전하게 찾을 수 있음
                if has_result_val and isinstance(res_col, int) and res_col >= 0:
                    bands = out.get("_bands")
                    line_idx = out.get("_line_idx")
                    if isinstance(bands, list) and isinstance(line_idx, int) and 0 <= line_idx < len(body_lines) and 0 <= res_col < len(bands):
                        L, R = bands[res_col]
                        line = body_lines[line_idx]

                        # 숫자 정규화: result 문자열에서 선행 숫자 부분만 추출
                        def _norm_num_str(s: Optional[str]) -> Optional[str]:
                            if not s or not isinstance(s, str):
                                return None
                            t = s.strip().replace("·", ".").replace(",", ".")
                            m = re.match(r"^[+-]?\d+(?:\.\d+)?", t)
                            return m.group(0) if m else None

                        target_num = _norm_num_str(out.get("result"))

                        best_tok = None
                        best_conf = None
                        # 라인 내에서 결과 밴드에 속한 숫자형 토큰을 탐색
                        if isinstance(line, (list, tuple)):
                            for tok in line:
                                try:
                                    if not isinstance(tok, dict):
                                        continue
                                    txt = str(tok.get("text", "") or "").strip()
                                    if not txt:
                                        continue
                                    xl = tok.get("x_left"); xr = tok.get("x_right")
                                    if not isinstance(xl, (int, float)) or not isinstance(xr, (int, float)):
                                        continue
                                    xc = (float(xl) + float(xr)) / 2.0
                                    if not (L <= xc < R):
                                        continue
                                    # 숫자형만 고려
                                    m = re.match(r"^[+-]?\d+(?:[.,]\d+)?", txt.replace("·", ".").replace(",", "."))
                                    if not m:
                                        continue
                                    num_txt = m.group(0).replace(",", ".")
                                    conf = tok.get("confidence")
                                    # 1순위: 숫자값이 target과 정확히 일치하는 토큰
                                    if target_num and num_txt == target_num and isinstance(conf, (int, float)):
                                        best_tok = tok
                                        best_conf = float(conf)
                                        break
                                    # 2순위: 밴드 내 숫자형 중 최고 신뢰도
                                    if isinstance(conf, (int, float)):
                                        cf = float(conf)
                                        if best_conf is None or cf > best_conf:
                                            best_conf = cf
                                            best_tok = tok
                                except Exception:
                                    continue
                        if best_tok is not None:
                            # 원본 토큰을 그대로 보존(디버깅 용도)
                            src_tokens.setdefault("result", best_tok)
            except Exception:
                # 토큰 고정에 실패해도 다른 로직은 계속 진행
                pass

            if src_tokens:
                out["_src_tokens"] = src_tokens
            filled.append(out)

        return filled

    def _split_reference_range(
        self, interim_rows: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """결합된 참조범위를 min/max로 분할(가능한 경우).

        입력: filled_rows(또는 그와 동등한 포맷) — 각 행에 최소한 다음 중 일부 키가 있을 수 있음:
          - name, unit, result, reference, min, max, _cells, _src_tokens

        동작:
          - min/max가 이미 있으면 우선 보존
          - reference가 존재하고 'a-b' / 'a–b' / 'a ~ b' 형태로 파싱되면 min/max를 채움
          - 숫자 파싱 오류 시 reference를 그대로 두고 min/max는 생략

        반환: min/max가 보강된 새로운 행 리스트
        """
        if not interim_rows:
            return []

        split_re = re.compile(r"^\s*([+-]?\d+(?:[.,]\d+)?)\s*[\-–~]\s*([+-]?\d+(?:[.,]\d+)?)\s*$")

        def _to_float(s: str) -> Optional[float]:
            try:
                s2 = s.replace("·", ".").replace(",", ".").strip()
                return float(s2)
            except Exception:
                return None

        out: List[Dict[str, Any]] = []
        for row in interim_rows:
            try:
                # 얕은 복사 후 업데이트
                new_row = dict(row)
                min_val = new_row.get("min")
                max_val = new_row.get("max")
                has_min = isinstance(min_val, str) and min_val.strip() != ""
                has_max = isinstance(max_val, str) and max_val.strip() != ""
                if has_min and has_max:
                    out.append(new_row)
                    continue
                ref = new_row.get("reference")
                if isinstance(ref, str) and ref.strip():
                    # 9.1 참조값이 UNKNOWN인 경우: min/max도 UNKNOWN으로 채움(없는 항목만)
                    try:
                        ref_stripped = ref.strip()
                        if ref_stripped.lower() == "unknown":
                            unk = "UNKNOWN"
                            st = new_row.get("_src_tokens") or {}
                            if isinstance(st, dict):
                                st = dict(st)
                            else:
                                st = {}
                            if not has_min:
                                new_row["min"] = unk
                                st.setdefault("min", {"text": unk, "_origin": "ref_unknown"})
                            if not has_max:
                                new_row["max"] = unk
                                st.setdefault("max", {"text": unk, "_origin": "ref_unknown"})
                            new_row["_src_tokens"] = st
                            out.append(new_row)
                            continue
                    except Exception:
                        # UNKNOWN 처리 중 예외가 나도 일반 분해 로직으로 진행
                        pass
                    m = split_re.match(ref)
                    if m:
                        a_s, b_s = m.group(1), m.group(2)
                        a_v = _to_float(a_s)
                        b_v = _to_float(b_s)
                        if a_v is not None and b_v is not None:
                            # 문자열로 유지하되, 숫자로 파싱 가능한 형태는 원문형을 그대로 둠
                            # 이후 최종 정규화 단계에서 float로 강제 가능
                            new_row.setdefault("min", a_s)
                            new_row.setdefault("max", b_s)
                            # 디버그 출처 표기
                            st = new_row.get("_src_tokens") or {}
                            if isinstance(st, dict):
                                st = dict(st)
                            else:
                                st = {}
                            st.setdefault("min", {"text": a_s, "_origin": "ref_split"})
                            st.setdefault("max", {"text": b_s, "_origin": "ref_split"})
                            new_row["_src_tokens"] = st
                out.append(new_row)
            except Exception:
                out.append(row)
        return out

    def _to_final_json(self, meta: Dict[str, Any], rows: List[Dict[str, Any]]) -> DocumentResult:
        """중간 행 리스트를 최종 DocumentResult 스키마로 정규화."""
        # 메타 병합
        doc: DocumentResult = {
            "hospital_name": meta.get("hospital_name"),
            "client_name": meta.get("client_name"),
            "patient_name": meta.get("patient_name"),
            "inspection_date": meta.get("inspection_date"),
            "tests": [],
        }

        if not rows:
            return doc

        # 선택: 코드별 기대 단위 맵을 1회 생성하여 호환성 확인(있을 때만)
        code_expected_unit: Dict[str, Optional[str]] = {}
        try:
            from .reference.reference_data import REFERENCE_TESTS  # type: ignore
            # 빌드: code -> canonical unit (REFERENCE_TESTS 기반)
            # 간단한 정규화 사용
            def canon_unit(u: Optional[str]) -> Optional[str]:
                if not u or not isinstance(u, str) or not u.strip():
                    return None
                if normalize_unit_simple is None:
                    return u
                try:
                    cu = normalize_unit_simple(u)
                    return cu or u
                except Exception:
                    return u
            for item in REFERENCE_TESTS:
                try:
                    if not isinstance(item, dict):
                        continue
                    c = item.get("code")
                    u = item.get("unit")
                    if c and c not in code_expected_unit:
                        code_expected_unit[c] = canon_unit(u)
                except Exception:
                    continue
        except Exception:
            code_expected_unit = {}

        def parse_flag(raw: Optional[str]) -> Optional[str]:
            if not raw or not isinstance(raw, str):
                return None
            t = raw.strip()
            m = re.match(r"^[+-]?\d+(?:[.,]\d+)?\s*([HhLlNn])\s*$", t)
            if not m:
                return None
            return m.group(1).upper()

        def to_float(s: Optional[str]) -> Optional[float]:
            if not s or not isinstance(s, str):
                return None
            try:
                return float(s.replace(",", "."))
            except Exception:
                return None

        tests: List[Dict[str, Any]] = []
        for row in rows:
            try:
                code_raw = row.get("name")
                code_canon = None
                if isinstance(code_raw, str) and code_raw.strip():
                    # 한 번 더 보수적으로 해석하여 canonical 코드 확보
                    try:
                        code_canon = self._resolve_code(code_raw) or code_raw
                    except Exception:
                        code_canon = code_raw
                # 값/단위
                unit_raw = row.get("unit") if isinstance(row.get("unit"), str) else None
                unit_canon = row.get("unit_canonical") if isinstance(row.get("unit_canonical"), str) else None
                unit_final = unit_canon or unit_raw

                result_norm = row.get("result_norm") if isinstance(row.get("result_norm"), str) else None
                value = to_float(result_norm) if result_norm else None
                # flag는 최종 스키마엔 포함하지 않음

                min_norm = row.get("min_norm") if isinstance(row.get("min_norm"), str) else None
                max_norm = row.get("max_norm") if isinstance(row.get("max_norm"), str) else None
                ref_min = to_float(min_norm) if min_norm else None
                ref_max = to_float(max_norm) if max_norm else None

                # 범위/값 검증
                range_check: Dict[str, Any] = {}
                if ref_min is not None and ref_max is not None:
                    range_check["min_le_max"] = bool(ref_min <= ref_max)
                if value is not None and ref_min is not None and ref_max is not None:
                    range_check["value_in_range"] = bool(ref_min <= value <= ref_max)

                # 단위 호환성
                unit_check: Dict[str, Any] = {}
                try:
                    expected = code_expected_unit.get(str(code_canon)) if code_canon else None
                except Exception:
                    expected = None
                if expected:
                    unit_check = {
                        "expected": expected,
                        "given": unit_final,
                        "matches_expected": bool(unit_final == expected),
                    }

                test_obj: Dict[str, Any] = {
                    "code": code_canon,
                    "unit": unit_final,
                    "reference_min": ref_min,
                    "reference_max": ref_max,
                    "value": value,
                }

                tests.append(test_obj)
            except Exception:
                continue

        doc["tests"] = tests
        return doc

    # -----------------------
    # Step 9: Truncate rows to header column count
    # -----------------------
    def _truncate_to_header_columns(
        self, rows: List[Dict[str, Any]], header_roles: Any
    ) -> List[Dict[str, Any]]:
        """헤더 역할(col_index)에 정의된 컬럼 수를 초과하는 셀은 뒤에서 제거하여 맞춘다.

        정책:
        - 무조건 truncate (사용자 요구). 단, 최소 필요한 역할 수 계산에 실패하면 원본 반환.
        - 기준 열 수 K 산정:
            · header_roles에 정의된 col_index의 최댓값 + 1
            · 없으면 rows의 첫 행 '_cells' 길이 사용(없으면 0)
        - 각 행의 '_cells' 길이가 K보다 크면 뒤에서 pop하여 맞춤.
        - 디버그 추적을 위해 '_row_fix'와 '_dropped_extra'에 기록.
        - 역할 키(name/result/unit/reference/min/max)는 해당 인덱스가 잘린 경우 재매핑하지 않고, 
          이후 단계에서 '_cells'를 우선 사용.
        """
        if not rows:
            return []

        # 기준 열 수 계산
        K = None
        try:
            roles_map = self._roles_to_mapping(header_roles)
            if roles_map:
                max_idx = -1
                for role, info in roles_map.items():
                    if isinstance(info, dict) and "col_index" in info:
                        try:
                            ci = int(info.get("col_index", -1))
                            if ci > max_idx:
                                max_idx = ci
                        except Exception:
                            continue
                if max_idx >= 0:
                    K = max_idx + 1
        except Exception:
            K = None
        if K is None:
            # 헤더 정보 없으면 첫 행 기준으로 사용
            try:
                first_cells = rows[0].get("_cells") if isinstance(rows[0], dict) else None
                if isinstance(first_cells, list):
                    K = len(first_cells)
            except Exception:
                K = None
        if not isinstance(K, int) or K <= 0:
            return rows

        out: List[Dict[str, Any]] = []
        for row in rows:
            try:
                new_row = dict(row)
                cells = list(new_row.get("_cells") or []) if isinstance(new_row.get("_cells"), list) else []
                if len(cells) > K:
                    dropped = cells[K:]
                    cells = cells[:K]
                    new_row["_cells"] = cells
                    # 추적 정보
                    new_row["_row_fix"] = "truncate_tail"
                    existing = new_row.get("_dropped_extra")
                    if isinstance(existing, list):
                        new_row["_dropped_extra"] = existing + dropped
                    else:
                        new_row["_dropped_extra"] = dropped
                out.append(new_row)
            except Exception:
                out.append(row)
        return out

    # -----------------------
    # Step 11: Unit/Result normalization
    # -----------------------
    def _normalize_unit_and_result(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Unit/Result 최종 정규화(단일 책임 지점) + 숫자 문자열 정리.

        정책(일원화):
        - 본 단계가 단위 정규화의 유일한 확정 지점입니다. (Step 4.x에서는 텍스트 변경 없음)
        - unit 정규화:
          · normalize_unit_simple 을 사용해 접두어(K/M), micro/L 접기, 그리고 OCR 혼동(ugD→µg/dL, mg/d1→mg/dL 등)을 한 번에 처리합니다.
          · 성공 시 unit_canonical에 저장하고 unit(원문)은 보존합니다.
          · 정규화 실패 시 unit은 그대로 두되 unit_canonical 없음.
        - result 정규화:
          · row.result가 문자열이면 숫자 부분만 추출.
          · 쉼표/중점 대체(, · → .), 앞뒤 공백 제거, 접두부 +/− 허용.
          · 숫자 파싱 실패 시 원문 유지(result_norm 없음).
        - Min/Max도 숫자 문자열로 강제(result와 동일 규칙)하여 min_norm/max_norm에 기록(존재할 경우).
        - UNKNOWN은 그대로 유지하며 *_norm 필드는 만들지 않음.
        """
        if not rows:
            return []

        def _norm_number_str(val: str) -> Optional[str]:
            if not isinstance(val, str):
                return None
            t = val.strip()
            if not t or t.upper() == "UNKNOWN":
                return None
            # 숫자+플래그(H/L/N) 꼬리 제거
            m = re.match(r"^\s*([+-]?\d+(?:[.,]\d+)?)(?:[HhLlNn])?\s*$", t)
            if not m:
                return None
            num = m.group(1).replace("·", ".").replace(",", ".")
            # 유효성 확인
            try:
                float(num)
            except Exception:
                return None
            return num

        out: List[Dict[str, Any]] = []
        for row in rows:
            try:
                new_row = dict(row)
                # Unit canonical - 최종 정규화(단일 지점)
                u = new_row.get("unit")
                if isinstance(u, str) and u.strip() and u.upper() != "UNKNOWN" and normalize_unit_simple is not None:
                    try:
                        cu = normalize_unit_simple(u)
                        if cu:
                            new_row["unit_canonical"] = cu
                    except Exception:
                        pass

                # Result number
                r = new_row.get("result")
                rn = _norm_number_str(r) if isinstance(r, str) else None
                if rn is not None:
                    new_row["result_norm"] = rn

                # Min/Max numeric strings
                mn = new_row.get("min")
                mx = new_row.get("max")
                mnn = _norm_number_str(mn) if isinstance(mn, str) else None
                mxn = _norm_number_str(mx) if isinstance(mx, str) else None
                if mnn is not None:
                    new_row["min_norm"] = mnn
                if mxn is not None:
                    new_row["max_norm"] = mxn

                out.append(new_row)
            except Exception:
                out.append(row)

        return out

    # -----------------------
    # Debug helpers (Step 5)
    # -----------------------
    def debug_step5(
        self,
        intermediates: Intermediates | Dict[str, Any],
        *,
        show_full_lines: bool = False,
    ) -> str:
        """Step 5 중간 산출물을 사람이 읽기 쉬운 문자열로 정리합니다.

        입력
        ----
        intermediates: extract_from_lines(..., return_intermediates=True) 가 반환한 dict
        show_full_lines: 전체 라인 구조도 함께 출력할지 여부 (항상 전체 출력)

        출력
        ----
        str: 노트북에서 print()로 바로 보여줄 수 있는 포맷된 텍스트
        """
        try:
            if not isinstance(intermediates, dict):
                return f"⚠️ intermediates 타입 이상: {type(intermediates)} | 값 미리보기: {repr(intermediates)[:200]}"

            body_start = intermediates.get("body_start")
            body_lines = intermediates.get("body_lines") or []
            dropped = intermediates.get("dropped") or []
            debug_preview = intermediates.get("debug_preview") or []
            scan_all = intermediates.get("code_resolve_scan_all") or []

            out: List[str] = []
            if body_start is None:
                out.append("❌ 바디 시작 라인을 찾지 못했습니다.")
                # 스캔 미리보기 표시: idx, 첫 토큰, 해석 코드
                try:
                    if debug_preview:
                        out.append("\n🔎 바디 시작 판별을 위해 스캔한 라인:")
                        for i, (idx0, first, resolved) in enumerate(debug_preview, 1):
                            out.append(f"  {i}. idx={idx0} first={first!r} resolved={resolved!r}")
                except Exception:
                    pass
                # 문서 전체 기준 코드 인식 실패 라인
                try:
                    if scan_all:
                        out.append("\n🧹 코드 인식 실패 라인 목록 (문서 전체):")
                        any_printed = False
                        for idx0, first, resolved, full in scan_all:
                            if not resolved:
                                out.append(f" - line#{idx0}: first={first!r} | full='{full}'")
                                any_printed = True
                        if not any_printed:
                            out.append(" (없음)")
                except Exception:
                    pass
                return "\n".join(out)

            out.append(f"✅ 바디 시작 인덱스: {body_start}")
            out.append(f"📦 바디 라인 수: {len(body_lines)}")

            # 바디 라인 미리보기 (요청 형식: "- line#<실제번호>: <내용>")
            out.append("\n🔎 바디 라인 미리보기:")
            for line in body_lines:
                try:
                    # 실제 원본 라인 인덱스 탐색: 우선 첫 토큰의 'line_index' 필드 사용
                    idx0 = None
                    if isinstance(line, (list, tuple)) and len(line) > 0 and isinstance(line[0], dict):
                        idx0 = line[0].get("line_index")

                    joined = self._line_join_texts(line)

                    # 보조: scan_all에서 full 텍스트 일치로 역추적
                    if idx0 is None:
                        try:
                            for _i, _f, _r, _full in scan_all:
                                if _full == joined:
                                    idx0 = _i
                                    break
                        except Exception:
                            pass

                    prefix = f" - line#{idx0}:" if idx0 is not None else " - line#?:"
                    # 코드 중복 표시 제거: joined 자체에 첫 토큰(정규화된 코드)이 포함되므로 first는 출력하지 않음
                    out.append(f"{prefix} {joined}")
                except Exception:
                    out.append(" - <미리보기 실패>")

            # 전체 라인 구조 출력(옵션)
            if show_full_lines:
                out.append("\n📋 바디 라인 전체(원본 구조):")
                for i, line in enumerate(body_lines, 1):
                    try:
                        out.append(f"  {i}. {line}")
                    except Exception:
                        out.append(f"  {i}. <표시 실패>")

            # 문서 전체 기준 코드 인식 실패 라인 (바디 제외)
            try:
                if scan_all:
                    # 바디에 포함된 실제 라인 인덱스 집합 계산
                    body_idx_set: set[int] = set()
                    try:
                        for bl in body_lines:
                            _idx = None
                            if isinstance(bl, (list, tuple)) and len(bl) > 0 and isinstance(bl[0], dict):
                                _idx = bl[0].get("line_index")
                            if _idx is None:
                                # fallback: full 텍스트 매칭
                                _full = self._line_join_texts(bl)
                                for _i, _f, _r, _full2 in scan_all:
                                    if _full2 == _full:
                                        _idx = _i
                                        break
                            if _idx is not None:
                                body_idx_set.add(int(_idx))
                    except Exception:
                        body_idx_set = set()

                    out.append("\n🧹 코드 인식 실패 라인 목록 (문서 전체):")
                    any_printed = False
                    for idx0, first, resolved, full in scan_all:
                        if (idx0 not in body_idx_set) and (not resolved):
                            out.append(f" - line#{idx0}: first={first!r} | full='{full}'")
                            any_printed = True
                    if not any_printed:
                        out.append(" (없음)")

                    # 추가: 바디에 포함되지 않은 라인 전체(성공/실패 무관) 목록
                    try:
                        out.append("\n🗂 바디에 포함되지 않은 라인 (문서 전체):")
                        any_non_body = False
                        for idx0, _first, _resolved, full in scan_all:
                            if idx0 not in body_idx_set:
                                out.append(f" - line#{idx0}: {full}")
                                any_non_body = True
                        if not any_non_body:
                            out.append(" (없음)")
                    except Exception:
                        pass
            except Exception:
                pass

            return "\n".join(out)
        except Exception as e:
            return f"⚠️ debug_step5 포맷팅 중 오류: {type(e).__name__}: {e}"

    # -----------------------
    # Debug helpers (Step 6)
    # -----------------------
    def debug_step6(
        self,
        intermediates: Intermediates | Dict[str, Any],
        *,
        show_full_header_line: bool = False,
    ) -> str:
        """Step 6(헤더 검증) 결과를 보기 좋은 문자열로 정리합니다.

        입력
        ----
        intermediates: extract_from_lines(..., return_intermediates=True) 가 반환한 dict
        show_full_header_line: 헤더 라인의 원본 구조를 함께 표시할지 여부

        출력
        ----
        str: 노트북에서 print()로 바로 보여줄 수 있는 포맷된 텍스트
        """
        try:
            if not isinstance(intermediates, dict):
                return f"⚠️ intermediates 타입 이상: {type(intermediates)} | 값 미리보기: {repr(intermediates)[:200]}"

            idx = intermediates.get("header_index")
            header_line = intermediates.get("header_line")
            header_roles = intermediates.get("header_roles")
            roles_map = self._roles_to_mapping(header_roles)
            header_valid = intermediates.get("header_valid")
            header_source = intermediates.get("header_source", "unknown")
            body_lines_count = intermediates.get("body_lines_count")
            pre_llm_roles = intermediates.get("inferred_roles_before_llm") or {}
            pre_llm_policy_valid = intermediates.get("pre_llm_policy_valid")
            llm_triggered = bool(intermediates.get("llm_triggered"))
            llm_trigger_cause = intermediates.get("llm_trigger_cause")

            out: List[str] = []
            if idx is None:
                # OCR 헤더 라인이 없더라도, 추론/LLM으로 역할이 채워졌을 수 있음
                if isinstance(roles_map, dict) and roles_map:
                    out.append("ℹ️ 헤더 라인 없음 (추론/백업 사용)")
                else:
                    out.append("❌ 헤더 라인을 찾지 못했습니다.")
                    return "\n".join(out)

            out.append(f"🧭 헤더 인덱스: {idx}")
            out.append(f"🔎 헤더 출처: {header_source}")

            # 헤더 텍스트 미리보기
            if header_line is not None:
                try:
                    preview = self._line_join_texts(header_line)
                    out.append(f"🖹 헤더 텍스트: {preview}")
                except Exception:
                    out.append("🖹 헤더 텍스트: <표시 실패>")

            # 유효성/역할 수 + 정책 기반 검사 결과도 함께 표기
            try:
                distinct = len([r for r in roles_map.keys() if roles_map.get(r)]) if isinstance(roles_map, dict) else 0
            except Exception:
                distinct = 0
            # 기존 플래그 우선, 없으면 distinct 기반 추정
            valid = bool(header_valid) if header_valid is not None else (distinct >= int(self.settings.role_min_distinct_hits))
            # 정책(필수 역할) 기반 재평가: name+unit+result 필수, reference 또는 (min/max) 필요
            policy_valid = False
            if isinstance(roles_map, dict) and roles_map:
                has_name = bool(roles_map.get("name"))
                has_unit = bool(roles_map.get("unit"))
                res = roles_map.get("result") or {}
                has_result = bool(res)
                has_reference_like = bool(roles_map.get("reference") or (roles_map.get("min") and roles_map.get("max")))
                policy_valid = has_name and has_unit and has_result and has_reference_like
            out.append(f"✅ 헤더 유효성: {valid} (roles={distinct}, threshold={self.settings.role_min_distinct_hits}) | 정책기준: {policy_valid} (필수: name+unit+result + ref|min/max)")

            # 유효성 실패 사유 상세 계산 도우미
            def _policy_and_reasons(roles_dict: Dict[str, Any]) -> Tuple[bool, List[str]]:
                pol_valid = False
                reasons: List[str] = []
                rm = self._roles_to_mapping(roles_dict)
                if isinstance(rm, dict) and rm:
                    has_name = bool(rm.get("name"))
                    has_unit = bool(rm.get("unit"))
                    has_result = bool(rm.get("result"))
                    has_ref_like = bool(rm.get("reference") or (rm.get("min") and rm.get("max")))
                    pol_valid = has_name and has_unit and has_result and has_ref_like
                    if not has_name:
                        reasons.append("누락: name")
                    if not has_unit:
                        reasons.append("누락: unit")
                    if not has_result:
                        reasons.append("누락: result")
                    if not has_ref_like:
                        reasons.append("누락: reference 또는 (min+max)")

                    def _thr_reason(role: str, base_thresh: float) -> None:
                        info = rm.get(role) or {}
                        if isinstance(info, dict) and info:
                            meets = info.get("meets_threshold")
                            if meets is False:
                                conf = info.get("confidence")
                                reasons.append(f"임계 미달: {role} (conf={conf}, base≥{base_thresh})")
                            if info.get("forced"):
                                reasons.append(f"강제 선택 사용: {role}")

                    _thr_reason("unit", float(self.settings.unit_threshold))
                    _thr_reason("result", float(self.settings.result_threshold))
                    _thr_reason("reference", float(self.settings.reference_threshold))
                    try:
                        if body_lines_count is not None and int(body_lines_count) < int(self.settings.min_rows_for_inference):
                            reasons.append(f"짧은 표 보너스(+{self.settings.short_table_threshold_bonus}) 적용 대상")
                    except Exception:
                        pass
                return pol_valid, reasons

            # 현재 header_roles에 대한 사유 출력
            if not policy_valid:
                _, reasons = _policy_and_reasons(roles_map)
                if reasons:
                    out.append("\n❌ 유효성 실패 사유:")
                    for r in reasons:
                        out.append(f" - {r}")

            # 역할 매핑 상세 출력 도우미
            def _render_roles(title: str, roles_dict: Dict[str, Any]) -> List[str]:
                lines: List[str] = []
                rm = self._roles_to_mapping(roles_dict)
                if isinstance(rm, dict) and rm:
                    lines.append(f"\n{title}")
                    def _col_i(v: Any) -> int:
                        try:
                            return int(v.get("col_index", -1)) if isinstance(v, dict) else -1
                        except Exception:
                            return -1
                    for role, info in sorted(rm.items(), key=lambda kv: _col_i(kv[1])):
                        if not isinstance(info, dict):
                            lines.append(f" - {role}: <정보 없음>")
                            continue
                        label = info.get("label")
                        col_index = info.get("col_index")
                        hits = info.get("hits") or []
                        conf = info.get("confidence")
                        forced = info.get("forced") if isinstance(info, dict) else False
                        forced_tag = " forced=True" if forced else ""
                        meets = info.get("meets_threshold") if isinstance(info, dict) else None
                        meets_tag = f" meets_threshold={meets}" if meets is not None else ""
                        lines.append(f" - {role}: label={label!r} col_index={col_index} hits={hits} conf={conf}{forced_tag}{meets_tag}")
                return lines

            # LLM이 사용된 경우, 규칙 기반(사전) 결과를 먼저 표시 + 사유
            if llm_triggered and isinstance(pre_llm_roles, dict) and pre_llm_roles:
                # 사유 표기
                cause_text = "정책 기준 미달" if llm_trigger_cause == "policy_invalid" else ("규칙 기반 헤더 미검출" if llm_trigger_cause == "no_rule_header" else "기타")
                out.append(f"\n🤖 LLM 백업 사용: {cause_text}")
                # 사전(규칙 기반) 결과의 정책 판단과 사유
                pre_valid, pre_reasons = _policy_and_reasons(pre_llm_roles)
                out.append(f"➡️ 규칙 기반 추론(LLM 전) 정책기준: {pre_valid}")
                if not pre_valid and pre_reasons:
                    out.append("사유:")
                    for r in pre_reasons:
                        out.append(f" - {r}")
                # 역할 매핑 렌더링
                out.extend(_render_roles("\n🔁 규칙 기반 추론 결과(LLM 호출 전):", pre_llm_roles))

                # LLM에 전달된 입력 샘플 출력(있을 경우)
                try:
                    llm_input_sample = intermediates.get("llm_input_sample") or []
                except Exception:
                    llm_input_sample = []
                if llm_input_sample:
                    out.append("\n📥 LLM 입력 샘플 행:")
                    try:
                        for i, row in enumerate(llm_input_sample, 1):
                            try:
                                row_str = ", ".join([str(x) for x in row])
                            except Exception:
                                row_str = str(row)
                            out.append(f"  {i}. [ {row_str} ]")
                    except Exception:
                        out.append("  <표시 실패>")

            # 현재(최종) 역할 매핑 출력: LLM이 있었다면 규칙 기반 출력 후에 표시
            if isinstance(roles_map, dict) and roles_map:
                # LLM이 사용되지 않았다면 평소처럼 바로 출력, 사용되었다면 위에서 규칙 기반 먼저 출력 후 이어서 출력
                title = "\n📏 역할 매핑:"
                out.extend(_render_roles(title, roles_map))

            # 헤더 출처가 inferred인 경우, 규칙 기반 추론에 사용된 입력 샘플도 표시
            try:
                if header_source == "inferred":
                    inferred_input_sample = intermediates.get("inferred_input_sample") or []
                    if inferred_input_sample:
                        out.append("\n🧪 규칙 기반 추론 입력 샘플 행:")
                        for i, row in enumerate(inferred_input_sample, 1):
                            try:
                                row_str = ", ".join([str(x) for x in row])
                            except Exception:
                                row_str = str(row)
                            out.append(f"  {i}. [ {row_str} ]")
            except Exception:
                pass

            # 원본 구조 출력(옵션)
            if show_full_header_line and header_line is not None:
                out.append("\n📋 헤더 라인(원본 구조):")
                try:
                    out.append(str(header_line))
                except Exception:
                    out.append("<표시 실패>")

            return "\n".join(out)
        except Exception as e:
            return f"⚠️ debug_step6 포맷팅 중 오류: {type(e).__name__}: {e}"

    # -----------------------
    # Debug helpers (Step 7: Metadata)
    # -----------------------
    def debug_step7(
        self,
        intermediates: Intermediates | Dict[str, Any],
        *,
        show_top_k: int = 5,
    ) -> str:
        """Step 8(메타데이터) 추출 결과를 보기 좋은 문자열로 정리합니다.

        입력
        ----
        intermediates: extract_from_lines(..., return_intermediates=True) 가 반환한 dict
        show_top_k: 각 필드별 후보 상위 K개를 표시

        출력
        ----
        str: 노트북에서 print()로 바로 보여줄 수 있는 포맷된 텍스트
        """
        try:
            if not isinstance(intermediates, dict):
                return f"⚠️ intermediates 타입 이상: {type(intermediates)} | 값 미리보기: {repr(intermediates)[:200]}"

            body_start = intermediates.get("body_start")
            if body_start is None:
                return "ℹ️ 메타데이터 스킵됨: 바디 시작 미검출"

            meta_candidates = intermediates.get("meta_candidates") or {}
            scanned = intermediates.get("meta_scanned_count")
            region_end = intermediates.get("meta_region_end_index")

            out: List[str] = []
            out.append("🧾 메타데이터 추출 결과 요약")
            out.append(f" - 스캔 라인 수: {scanned} (end_index={region_end})")

            def _render_field(field: str, candidates: Dict[str, Any]) -> List[str]:
                lines: List[str] = []
                items = candidates.get(field) or []
                if not items:
                    lines.append(f" - {field}: 후보 없음")
                    return lines
                # 점수 내림차순 상위 K개
                try:
                    items = sorted(items, key=lambda x: float(x.get("score", 0.0)))
                    items = list(reversed(items))
                except Exception:
                    pass
                top = items[: max(0, int(show_top_k))]
                lines.append(f" - {field}: 후보 {len(items)}개 (상위 {len(top)}):")
                for i, it in enumerate(top, 1):
                    try:
                        label = it.get("label")
                        value = it.get("value")
                        score = it.get("score")
                        idx = it.get("line_index")
                        lines.append(f"    {i}. [{label}] score={score} line={idx} | {value}")
                    except Exception:
                        lines.append(f"    {i}. <표시 실패>")
                return lines

            out.extend(_render_field("hospital_name", meta_candidates))
            out.extend(_render_field("client_name", meta_candidates))
            out.extend(_render_field("patient_name", meta_candidates))
            out.extend(_render_field("inspection_date", meta_candidates))

            return "\n".join(out)
        except Exception as e:
            return f"⚠️ debug_step8 포맷팅 중 오류: {type(e).__name__}: {e}"

    # -----------------------
    # Debug helpers (Step 8: Filling)
    # -----------------------
    def debug_step8(
        self,
        intermediates: Intermediates | Dict[str, Any],
    ) -> str:
        """Step 8(Interim/Filling) 결과를 보기 좋은 문자열로 정리합니다.

        출력: 채워진 행을 실제 테이블처럼 헤더 포함 정렬해 표시합니다. (전체 행 출력)
        - 컬럼: Name | Reference | Result | Unit (고정, 내부 정규화 순서)
        - 헤더 라벨: OCR에서 검출된 라벨이 있으면 사용, 없으면 기본 영문 라벨 사용
        - 행 수: 전체
        """
        try:
            if not isinstance(intermediates, dict):
                return f"⚠️ intermediates 타입 이상: {type(intermediates)}"

            # 샘플 요약(먼저 표시)
            out: List[str] = []
            try:
                step8_dbg = intermediates.get("step8_debug") or {}
                body_lines = intermediates.get("body_lines") or []
                sample_idx_list = step8_dbg.get("sample_body_indices") or []
                K = step8_dbg.get("K")
                sc = step8_dbg.get("sample_count")
                out.append("📌 Step 8 샘플(geometry 기반)")
                out.append(f" - K={K} | sample_count={sc}")
                if sample_idx_list:
                    out.append(" - 샘플 라인:")
                    for bi in sample_idx_list:
                        try:
                            # 원본 라인 인덱스 추출 시도
                            orig_idx = None
                            line = body_lines[bi] if 0 <= int(bi) < len(body_lines) else None
                            if isinstance(line, (list, tuple)) and len(line) > 0 and isinstance(line[0], dict):
                                orig_idx = line[0].get("line_index")
                            preview = self._line_join_texts(line) if line is not None else ""
                            prefix = f"   - line#{orig_idx}" if orig_idx is not None else "   - line#?"
                            out.append(f"{prefix}: {preview}")
                        except Exception:
                            out.append("   - <표시 실패>")
                else:
                    out.append(" - (샘플 없음)")
            except Exception:
                # 샘플 요약 실패 시 무시하고 계속
                pass

            filled = intermediates.get("filled_rows") or []
            if not filled:
                out.append("\nℹ️ filled_rows 비어있음 (Step 8 미실행 또는 헤더 스코프 불일치)")
                return "\n".join(out)

            # 1) 헤더/역할 구성: 실제 헤더 순서를 따르는 동적 컬럼 구성
            header_roles = intermediates.get("header_roles") or {}
            # 표준화된 header_roles(list/any)를 roles mapping으로 변환하여 일관 사용
            try:
                roles_map = self._roles_to_mapping(header_roles)
            except Exception:
                roles_map = {}
            header_source = intermediates.get("header_source") or "unknown"

            def _role_label(role: str, default_label: str) -> str:
                try:
                    roles_map = self._roles_to_mapping(header_roles)
                    info = roles_map.get(role) if isinstance(roles_map, dict) else None
                    if header_source == "ocr" and isinstance(info, dict):
                        lab = info.get("label")
                        # 'inferred'/'llm' 같은 내부 라벨은 무시하고, 실제 텍스트일 때만 사용
                        if isinstance(lab, str) and lab.strip() and lab.lower() not in ("inferred", "llm"):
                            return lab.strip()
                except Exception:
                    pass
                return default_label

            # 헤더에 정의된 역할을 col_index 순으로 정렬하고 표시 가능한 역할만 선택
            def _col_index_for(role: str) -> int:
                try:
                    roles_map = self._roles_to_mapping(header_roles)
                    info = roles_map.get(role) if isinstance(roles_map, dict) else None
                    return int(info.get("col_index", 10**6)) if isinstance(info, dict) else 10**6
                except Exception:
                    return 10**6

            roles_map = self._roles_to_mapping(header_roles)
            roles_present = [r for r in ["name", "unit", "reference", "min", "max", "result"] if isinstance(roles_map, dict) and roles_map.get(r)]
            roles_present.sort(key=_col_index_for)

            # reference vs (min,max) 충돌 시 min/max를 우선(문서 스키마 보존). 중복 제거.
            if "min" in roles_present or "max" in roles_present:
                roles_present = [r for r in roles_present if r != "reference"]

            # 표시 컬럼이 없거나 헤더가 미검출이면 기본 레이아웃으로 대체
            if not roles_present:
                roles_present = ["name", "reference", "result", "unit"]

            # 2) 값 추출 도우미 (min/max는 src_token 우선, 없으면 reference 분해)
            rows = filled

            def _disp(v: Any) -> str:
                try:
                    if v is None:
                        return "UNKNOWN"
                    s = str(v)
                    if not s.strip():
                        return "UNKNOWN"
                    return s
                except Exception:
                    return "UNKNOWN"

            range_split_re = re.compile(r"\s*[-–~]\s*")

            def _cell_value(row: Dict[str, Any], role: str) -> str:
                try:
                    if role in ("name", "unit", "result", "reference"):
                        return _disp(row.get(role))
                    if role in ("min", "max"):
                        # 헤더가 min/max인 경우, 값은 항상 분리되어 있다고 가정하므로
                        # src_tokens의 해당 토큰만 사용하고, reference 분해는 시도하지 않는다.
                        st = row.get("_src_tokens") or {}
                        tok = st.get(role)
                        if isinstance(tok, dict):
                            return _disp(tok.get("text"))
                        return ""
                except Exception:
                    return ""
                return ""

            # 3) 컬럼 라벨/정렬/폭 계산
            labels = []
            align_right = set(["result", "min", "max"])  # 숫자 열 우측 정렬
            for role in roles_present:
                if role == "name":
                    labels.append(_role_label("name", "Name"))
                elif role == "unit":
                    labels.append(_role_label("unit", "Unit"))
                elif role == "reference":
                    labels.append(_role_label("reference", "Reference"))
                elif role == "min":
                    labels.append(_role_label("min", "Min"))
                elif role == "max":
                    labels.append(_role_label("max", "Max"))
                elif role == "result":
                    labels.append(_role_label("result", "Result"))

            # 폭 계산
            col_widths: List[int] = []
            for idx, role in enumerate(roles_present):
                width = len(labels[idx])
                for r in rows:
                    width = max(width, len(_cell_value(r, role)))
                col_widths.append(width)

            # 한 행 포맷터
            def _fmt_cells(cells: List[str]) -> str:
                parts = []
                for i, val in enumerate(cells):
                    role = roles_present[i]
                    w = col_widths[i]
                    if role in align_right:
                        parts.append(val.rjust(w))
                    else:
                        parts.append(val.ljust(w))
                return " | ".join(parts)

            # 구분선 생성
            def _sep_line() -> str:
                parts = ["-" * w for w in col_widths]
                return "-+-".join(parts)

            # 4) 테이블 렌더링
            out.append("")
            out.append("🧩 Step 8: Filling 결과 (정렬된 표, 전체)")
            out.append(_fmt_cells(labels))
            out.append(_sep_line())
            for r in rows:
                try:
                    cells = [_cell_value(r, role) for role in roles_present]
                    out.append(_fmt_cells(cells))
                except Exception:
                    out.append("<표시 실패>")

            try:
                out.append("")
                out.append(f"(header_source={header_source})")
            except Exception:
                pass

            return "\n".join(out)
        except Exception as e:
            return f"⚠️ debug_step8 포맷팅 중 오류: {type(e).__name__}: {e}"

    # -----------------------
    # Debug helpers (Step 9: Truncate rows)
    # -----------------------
    def debug_step9(
        self,
        intermediates: Intermediates | Dict[str, Any],
    ) -> str:
        """Step 9(행 길이 정규화: 뒤에서 자르기) 결과 미리보기.

        헤더 기준 열 수에 맞춰 잘린 '_cells'를 확인하고, 기본 레이아웃으로 미리보기를 렌더링합니다.
        """
        try:
            if not isinstance(intermediates, dict):
                return f"⚠️ intermediates 타입 이상: {type(intermediates)}"

            rows = intermediates.get("step9_rows") or intermediates.get("filled_rows") or []
            if not rows:
                return "ℹ️ step9_rows 비어있음 (Step 9 미실행 또는 이전 단계 결과 없음)"

            def _s(v: Any) -> str:
                try:
                    if v is None:
                        return ""
                    return str(v)
                except Exception:
                    return ""

            # 기본 레이아웃(Name | Reference | Result | Unit)로 보여줌
            labels = ["Name", "Reference", "Result", "Unit", "_fix"]
            data: List[List[str]] = []
            for r in rows:
                data.append([
                    _s(r.get("name")),
                    _s(r.get("reference")),
                    _s(r.get("result")),
                    _s(r.get("unit")),
                    _s(r.get("_row_fix")),
                ])

            # 열 폭 계산 및 정렬
            widths = [len(l) for l in labels]
            for row in data:
                for i, v in enumerate(row):
                    widths[i] = max(widths[i], len(v))

            def fmt_row(cells: List[str]) -> str:
                parts = []
                for i, v in enumerate(cells):
                    if labels[i] in ("Result",):
                        parts.append(v.rjust(widths[i]))
                    else:
                        parts.append(v.ljust(widths[i]))
                return " | ".join(parts)

            sep = "-+-".join(["-" * w for w in widths])
            out: List[str] = []
            out.append("🧪 Step 9: 행 길이 정규화(뒤에서 자르기) 결과(전체)")
            out.append(fmt_row(labels))
            out.append(sep)
            for row in data:
                out.append(fmt_row(row))
            return "\n".join(out)
        except Exception as e:
            return f"⚠️ debug_step9 포맷팅 중 오류: {type(e).__name__}: {e}"

    # -----------------------
    # Debug helpers (Step 10: Reference split)
    # -----------------------
    def debug_step10(
        self,
        intermediates: Intermediates | Dict[str, Any],
    ) -> str:
        """Step 10(Reference → Min/Max 분리) 결과 미리보기.

        Name | Min | Max | Result | Unit 형태로 상위 행을 렌더링합니다.
        """
        try:
            if not isinstance(intermediates, dict):
                return f"⚠️ intermediates 타입 이상: {type(intermediates)}"

            rows = intermediates.get("step10_rows") or intermediates.get("step9_rows") or []
            if not rows:
                return "ℹ️ step10_rows 비어있음 (Step 10 미실행 또는 이전 단계 결과 없음)"

            def _s(v: Any) -> str:
                try:
                    if v is None:
                        return ""
                    return str(v)
                except Exception:
                    return ""

            labels = ["Name", "Min", "Max", "Result", "Unit"]
            data = []
            for r in rows:
                data.append([
                    _s(r.get("name")),
                    _s(r.get("min")),
                    _s(r.get("max")),
                    _s(r.get("result")),
                    _s(r.get("unit")),
                ])

            # 열 폭 계산 및 정렬
            widths = [len(l) for l in labels]
            for row in data:
                for i, v in enumerate(row):
                    widths[i] = max(widths[i], len(v))

            def fmt_row(cells: List[str]) -> str:
                parts = []
                for i, v in enumerate(cells):
                    if labels[i] in ("Min", "Max", "Result"):
                        parts.append(v.rjust(widths[i]))
                    else:
                        parts.append(v.ljust(widths[i]))
                return " | ".join(parts)

            sep = "-+-".join(["-" * w for w in widths])
            out: List[str] = []
            out.append("🧪 Step 10: Reference → Min/Max 분리 결과(전체)")
            out.append(fmt_row(labels))
            out.append(sep)
            for row in data:
                out.append(fmt_row(row))
            return "\n".join(out)
        except Exception as e:
            return f"⚠️ debug_step10 포맷팅 중 오류: {type(e).__name__}: {e}"

    # -----------------------
    # Debug helpers (Step 11: Unit/Result normalization)
    # -----------------------
    def debug_step11(
        self,
        intermediates: Intermediates | Dict[str, Any],
    ) -> str:
        """Step 11(Unit/Result 정규화) 결과 미리보기.

        Name | Result(result_norm) | Unit(unit_canonical) | Min(min_norm) | Max(max_norm)
        """
        try:
            if not isinstance(intermediates, dict):
                return f"⚠️ intermediates 타입 이상: {type(intermediates)}"

            rows = intermediates.get("step11_rows") or intermediates.get("step10_rows") or []
            if not rows:
                return "ℹ️ step11_rows 비어있음 (Step 11 미실행 또는 이전 단계 결과 없음)"

            def _s(v: Any) -> str:
                try:
                    if v is None:
                        return ""
                    return str(v)
                except Exception:
                    return ""

            labels = ["Name", "Result", "result_norm", "Unit", "unit_canonical", "Min", "min_norm", "Max", "max_norm"]
            data = []
            for r in rows:
                data.append([
                    _s(r.get("name")),
                    _s(r.get("result")),
                    _s(r.get("result_norm")),
                    _s(r.get("unit")),
                    _s(r.get("unit_canonical")),
                    _s(r.get("min")),
                    _s(r.get("min_norm")),
                    _s(r.get("max")),
                    _s(r.get("max_norm")),
                ])

            widths = [len(l) for l in labels]
            for row in data:
                for i, v in enumerate(row):
                    widths[i] = max(widths[i], len(v))

            def fmt_row(cells: List[str]) -> str:
                parts = []
                for i, v in enumerate(cells):
                    if labels[i] in ("Result", "result_norm", "Min", "min_norm", "Max", "max_norm"):
                        parts.append(v.rjust(widths[i]))
                    else:
                        parts.append(v.ljust(widths[i]))
                return " | ".join(parts)

            sep = "-+-".join(["-" * w for w in widths])
            out: List[str] = []
            out.append("🧪 Step 11: Unit/Result 정규화 결과(전체)")
            out.append(fmt_row(labels))
            out.append(sep)
            for row in data:
                out.append(fmt_row(row))
            return "\n".join(out)
        except Exception as e:
            return f"⚠️ debug_step11 포맷팅 중 오류: {type(e).__name__}: {e}"

    # -----------------------
    # Debug helpers (Step 12: Body + Filtered tests)
    # -----------------------
    def debug_step12(
        self,
        intermediates: Intermediates | Dict[str, Any],
    ) -> str:
        """Step 12(최종 필터 적용 후) 포함/제외 tests를 "라인 순"으로 한 표에 렌더링.

        출력 컬럼: code | value_conf | value | unit | reference_min | reference_max | drop_reason

        규칙:
        - value_conf 표시: 가능하면 Step 8에서 고정 저장한 result 토큰의 OCR confidence를 사용하며, 없으면 헤더 result 열의 column-level confidence를 사용합니다(표시 시 소숫점 네 자리에서 자르기; 반올림 없음).
        - drop_reason은 다음 순서로 부여:
          1) unknown_value → value가 None
          2) low_confidence → value_conf < conf_threshold(기본 0.94)
          3) duplicated_code_kept_last → 위 두 조건을 통과(포함 후보)했지만 동일 code가 여러개일 때 마지막만 포함

        순서는 Step 11 결과(step11_rows)의 원래 순서를 따릅니다.
        step11_rows가 없을 경우, 이전(제외 전용) 포맷으로 폴백합니다.
        """
        try:
            if not isinstance(intermediates, dict):
                return f"⚠️ intermediates 타입 이상: {type(intermediates)}"

            step11_rows = intermediates.get("step11_rows") or []
            header_roles = intermediates.get("header_roles") or {}
            stats = intermediates.get("step12_stats") or {}
            body_lines = intermediates.get("body_lines") or []

            # 표준화된 header_roles(list/any)를 roles mapping으로 변환하여 일관 사용
            try:
                roles_map = self._roles_to_mapping(header_roles)
            except Exception:
                roles_map = {}

            # 임계값: step12에서 사용한 값이 있으면 그 값을 따름
            try:
                conf_threshold = float(stats.get("conf_threshold", 0.94))
            except Exception:
                conf_threshold = 0.94

            # 결과 열의 column-level confidence를 그대로 사용
            try:
                res_info = roles_map.get("result") if isinstance(roles_map, dict) else None
                base_conf: float = float(res_info.get("confidence", 0.5)) if isinstance(res_info, dict) else 0.5
            except Exception:
                base_conf = 0.5

            # 행별 value 토큰의 OCR confidence 추출 (우선순위: _src_tokens['result'] → 라인/밴드 탐색)
            import math
            def _conf_trunc4_str(x: Any) -> str:
                try:
                    f = float(x)
                    if f < 0.0:
                        f = 0.0
                    elif f > 1.0:
                        f = 1.0
                    f4 = math.trunc(f * 10000) / 10000.0
                    return f"{f4:.4f}"
                except Exception:
                    return ""
            num_re = re.compile(r"^\s*([+-]?\d+(?:[.,]\d+)?)")
            def _norm_num_str(s: Optional[str]) -> Optional[str]:
                if not s or not isinstance(s, str):
                    return None
                t = s.strip().replace("·", ".").replace(",", ".")
                m = re.match(r"^[+-]?\d+(?:\.\d+)?", t)
                return m.group(0) if m else None

            def _value_token_conf_for_row(row_obj: Dict[str, Any]) -> Optional[float]:
                try:
                    # 0) Step 8에서 고정 저장된 토큰 우선 사용
                    st = row_obj.get("_src_tokens") if isinstance(row_obj.get("_src_tokens"), dict) else None
                    if isinstance(st, dict):
                        tok = st.get("result")
                        if isinstance(tok, dict):
                            cf = tok.get("confidence")
                            if isinstance(cf, (int, float)):
                                try:
                                    fv = float(cf)
                                    return max(0.0, min(1.0, fv))
                                except Exception:
                                    pass
                    # 기준 숫자 문자열: result_norm 우선, 없으면 result에서 숫자 부분
                    target = row_obj.get("result_norm") if isinstance(row_obj.get("result_norm"), str) else None
                    if not target:
                        target = _norm_num_str(row_obj.get("result") if isinstance(row_obj.get("result"), str) else None)
                    if not target:
                        return None
                    # 특정 밴드(결과 열)에 속한 토큰만 대상으로 탐색
                    line_idx = row_obj.get("_line_idx")
                    bands = row_obj.get("_bands")
                    res_info = roles_map.get("result") if isinstance(roles_map, dict) else None
                    res_col = int(res_info.get("col_index", -1)) if isinstance(res_info, dict) else -1
                    if not (isinstance(line_idx, int) and isinstance(bands, list) and 0 <= res_col < len(bands)):
                        # 밴드 정보를 사용할 수 없으면 라인 전체에서 탐색(폴백)
                        line = body_lines[line_idx] if (isinstance(body_lines, list) and isinstance(line_idx, int) and 0 <= line_idx < len(body_lines)) else None
                        if not line:
                            return None
                        for tok in (line or []):
                            try:
                                if not isinstance(tok, dict):
                                    continue
                                txt = str(tok.get("text", "") or "").strip()
                                if not txt:
                                    continue
                                m = num_re.match(txt.replace("·", ".").replace(",", "."))
                                if not m:
                                    continue
                                num_txt = m.group(1)
                                if num_txt == target:
                                    conf = tok.get("confidence")
                                    if isinstance(conf, (int, float)):
                                        try:
                                            fv = float(conf)
                                            return max(0.0, min(1.0, fv))
                                        except Exception:
                                            return None
                            except Exception:
                                continue
                        return None

                    # 밴드 한정 탐색
                    L, R = bands[res_col]
                    line = body_lines[line_idx] if (isinstance(body_lines, list) and 0 <= line_idx < len(body_lines)) else None
                    if not line:
                        return None
                    # line은 토큰들의 리스트로 가정
                    best_conf = None
                    for tok in (line or []):
                        try:
                            if not isinstance(tok, dict):
                                continue
                            txt = str(tok.get("text", "") or "").strip()
                            if not txt:
                                continue
                            xl = tok.get("x_left"); xr = tok.get("x_right")
                            if not isinstance(xl, (int, float)) or not isinstance(xr, (int, float)):
                                continue
                            xc = (float(xl) + float(xr)) / 2.0
                            if not (L <= xc < R):
                                continue
                            m = num_re.match(txt.replace("·", ".").replace(",", "."))
                            if not m:
                                continue
                            num_txt = m.group(1)
                            conf = tok.get("confidence")
                            if num_txt == target and isinstance(conf, (int, float)):
                                try:
                                    fv = float(conf)
                                    return max(0.0, min(1.0, fv))
                                except Exception:
                                    return None
                            # 후보 중 가장 높은 confidence를 보조 선택지로 저장
                            if isinstance(conf, (int, float)):
                                cf = max(0.0, min(1.0, float(conf)))
                                if best_conf is None or cf > best_conf:
                                    best_conf = cf
                        except Exception:
                            continue
                    return best_conf
                except Exception:
                    return None

            # step11_rows가 없으면 이전 "제외 전용" 미리보기로 폴백
            if not step11_rows:
                out: List[str] = []
                out.append("🧾 Step 12: 제외된 tests (필터 사유 포함)")
                excluded = stats.get("excluded") if isinstance(stats, dict) else None
                if not excluded:
                    out.append(" (제외된 항목 없음)")
                    return "\n".join(out)
                # 폴백 시에도 신규 컬럼 순서를 유지
                labels = ["code", "value", "value_conf", "unit", "reference_min", "reference_max", "reason"]
                data: List[List[str]] = []
                def _d(v: Any) -> str:
                    try:
                        if v is None:
                            return "UNKNOWN"
                        s = str(v)
                        return s if s.strip() else "UNKNOWN"
                    except Exception:
                        return "UNKNOWN"
                for t in excluded:
                    reason = t.get("_excluded_reason")
                    if isinstance(reason, list):
                        reason_s = ",".join(reason)
                    else:
                        reason_s = _d(reason)
                    conf = t.get("_value_conf")
                    # 표시: 소숫점 네 자리에서 자르기(반올림 없음)
                    conf_s = _conf_trunc4_str(conf) if isinstance(conf, (int, float)) else ""
                    data.append([
                        _d(t.get("code")),
                        _d(t.get("value")),
                        conf_s,
                        _d(t.get("unit")),
                        _d(t.get("reference_min")),
                        _d(t.get("reference_max")),
                        reason_s,
                    ])
                widths = [len(l) for l in labels]
                for row in data:
                    for i, v in enumerate(row):
                        widths[i] = max(widths[i], len(v))
                def fmt_row(cells: List[str]) -> str:
                    parts = []
                    for i, v in enumerate(cells):
                        if labels[i] in ("value", "reference_min", "reference_max", "value_conf"):
                            parts.append(v.rjust(widths[i]))
                        else:
                            parts.append(v.ljust(widths[i]))
                    return " | ".join(parts)
                sep = "-+-".join(["-" * w for w in widths])
                out.append(fmt_row(labels))
                out.append(sep)
                for row in data:
                    out.append(fmt_row(row))
                return "\n".join(out)

            # 도우미: 문자열 숫자 → float
            def _to_float(v: Any) -> Optional[float]:
                if v is None:
                    return None
                if isinstance(v, (int, float)):
                    try:
                        return float(v)
                    except Exception:
                        return None
                if not isinstance(v, str):
                    return None
                try:
                    return float(v.replace(",", "."))
                except Exception:
                    return None

            # 1) Step11 기준(라인 순)으로 행 구성 + value_conf/1·2차 필터 사유 산정
            rows: List[Dict[str, Any]] = []
            for idx, r in enumerate(step11_rows):
                try:
                    code = r.get("name")
                    unit_raw = r.get("unit") if isinstance(r.get("unit"), str) else None
                    unit_canon = r.get("unit_canonical") if isinstance(r.get("unit_canonical"), str) else None
                    unit = unit_canon or unit_raw

                    val = _to_float(r.get("result_norm"))
                    rmin = _to_float(r.get("min_norm"))
                    rmax = _to_float(r.get("max_norm"))

                    # value_conf: result 열의 column-level confidence
                    try:
                        conf = max(0.0, min(1.0, float(base_conf)))
                    except Exception:
                        conf = 0.0

                    # 표시용 per-row value 토큰 confidence (가능하면 사용, 없으면 None)
                    tok_conf = _value_token_conf_for_row(r)

                    reasons: List[str] = []
                    if val is None:
                        reasons.append("unknown_value")
                    else:
                        if conf < conf_threshold:
                            reasons.append("low_confidence")

                    rows.append({
                        "code": code,
                        "unit": unit,
                        "reference_min": rmin,
                        "reference_max": rmax,
                        "value": val,
                        "_conf": conf,
                        "_tok_conf": tok_conf,
                        "_reasons": reasons,
                    })
                except Exception:
                    rows.append({
                        "code": None,
                        "unit": None,
                        "reference_min": None,
                        "reference_max": None,
                        "value": None,
                        "_conf": 0.5,
                        "_tok_conf": None,
                        "_reasons": ["parse_error"],
                    })

            # 2) 중복 코드 규칙 적용: (code, unit) 기준으로 마지막만 포함
            #    - 단위가 비어있으면 code만으로 판정
            last_index: Dict[tuple, int] = {}
            def _dup_key(t: Dict[str, Any]) -> Optional[tuple]:
                c = t.get("code")
                if not (isinstance(c, str) and c.strip()):
                    return None
                u = t.get("unit")
                if isinstance(u, str) and u.strip():
                    return (c.strip(), u.strip())
                return (c.strip(), None)

            for idx, t in enumerate(rows):
                k = _dup_key(t)
                if k is not None:
                    last_index[k] = idx
            for idx, t in enumerate(rows):
                k = _dup_key(t)
                if k is not None:
                    if not t["_reasons"] and last_index.get(k) != idx:
                        t["_reasons"].append("duplicated_code_kept_last")

            # 3) 테이블 렌더링
            labels = ["code", "value", "value_conf", "unit", "reference_min", "reference_max", "drop_reason"]

            def _disp(v: Any) -> str:
                try:
                    if v is None:
                        return "UNKNOWN"
                    s = str(v)
                    return s if s.strip() else "UNKNOWN"
                except Exception:
                    return "UNKNOWN"

            data: List[List[str]] = []
            for t in rows:
                reason_s = ",".join(t["_reasons"]) if t["_reasons"] else ""
                # 표시: value 토큰 신뢰도가 있으면 그것을 사용, 없으면 column-level 사용 (소숫점 네 자리에서 자르기)
                disp_conf = t.get("_tok_conf") if isinstance(t.get("_tok_conf"), (int, float)) else t.get("_conf")
                conf_s = _conf_trunc4_str(disp_conf) if isinstance(disp_conf, (int, float)) else ""
                data.append([
                    _disp(t.get("code")),
                    _disp(t.get("value")),
                    conf_s,
                    _disp(t.get("unit")),
                    _disp(t.get("reference_min")),
                    _disp(t.get("reference_max")),
                    reason_s,
                ])

            widths = [len(l) for l in labels]
            for row in data:
                for i, v in enumerate(row):
                    widths[i] = max(widths[i], len(v))

            def fmt_row(cells: List[str]) -> str:
                parts = []
                for i, v in enumerate(cells):
                    if labels[i] in ("value", "reference_min", "reference_max", "value_conf"):
                        parts.append(v.rjust(widths[i]))
                    else:
                        parts.append(v.ljust(widths[i]))
                return " | ".join(parts)

            sep = "-+-".join(["-" * w for w in widths])
            out: List[str] = []
            out.append("🧾 Step 12: 포함/제외 tests 전체 (라인 순)")
            out.append(fmt_row(labels))
            out.append(sep)
            for row in data:
                out.append(fmt_row(row))

            return "\n".join(out)
        except Exception as e:
            return f"⚠️ debug_step12 포맷팅 중 오류: {type(e).__name__}: {e}"

    # -----------------------
    # Debug helpers (Step 13: Final JSON)
    # -----------------------
    def debug_step13(
        self,
        intermediates: Intermediates | Dict[str, Any],
    ) -> str:
        """Step 13(최종 JSON) 결과 미리보기와 QA 요약.

        표시는: code | unit | reference_min | reference_max | value 
        """
        try:
            if not isinstance(intermediates, dict):
                return f"⚠️ intermediates 타입 이상: {type(intermediates)}"

            final_doc = intermediates.get("final_doc") or {}
            tests = final_doc.get("tests") if isinstance(final_doc, dict) else []
            if not tests:
                return "ℹ️ final_doc.tests 비어있음 (Step 13 미실행 또는 이전 단계 결과 없음)"

            # 결과 열의 column-level confidence를 기본값으로 사용
            # 표준화된 header_roles(list/any)를 roles mapping으로 변환하여 사용
            header_roles = intermediates.get("header_roles")
            try:
                roles_map = self._roles_to_mapping(header_roles)
                res_info = roles_map.get("result") if isinstance(roles_map, dict) else None
                base_conf: float = float(res_info.get("confidence", 0.5)) if isinstance(res_info, dict) else 0.5
            except Exception:
                base_conf = 0.5

            def _disp(v: Any) -> str:
                try:
                    if v is None:
                        return "UNKNOWN"
                    s = str(v)
                    if not s.strip():
                        return "UNKNOWN"
                    return s
                except Exception:
                    return "UNKNOWN"

            labels = ["code", "value", "unit", "reference_min", "reference_max"]
            data: List[List[str]] = []
            for t in tests:
                code = t.get("code")
                val = t.get("value")
                unit = t.get("unit")
                rmin = t.get("reference_min")
                rmax = t.get("reference_max")

                data.append([
                    _disp(code),
                    _disp(val),
                    _disp(unit),
                    _disp(rmin),
                    _disp(rmax),
                ])

            widths = [len(l) for l in labels]
            for row in data:
                for i, v in enumerate(row):
                    widths[i] = max(widths[i], len(v))

            def fmt_row(cells: List[str]) -> str:
                parts = []
                for i, v in enumerate(cells):
                    if labels[i] in ("value", "reference_min", "reference_max"):
                        parts.append(v.rjust(widths[i]))
                    else:
                        parts.append(v.ljust(widths[i]))
                return " | ".join(parts)

            sep = "-+-".join(["-" * w for w in widths])
            out: List[str] = []
            # Meta header
            try:
                hosp = final_doc.get("hospital_name")
                client = final_doc.get("client_name")
                patient = final_doc.get("patient_name")
                date = final_doc.get("inspection_date")
                def _m(v: Any) -> str:
                    try:
                        return str(v) if (v is not None and str(v).strip()) else "(None)"
                    except Exception:
                        return "(None)"
                out.append(f"🏥 hospital_name: {_m(hosp)}")
                out.append(f"👤 client_name  : {_m(client)}")
                out.append(f"🐾 patient_name : {_m(patient)}")
                out.append(f"🗓  inspection_date: {_m(date)}")
                out.append("")
            except Exception:
                pass

            out.append("🧾 Step 13: 최종 JSON")
            out.append(fmt_row(labels))
            out.append(sep)
            for row in data:
                out.append(fmt_row(row))

            qa = intermediates.get("qa_summary") or {}
            if qa:
                out.append("")
                out.append("📊 QA 요약:")
                for k, v in qa.items():
                    out.append(f" - {k}: {v}")

            # Pretty-print final JSON as part of the debug output
            try:
                import json as _json
                out.append("")
                out.append("🧾 Final JSON:")
                if isinstance(final_doc, dict):
                    out.append(_json.dumps(final_doc, ensure_ascii=False, indent=2))
                else:
                    out.append(str(final_doc))
            except Exception:
                pass

            return "\n".join(out)
        except Exception as e:
            return f"⚠️ debug_step13 포맷팅 중 오류: {type(e).__name__}: {e}"

    # -----------------------
    # Step 12 filters: UNKNOWN, low confidence, de-dup by code(keep last)
    # -----------------------
    def _apply_step12_filters(self, final_doc: DocumentResult, header_roles: Any, *, conf_threshold: float = 0.94) -> Tuple[DocumentResult, Dict[str, Any]]:
        """Apply Step 12 filters on final_doc.tests.

        Rules:
        - Drop items with value is None (UNKNOWN)
        - Compute value_conf with same heuristic as debug_step12 and drop if < conf_threshold
        - De-duplicate by code, keeping the last occurrence

        Returns updated final_doc and stats.
        """
        if not isinstance(final_doc, dict):
            return final_doc, {"removed_unknown": 0, "removed_low_conf": 0, "dedup_removed": 0, "conf_threshold": conf_threshold}

        tests = list(final_doc.get("tests") or [])
        if not tests:
            return final_doc, {"removed_unknown": 0, "removed_low_conf": 0, "dedup_removed": 0, "conf_threshold": conf_threshold, "excluded": []}

        # Base confidence from header result role
        try:
            roles_map = self._roles_to_mapping(header_roles)
            res_info = roles_map.get("result") if isinstance(roles_map, dict) else None
            base_conf: float = float(res_info.get("confidence", 0.5)) if isinstance(res_info, dict) else 0.5
        except Exception:
            base_conf = 0.5

        def compute_conf(t: Dict[str, Any]) -> float:
            """행별 value_conf는 결과 열의 column-level confidence를 그대로 사용한다.
            이전의 범위/단위 기반 보정 휴리스틱은 제거.
            """
            try:
                return max(0.0, min(1.0, float(base_conf)))
            except Exception:
                return 0.5

        # 1) Remove UNKNOWN values
        removed_unknown = 0
        filtered = []
        excluded: List[Dict[str, Any]] = []
        for t in tests:
            try:
                if t.get("value") is None:
                    removed_unknown += 1
                    # 기록: 어떤 필터에 걸렸는지
                    rec = dict(t)
                    rec["_excluded_reason"] = ["unknown_value"]
                    excluded.append(rec)
                    continue
            except Exception:
                pass
            filtered.append(t)

        # 2) Remove low confidence
        removed_low_conf = 0
        filtered2 = []
        for t in filtered:
            try:
                conf = compute_conf(t)
                if conf < conf_threshold:
                    removed_low_conf += 1
                    rec = dict(t)
                    rec["_excluded_reason"] = ["low_confidence" ]
                    rec["_value_conf"] = round(float(conf), 3)
                    excluded.append(rec)
                    continue
            except Exception:
                pass
            filtered2.append(t)

        # 3) De-duplicate by (code, unit) when unit is available; else by code (keep the last occurrence)
        #    - 퍼센트와 절대치(예: RETIC% vs RETIC#)가 공존하는 경우, 단위가 다르면 서로 다른 측정으로 간주해 보존합니다.
        #    - 단위가 명확하지 않은(비어있거나 None) 경우에는 기존대로 code만으로 중복 판정합니다.
        dedup_removed = 0
        # 마지막 인덱스 기록: key = (code, unit_or_none)
        last_index: Dict[tuple, int] = {}
        def _dedup_key(t: Dict[str, Any]) -> Optional[tuple]:
            c = t.get("code")
            if not (isinstance(c, str) and c.strip()):
                return None
            u = t.get("unit")
            u_key: Optional[str]
            if isinstance(u, str) and u.strip():
                u_key = u.strip()
            else:
                u_key = None
            return (c.strip(), u_key)

        for idx, t in enumerate(filtered2):
            k = _dedup_key(t)
            if k is not None:
                last_index[k] = idx

        result: List[Dict[str, Any]] = []
        for idx, t in enumerate(filtered2):
            k = _dedup_key(t)
            if k is not None:
                if last_index.get(k) != idx:
                    dedup_removed += 1
                    rec = dict(t)
                    rec["_excluded_reason"] = ["duplicated_code_kept_last"]
                    excluded.append(rec)
                    continue
            result.append(t)

        new_doc = dict(final_doc)
        new_doc["tests"] = result
        stats = {
            "removed_unknown": removed_unknown,
            "removed_low_conf": removed_low_conf,
            "dedup_removed": dedup_removed,
            "conf_threshold": conf_threshold,
            "excluded": excluded,
        }
        return new_doc, stats

 
