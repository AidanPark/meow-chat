"""
검사코드 정규화 모듈

OCR로 인식된 검사항목 코드 텍스트를 표준(canonical) 코드로 변환합니다.
code_lexicon의 resolve_code를 래핑하여 추가적인 정규화 로직을 제공합니다.

주요 기능:
- 괄호 제거: "SODIUM(Na+)" → "SODIUM"
- 접미사 제거: "WBC-A" → "WBC"
- 0/O 혼동 보정: "p02" → "pO2"
- 외부 리졸버 지원: 사용자 정의 해석 로직 연결 가능

사용 예시:
    from src.services.lab_extraction.code_normalizer import resolve_code_with_fallback

    lexicon = get_code_lexicon()
    result = resolve_code_with_fallback("SODIUM(Na+)", lexicon)
    # result: "SODIUM"
"""
from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional

# 타입 별칭
Lexicon = Dict[str, Any]
ExtResolver = Callable[[str, Lexicon], Optional[str]]

# 외부 사전 리졸버 (선택) - 순환 의존 방지 위해 optional import
try:
    from .reference.code_lexicon import resolve_code as _lex_resolve_code  # type: ignore
except Exception:  # pragma: no cover
    _lex_resolve_code = None  # type: ignore


def normalize_code_candidate(s: str) -> str:
    """검사코드 후보 텍스트를 보수적으로 정규화합니다.

    변환 규칙:
    - 주변 공백 제거
    - 괄호 이후 내용 제거 (예: "LYMPHO(%)" → "LYMPHO")
    - 퍼센트 기호 제거 (예: "NEUT%" → "NEUT")
    - 말단 노이즈 하이픈 제거 (예: "Cl-" → "Cl")

    매개변수:
        s: 정규화할 검사코드 텍스트

    반환값:
        정규화된 검사코드 문자열

    사용 예시:
        >>> normalize_code_candidate("LYMPHO(%)")
        'LYMPHO'
        >>> normalize_code_candidate("NEUT%")
        'NEUT'
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
    lexicon: Lexicon,
    ext_resolver: Optional[ExtResolver] = None,
) -> Optional[str]:
    """검사코드 텍스트를 표준 코드로 해석합니다.

    여러 단계의 폴백 전략을 사용하여 OCR 오류에 강건한 코드 해석을 제공합니다.

    매개변수:
        text: OCR로 인식된 검사항목 코드 텍스트
        lexicon: 검사코드 사전 (get_code_lexicon()으로 생성)
        ext_resolver: 외부 리졸버 함수 (선택적, 사용자 정의 해석 로직)

    반환값:
        표준화된 검사코드 문자열 또는 None (해석 실패 시)

    해석 전략 (순서대로 시도):
        1. 외부 리졸버가 있으면 먼저 시도
        2. 전체 텍스트로 code_lexicon.resolve_code 호출
        3. 괄호 앞부분만 추출하여 재시도 (예: "SODIUM(Na+)" → "SODIUM")
        4. 접미사 제거 후 재시도 (예: "WBC-A" → "WBC")

    사용 예시:
        >>> lexicon = get_code_lexicon()
        >>> resolve_code_with_fallback("SODIUM(Na+)", lexicon)
        'SODIUM'
        >>> resolve_code_with_fallback("WBC-A", lexicon)
        'WBC'
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
