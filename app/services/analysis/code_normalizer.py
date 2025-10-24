"""
검사 코드 정규화/해석 유틸리티 모듈
-----------------------------------------------------
unit_normalizer.py와 유사한 분리 스타일로, 코드 텍스트의 보수적 정규화와
사전(lexicon)을 이용한 해석을 제공합니다.

우선순위:
1) reference.code_lexicon.resolve_code 사용 가능 시 우선
2) 호출 측에서 주입한 ext_resolver 콜백
3) 내부 휴리스틱(upper_index, 키 직접/대소문 무시 매칭, 간단 전처리)

주의: 본 모듈은 상태가 없으며, lexicon을 호출 측에서 주입받습니다.
"""
from __future__ import annotations

import re
from typing import Any, Callable, Dict, Optional, List

# 외부 사전 리졸버 (선택) - 순환 의존 방지 위해 optional import
try:
    from .reference.code_lexicon import resolve_code as _lex_resolve_code  # type: ignore
except Exception:  # pragma: no cover
    _lex_resolve_code = None  # type: ignore


def normalize_code_candidate(s: str) -> str:
    """검사코드 후보 텍스트를 보수적으로 정규화.

    - 주변 공백 제거
    - 괄호 이후 내용 제거 (예: "LYMPHO(%)" -> "LYMPHO")
    - 퍼센트 기호 제거 (예: "NEUT%" -> "NEUT")
    - 말단 노이즈 하이픈 제거 (예: "Cl-" -> "Cl")
    """
    t = s.strip()
    if "(" in t:
        t = t.split("(", 1)[0]
    t = t.replace("%", "").strip()
    # 말단 하이픈/대시류 제거: Cl-, Na−, K– 같은 OCR 노이즈 방지
    # 단, 중간 하이픈은 보존 (예: "ALP-iso" 등)
    t = re.sub(r"[\-−–—]+$", "", t).strip()
    return t


def resolve_code_with_fallback(
    text: str,
    lexicon: Optional[Dict[str, Any]],
    *,
    ext_resolver: Optional[Callable[[str, Dict[str, Any]], Optional[str]]] = None,
) -> Optional[str]:
    """코드 텍스트를 표준 코드로 해석.

    우선순위:
    1) reference.code_lexicon.resolve_code (가능 시)
    2) ext_resolver 콜백
    3) 내부 휴리스틱(upper_index/직접 키/대문자 동등)
    """
    if not text:
        return None
    if not isinstance(lexicon, dict) or not lexicon:
        # 사전이 없으면 해석 불가
        return None

    raw = text

    # 외부 리졸버 후보 생성: '-A' 접미 제거 변형 우선
    candidates_for_external: List[str] = []
    try:
        base = raw
        if re.search(r"-a$", raw.strip(), flags=re.IGNORECASE):
            base = re.sub(r"-a$", "", raw.strip(), flags=re.IGNORECASE)
            # upper_index에 존재하면 베이스를 우선 후보로
            try:
                up_idx = lexicon.get("upper_index", {})  # type: ignore[assignment]
                if isinstance(up_idx, dict):
                    up_key = re.sub(r"\s+", "", base.upper())
                    if up_key in up_idx:
                        candidates_for_external.append(base)
            except Exception:
                candidates_for_external.append(base)
        candidates_for_external.append(raw)
    except Exception:
        candidates_for_external = [raw]

    # 1) 외부 사전 리졸버(resolve_code)가 있으면 먼저 시도
    if _lex_resolve_code is not None:
        for cand in candidates_for_external:
            try:
                # trailing '#': base 우선 규칙
                if re.search(r"#\s*$", cand):
                    base2 = re.sub(r"#\s*$", "", cand)
                    code = _lex_resolve_code(base2, lexicon)
                    if code:
                        return code
                code = _lex_resolve_code(cand, lexicon)
                if code:
                    return code
            except Exception:
                continue

    # 2) 호출 측에서 주입한 ext_resolver
    if ext_resolver is not None:
        try:
            code = ext_resolver(text, lexicon)
            if code:
                return code
        except Exception:
            pass

    # 3) 내부 휴리스틱: upper_index 및 키 직접 매칭
    def _try_keys(c: str) -> Optional[str]:
        try:
            up_idx = lexicon.get("upper_index")  # type: ignore[assignment]
            if isinstance(up_idx, dict):
                up_key = re.sub(r"\s+", "", c.upper())
                if up_key in up_idx:
                    return up_idx[up_key]
        except Exception:
            pass
        try:
            if c in lexicon:  # type: ignore[operator]
                return c
            cu = c.upper()
            for k in list(lexicon.keys()):  # type: ignore[union-attr]
                if isinstance(k, str) and k.upper() == cu:
                    return k
        except Exception:
            pass
        return None

    # 후보들: 원문/트림/대문자/간단정규화/정규화+대문자 + '-A' 접미 제거 변형
    candidates: List[str] = []
    seen: set[str] = set()

    def _add(c: Optional[str]) -> None:
        if not c:
            return
        cc = c.strip()
        if not cc:
            return
        if cc not in seen:
            candidates.append(cc)
            seen.add(cc)

    def _variants(base: str) -> List[str]:
        out = [base]
        try:
            if re.search(r"-a$", base, flags=re.IGNORECASE):
                out.append(re.sub(r"-a$", "", base, flags=re.IGNORECASE))
        except Exception:
            pass
        return out

    for base in [text, text.strip()]:
        for v in _variants(base):
            _add(v)
            _add(v.upper())

    norm = normalize_code_candidate(text)
    if norm:
        for v in _variants(norm):
            _add(v)
            _add(v.upper())

    for c in candidates:
        try:
            if re.search(r"#\s*$", c):
                c_base = re.sub(r"#\s*$", "", c)
                key = _try_keys(c_base)
                if key:
                    return key
        except Exception:
            pass
        key = _try_keys(c)
        if key:
            return key

    return None
