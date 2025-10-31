"""
검사 단위 사전 (reference/unit_lexicon)
-----------------------------------------------------
- 테이블 파이프라인(값/단위 분리, 열 추론, 최종 정규화)에서 사용할 단위 렉시콘을 생성/캐시합니다.
- reference_data.py 의 REFERENCE_TESTS 내 unit 값을 수집하여
        'canonical unit' 집합을 만들고, 다양한 OCR/표기 변형(µ/μ/u, l/L/ℓ, K/10^3, 공백/대소문 등)에 견딜 수 있는
        변형 인덱스를 함께 제공합니다.

주요 제공 함수
- get_unit_lexicon(): dict 반환. 최초 1회 빌드 후 메모리 캐시.
- list_all_units(): 모든 canonical 단위 목록 반환.
- resolve_unit(token: str, lexicon=None) -> Optional[str]:
    토큰(예: OCR로 추출된 "k/uL", "MG/DL", "10^3/uL")을 가장 적합한 canonical 단위로 해석.

정책 업데이트(일원화)
- CBC 절대수 단위는 '10^3/µL', '10³/µL' 등 혼재 가능성을 제거하고 canonical 을 'K/µL' 로 일원화합니다.
- 정규화 시 '10³/µL', '10³/uL', '10^3/µL', 'x10^3/uL', 'k/ul', 'K/UL' 등은 모두 'K/µL' 로 매핑됩니다.

주의사항
- ratios 등 단위가 None/빈 문자열인 항목은 제외합니다.
"""
from __future__ import annotations

from typing import Dict, Optional, Set, Tuple
import re

# 공통 단위 정규화 유틸리티 import
from ..unit_normalizer import fold_micro, fold_liter

# 모듈 전역 캐시
_UNIT_LEXICON_CACHE: Optional[Dict[str, object]] = None


_MICRO_CHARS = {"µ", "μ"}  # micro sign vs greek mu
_L_LIKE = {"L", "l", "ℓ"}


def _normalize_unit_canonical(s: str) -> str:
    # canonical 표기 정리: micro/L 통일, 다중 공백/슬래시 정리
    t = s.strip()
    t = fold_micro(t)
    t = fold_liter(t)
    t = re.sub(r"\s+", "", t)
    # '^' 지수와 유니코드 지수 혼용 보정은 canonical 그대로 보존(여기선 삭제하지 않음)
    return t


def _alias_pow10_to_prefix(c: str) -> str:
    """일부 지수형 표기를 접두(prefix) 표기로 일원화합니다.

    - 10^3/µL, 10³/µL (및 uL 변형) -> K/µL
    - 그 외는 변경하지 않음.
    """
    t = c
    # micro/liter 접기 먼저 보장된 상태에서 호출된다고 가정하지만, 방어적으로 한 번 더 처리
    t = _normalize_unit_canonical(t)
    # 10^3 또는 10³ → K/µL
    if re.fullmatch(r"10\^[ ]*3/µL", t) or re.fullmatch(r"10³/µL", t):
        return "K/µL"
    # 10^6 또는 10⁶ → M/µL
    if re.fullmatch(r"10\^[ ]*6/µL", t) or re.fullmatch(r"10⁶/µL", t):
        return "M/µL"
    return t


def _generate_unit_keys(unit: str) -> Tuple[str, str]:
    """단위에서 매칭용 키를 생성합니다.
    - upper_key: 대문자 + 공백 제거 + micro/liter 접기
    - alnum_key: A-Z0-9 만 남긴 키 (특수문자 유실/OCR 변형 대비)
    예) "mg/dL" -> upper_key: "MG/DL", alnum_key: "MGDL"
    예) "10³/µL" -> upper_key: "10³/µL" (대문자화 영향 없음), alnum_key: "103L"
    """
    t = _normalize_unit_canonical(unit)
    upper = t.upper()
    # micro는 대문자 변환에서 영향 없음(µ == µ), liter는 이미 L
    alnum = re.sub(r"[^A-Z0-9]", "", upper)
    return upper, alnum


def _curated_variants_for(canonical: str) -> Set[str]:
    """일부 canonical 단위에 대해 널리 쓰이는 변형을 추가로 생성합니다.
    예) 10³/µL -> {10^3/µL, K/µL, K/uL, K/UL, X10^3/µL, x10^3/uL, k/ul}
    """
    c = _normalize_unit_canonical(canonical)
    vars: Set[str] = set()

    def add(*vs: str) -> None:
        for v in vs:
            if v:
                vars.add(v)

    # 10^3 per µL 계열 (지수 표기가 canonical 인 경우)
    if re.fullmatch(r"10[\^³][0-9]+/µL", c):
        # 지수 추출(103 형태)
        exp = re.sub(r"^10[\^³]([0-9]+).*$", r"\1", c)
        add(f"10^{exp}/µL", f"10^{exp}/uL", f"10^{exp}/UL")
        add(f"x10^{exp}/µL", f"x10^{exp}/uL", f"x10^{exp}/UL")
        add(f"X10^{exp}/µL", f"X10^{exp}/uL", f"X10^{exp}/UL")
        if exp == "3":
            # K/µL 동치 허용
            add("K/µL", "K/uL", "K/UL", "k/µl", "k/ul")
        if exp == "6":
            # M/µL 동치 허용
            add("M/µL", "M/uL", "M/UL", "m/µl", "m/ul")

    # K/µL 을 canonical 로 일원화한 경우: 널리 쓰이는 지수 표기를 변형으로 추가
    if re.fullmatch(r"(?i)k/[µμ]L", c):
        exp = "3"
        add("K/uL", "K/UL", "k/µl", "k/ul")
        add(f"10^{exp}/µL", f"10^{exp}/uL", f"10^{exp}/UL")
        add(f"x10^{exp}/µL", f"x10^{exp}/uL", f"x10^{exp}/UL")
        add("10³/µL")

    # M/µL 을 canonical 로 일원화한 경우: 널리 쓰이는 지수 표기를 변형으로 추가
    if re.fullmatch(r"(?i)m/[µμ]L", c):
        exp = "6"
        add("M/uL", "M/UL", "m/µl", "m/ul")
        add(f"10^{exp}/µL", f"10^{exp}/uL", f"10^{exp}/UL")
        add(f"x10^{exp}/µL", f"x10^{exp}/uL", f"x10^{exp}/UL")
        add("10⁶/µL")

    # g/dL, mg/dL, ng/mL 등 대소문/슬래시/L 문양 변형
    if re.search(r"/ML$|/DL$|/L$", c.upper()) or c.upper() in {"G/DL", "MG/DL", "UG/ML", "UG/L", "NG/ML", "MMOL/L", "IU/L", "U/L"}:
        base = c.upper()
        add(base, base.replace("/ML", "/mL").replace("/DL", "/dL"))
        # micro 표기 변형
        add(base.replace("UG/ML", "µg/mL").replace("UG/L", "µg/L"))

    # 퍼센트/초/압력 등의 간단 표기
    if c in {"%", "SEC", "MMHG", "G/DL", "U/L", "IU/L", "MMOL/L"}:
        add(c, c.lower(), c.capitalize())

    return vars


def build_unit_lexicon() -> Dict[str, object]:
    """단위 렉시콘을 빌드하여 반환합니다.

    반환 구조 dict:
    - canonical_set: Set[str]           모든 canonical 단위(원형 보존)
    - upper_index: Dict[str, str]       upper_key -> canonical (정확/즉시 매칭용)
    - alnum_index: Dict[str, Set[str]]  alnum_key -> {canonical...} (강건 매칭용)
    """
    from .reference_data import REFERENCE_TESTS

    units: Set[str] = set()

    # REFERENCE_TESTS 내 unit 수집 (None/빈 문자열 제외)
    for item in REFERENCE_TESTS:
        try:
            u = item.get("unit") if isinstance(item, dict) else None
            if u is None:
                continue
            if isinstance(u, str) and u.strip():
                units.add(u)
        except Exception:
            continue

    # canonical 표기 정리 (+ 정책 기반 alias 반영)
    canonical_set: Set[str] = set()
    for u in sorted(units):
        cu = _normalize_unit_canonical(u)
        cu = _alias_pow10_to_prefix(cu)
        canonical_set.add(cu)

    # 기본 인덱스 생성
    upper_index: Dict[str, str] = {}
    alnum_index: Dict[str, Set[str]] = {}

    # canonical 자체 등록
    for cu in canonical_set:
        uk, ak = _generate_unit_keys(cu)
        upper_index[uk] = cu
        alnum_index.setdefault(ak, set()).add(cu)

    # 큐레이션된 변형 등록
    for cu in list(canonical_set):
        for v in _curated_variants_for(cu):
            uk, ak = _generate_unit_keys(v)
            upper_index[uk] = cu
            alnum_index.setdefault(ak, set()).add(cu)

    return {
        "canonical_set": canonical_set,
        "upper_index": upper_index,
        "alnum_index": alnum_index,
    }


def get_unit_lexicon(force_rebuild: bool = False) -> Dict[str, object]:
    global _UNIT_LEXICON_CACHE
    if force_rebuild or _UNIT_LEXICON_CACHE is None:
        _UNIT_LEXICON_CACHE = build_unit_lexicon()
    return _UNIT_LEXICON_CACHE


def list_all_units() -> Set[str]:
    return set(get_unit_lexicon()["canonical_set"])  # type: ignore[index]


def resolve_unit(token: str, lexicon: Optional[Dict[str, object]] = None) -> Optional[str]:
    """토큰을 가장 그럴듯한 canonical 단위로 해석합니다.

    매칭 전략 (보수적):
    1) 대소문자/공백 제거 + micro/liter 통일 후 upper_key 로 정확 매칭
    2) 알파넘 키 일치 후보가 한 개면 반환
    3) 복수 후보일 땐 micro/L/케이스 변형 힌트로 1회 필터링
    4) 여전히 모호하면 None (상위 로직에서 추가 단서 활용)
    """
    if not token:
        return None

    lx = lexicon or get_unit_lexicon()
    upper_index: Dict[str, str] = lx["upper_index"]  # type: ignore[index]
    alnum_index: Dict[str, Set[str]] = lx["alnum_index"]  # type: ignore[index]

    raw = token.strip()
    if not raw:
        return None

    # 1) 정확 매칭
    t = _normalize_unit_canonical(raw)
    upper_key = t.upper()
    if upper_key in upper_index:
        return upper_index[upper_key]

    # 2) 알파넘 강건 매칭
    alnum_key = re.sub(r"[^A-Z0-9]", "", upper_key)
    candidates = set(alnum_index.get(alnum_key, set()))
    if not candidates:
        return None
    if len(candidates) == 1:
        return next(iter(candidates))

    # 3) 힌트 기반 필터링: micro/L/지수/접두 동치
    hints = set()
    if any(ch in raw for ch in _MICRO_CHARS) or "u" in raw:
        hints.add("micro")
    if any(ch in raw for ch in _L_LIKE):
        hints.add("liter")
    if any(sym in raw for sym in ("^", "³", "K", "M", "x10")):
        hints.add("pow10")
    if hints:
        def _match_hint(cu: str) -> bool:
            cu_up = cu.upper()
            if "micro" in hints and "µ" not in cu:
                return False
            if "liter" in hints and "L" not in cu_up:
                return False
            if "pow10" in hints and not ("10" in cu_up or "/UL" in cu_up or "/µL" in cu_up):
                return False
            return True
        filtered = {c for c in candidates if _match_hint(c)}
        if len(filtered) == 1:
            return next(iter(filtered))
        if len(filtered) > 1:
            candidates = filtered

    # 4) 여전히 복수면 None
    return None


__all__ = [
    "get_unit_lexicon",
    "build_unit_lexicon",
    "list_all_units",
    "resolve_unit",
]
