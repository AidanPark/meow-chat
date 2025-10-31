"""
검사항목 코드 사전 (reference/code_lexicon)
-----------------------------------------------------
- 테이블 바디 시작 검출 및 바디 필터링에서 사용할 견고한 코드 사전을 생성/캐시합니다.
- reference_data.py 의 REFERENCE_TESTS 에서 code 값을 수집합니다.
- OCR 변형(대/소문자, 특수문자 누락 등)에 견디기 위해 알파넘(영문/숫자만) 인덱스를 함께 생성합니다.

주요 제공 함수
- get_code_lexicon(): dict 반환. 최초 1회 빌드 후 메모리 캐시.
- list_all_codes(): 모든 canonical 코드 목록 반환.
- resolve_code(token: str, lexicon=None) -> Optional[str]:
    토큰(예: OCR로 추출된 "NEU%", "Na+", "BUN/CRE")을 가장 적합한 canonical 코드로 해석.

주의사항
- 모호성(예: "NA" → {"Na", "Na+"})이 해소되지 않으면 None을 반환하여
    상위 로직에서 추가 힌트(기호 존재, 위치, 주변 텍스트 등)로 재시도하도록 설계했습니다.
"""
from __future__ import annotations

import re
from typing import Dict, Optional, Set, Tuple

# 모듈 전역 캐시
_LEXICON_CACHE: Optional[Dict[str, object]] = None


def _generate_code_variants(code: str) -> Tuple[str, str]:
    """코드에서 매칭에 사용할 2가지 키를 생성합니다.
    - upper_key: 대문자 + 공백 제거 (원형 보존에 유리, 정확 매칭용)
    - alnum_key: A-Z0-9 만 남긴 키 (특수문자 유실/OCR 변형 대비)

    예)
      "WBC-NEU%" -> upper_key: "WBC-NEU%", alnum_key: "WBCNEU"
      "Na/K"     -> upper_key: "NA/K",      alnum_key: "NAK"
    """
    upper = re.sub(r"\s+", "", code.upper())
    alnum = re.sub(r"[^A-Z0-9]", "", upper)
    return upper, alnum


def build_code_lexicon() -> Dict[str, object]:
    """사전을 빌드하여 반환합니다.

    반환 구조 dict:
    - canonical_set: Set[str]           모든 canonical 코드(원본 케이스 보존)
    - upper_index: Dict[str, str]       upper_key -> canonical (정확/즉시 매칭용)
    - alnum_index: Dict[str, Set[str]]  alnum_key -> {canonical...} (강건 매칭용)
    """
    # 지연 import (순환 의존성 최소화)
    from .reference_data import REFERENCE_TESTS

    codes: Set[str] = set()
    # REFERENCE_TESTS 항목들에서 code 수집
    for item in REFERENCE_TESTS:
        try:
            code = item.get("code") if isinstance(item, dict) else None
            if code:
                codes.add(code)
        except Exception:
            continue

    # 대소문자만 다른 코드들은 하나로 통합 (대문자 사용 비율이 높은 것을 남김)
    by_upper: Dict[str, Set[str]] = {}
    for c in codes:
        key = re.sub(r"\s+", "", c.upper())
        by_upper.setdefault(key, set()).add(c)

    def _uppercase_score(s: str) -> tuple:
        ups = sum(1 for ch in s if ch.isupper())
        all_up = int(s == s.upper())
        return (all_up, ups, -len(s), s)

    canonical_selected: Set[str] = set()
    for key, variants in by_upper.items():
        try:
            chosen = sorted(list(variants), key=_uppercase_score, reverse=True)[0]
        except Exception:
            chosen = sorted(list(variants))[0]
        canonical_selected.add(chosen)

    canonical_set: Set[str] = set(sorted(canonical_selected))

    upper_index: Dict[str, str] = {}
    alnum_index: Dict[str, Set[str]] = {}

    for code in canonical_set:
        upper_key, alnum_key = _generate_code_variants(code)
        # upper_index 충돌 시 규칙: 완전 대문자 표기를 우선 채택
        if upper_key in upper_index:
            existing = upper_index[upper_key]
            try:
                if isinstance(existing, str) and existing != existing.upper() and code == code.upper():
                    upper_index[upper_key] = code
            except Exception:
                # 문제가 있으면 기존 동작 유지(덮어쓰기)
                upper_index[upper_key] = code
        else:
            upper_index[upper_key] = code
        # alnum_index 는 다:1 가능 (동일 alnum 을 공유하는 코드들 존재 가능)
        alnum_index.setdefault(alnum_key, set()).add(code)

    return {
        "canonical_set": canonical_set,
        "upper_index": upper_index,
        "alnum_index": alnum_index,
    }


def get_code_lexicon(force_rebuild: bool = False) -> Dict[str, object]:
    """전역 캐시된 사전을 반환합니다. force_rebuild=True 면 재생성.
    새 코드가 참조 파일에 추가된 배포 이후, 프로세스 재시작 또는 force_rebuild 로 갱신 가능합니다.
    """
    global _LEXICON_CACHE
    if force_rebuild or _LEXICON_CACHE is None:
        _LEXICON_CACHE = build_code_lexicon()
    return _LEXICON_CACHE


def list_all_codes() -> Set[str]:
    """모든 canonical 코드를 반환합니다."""
    return set(get_code_lexicon()["canonical_set"])  # type: ignore[index]


def resolve_code(token: str, lexicon: Optional[Dict[str, object]] = None) -> Optional[str]:
    """토큰을 가장 그럴듯한 canonical 코드로 해석합니다.

    매칭 전략 (보수적):
    1) 대소문자/공백 제거한 upper_key 로 정확 매칭 시 즉시 반환
    2) 알파넘 키 일치 후보가 한 개면 반환
    3) 복수 후보일 땐 토큰의 특수기호(+,-,%,/,_ 등) 존재로 1회 필터링
    4) 추가 폴백: 숫자 '0' → 알파벳 'O' 치환 후 재시도 (OCR 혼동 완화: 예 'p02' → 'pO2')
    5) 여전히 모호하면 None (상위 로직에서 추가 단서 활용)
    """
    if not token:
        return None

    lx = lexicon or get_code_lexicon()
    upper_index: Dict[str, str] = lx["upper_index"]  # type: ignore[index]
    alnum_index: Dict[str, Set[str]] = lx["alnum_index"]  # type: ignore[index]

    raw = token.strip()
    if not raw:
        return None

    # 특수 정규화: '(%)', ' (%)', ' %' 같은 변형을 '%'로 통일
    # 예) 'LYMPH(%)' / 'LYMPH (%)' / 'LYMPH %' -> 'LYMPH%'
    def _normalize_percent_variants(s: str) -> str:
        s2 = s
        try:
            s2 = re.sub(r"\(\s*%\s*\)", "%", s2)
            s2 = re.sub(r"\s+%", "%", s2)
        except re.error:
            pass
        return s2

    # 추가: '(#)', ' #' 도 '#'로 통일
    def _normalize_hash_variants(s: str) -> str:
        s2 = s
        try:
            s2 = re.sub(r"\(\s*#\s*\)", "#", s2)
            s2 = re.sub(r"\s+#", "#", s2)
        except re.error:
            pass
        return s2

    raw_norm = _normalize_hash_variants(_normalize_percent_variants(raw))

    # '#'-base 우선 규칙: 토큰이 '#'(공백 포함)로 끝나고, 베이스가 사전에 존재하면 베이스를 우선 반환
    base_if_hash = None
    try:
        if re.search(r"#\s*$", raw_norm):
            base_if_hash = re.sub(r"#\s*$", "", raw_norm)
    except re.error:
        base_if_hash = None

    if base_if_hash:
        base_upper_key = re.sub(r"\s+", "", base_if_hash.upper())
        if base_upper_key in upper_index:
            return upper_index[base_upper_key]

    upper_key = re.sub(r"\s+", "", raw_norm.upper())
    # 1) 정확 매칭 (대/소문자, 공백 무시)
    if upper_key in upper_index:
        return upper_index[upper_key]

    # 2) 알파넘 강건 매칭
    alnum_key = re.sub(r"[^A-Z0-9]", "", upper_key)
    candidates = set(alnum_index.get(alnum_key, set()))
    # len==0 이어도 곧바로 반환하지 말고 0→O 폴백을 먼저 시도한다.
    if len(candidates) == 1:
        return next(iter(candidates))

    # 3) 특수기호 힌트 기반 필터링
    hints = {
        "+": "+",
        "-": "-",
        "%": "%",
        "/": "/",
        "_": "_",
        ".": ".",
    }
    present = {h for h, sym in hints.items() if sym in raw_norm}
    if present and candidates:
        filtered = {c for c in candidates if any(h in c for h in present)}
        if len(filtered) == 1:
            return next(iter(filtered))
        if len(filtered) > 1:
            candidates = filtered

    # 4) '0'→'O' 폴백: OCR 이 'O'를 '0'으로 읽은 케이스 보정 (예: p02 → pO2, C02 → CO2)
    try:
        upper_key_o = upper_key.replace("0", "O")
        if upper_key_o != upper_key and upper_key_o in upper_index:
            return upper_index[upper_key_o]

        alnum_key_o = alnum_key.replace("0", "O")
        if alnum_key_o != alnum_key:
            candidates_o = set(alnum_index.get(alnum_key_o, set()))
            if len(candidates_o) == 1:
                return next(iter(candidates_o))

            if candidates_o:
                # 기존 특수기호 힌트로 1회 더 필터링
                filtered_o = {c for c in candidates_o if any(h in c for h in present)} if 'present' in locals() else candidates_o
                if len(filtered_o) == 1:
                    return next(iter(filtered_o))
    except Exception:
        # 폴백 과정에서의 예외는 무시하고 상위 로직에 판단을 맡깁니다.
        pass

    # 폴백까지 실패했고 candidates도 없거나 모호하면 None
    if not candidates:
        return None

    # 5) 여전히 복수면 보수적으로 None 반환 (상위 로직에서 컨텍스트로 결정)
    return None


__all__ = [
    "get_code_lexicon",
    "build_code_lexicon",
    "list_all_codes",
    "resolve_code",
]
