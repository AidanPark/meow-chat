"""
단위 정규화 유틸리티 모듈
-----------------------------------------------------
단위 문자열의 기본적인 정규화 기능을 제공하는 공통 유틸리티입니다.

주요 기능:
1. 문자 정규화: µ, μ, u -> µ로 통일, l, L, ℓ -> L로 통일  
2. 공백 및 접두어 정규화
3. CBC 절대수 단위의 10^3 계열을 K로 변환 등

사용처:
- unit_lexicon.py: 복잡한 단위 사전 생성 시 기본 문자 정규화
- lab_table_extractor.py: 간단한 단위 정규화 (사전 없이)
"""
import re
from typing import Optional


def fold_micro(s: str) -> str:
    """다양한 'micro' 문자를 표준 'µ' 로 통일"""
    out = s
    # µ(U+00B5), μ(U+03BC) -> µ(U+00B5)
    out = out.replace("μ", "µ")
    
    # 'u' -> 'µ' (단위 문맥에서만 안전하게)
    # 시작(^) 또는 슬래시(/) 바로 뒤의 'u'만 치환
    # K, M 뒤의 'u'도 치환 (KuL -> K/µL, MuL -> M/µL)
    # 다음 문자가 l/L 또는 단어 경계일 때만
    out = re.sub(r"(^|/|[KM])u(?=(?:l|L|/|\b))", r"\1µ", out)
    return out


def fold_liter(s: str) -> str:
    """liter 표기를 대문자 L로 통일하되, 'mol' 같은 단위 내부의 l 은 보존한다.

    안전 규칙:
    - '/l' → '/L', '/dl' → '/dL', '/ml' → '/mL', '/ul' → '/uL' 등 슬래시 뒤 단위의 l 만 대문자화
    - 'µl'/'μl' → 'µL'
    - 그 외 'l' (예: 'mol', 'mmol') 은 변경하지 않음
    """
    out = s
    if not isinstance(out, str):
        return out
    # µl/μl → µL
    out = out.replace("µl", "µL").replace("μl", "µL")
    # 슬래시 뒤 소문자 l 을 대문자 L 로 (예: /dl, /ml, /ul, /l)
    out = re.sub(r"/(\s*[A-Za-zµμ]*?)l(\b)", lambda m: "/" + m.group(1) + "L" + m.group(2), out)
    return out


def normalize_unit_simple(unit: str) -> Optional[str]:
    """
    간단한 unit 정규화 - 접두어 제거 위주 (보수적 공백 처리)
    
    Args:
        unit: 원본 단위 문자열
        
    Returns:
        정규화된 단위 문자열 또는 None (정규화 실패시)
    """
    if not unit or not isinstance(unit, str):
        return None
        
    u = unit.strip()
    if not u or u.upper() == "UNKNOWN":
        return None
    
    # 0-) OCR 노이즈 1차 제거: 파이프(|), 전각 파이프(｜), 눈에 띄는 테두리 기호 제거
    #     - 앞뒤 가장자리의 불필요한 구두점/장식 제거
    #     - 내부의 파이프 기호 제거(단위에는 사용되지 않음)
    u = _clean_unit_ocr_noise(u)
    
    # 특수 케이스 선(先) 처리: 장비 표기 분절로 '10 x3/µL'처럼 분리된 형태
    # - '10 x3/µL', '10x3/µL', '10 ×3/µL', '10 x3/uL' 등은 모두 10^3/µL 의미로 간주
    # - 분모가 일부 유실된 형태도 보정: '10 x3/μ', '10 x6/', '10 x3/μuL' → 각각 10^3/µL, 10^6/µL로 간주
    # 이 규칙은 값+단위 혼합 판단보다 먼저 적용해 오탐을 방지
    if re.fullmatch(r"10\s*[x×]\s*3\s*/\s*(?:µ|μ|u)(?:u?L)?\s*", u, re.IGNORECASE) or \
       re.fullmatch(r"10\s*[x×]\s*3\s*/\s*", u, re.IGNORECASE):
        u = "10^3/µL"
    elif re.fullmatch(r"10\s*[x×]\s*6\s*/\s*(?:µ|μ|u)(?:u?L)?\s*", u, re.IGNORECASE) or \
         re.fullmatch(r"10\s*[x×]\s*6\s*/\s*", u, re.IGNORECASE):
        u = "10^6/µL"

    # 값+단위 혼합 문자열 감지 (예: 'neg pos/n', '12.5 mg/dL')
    # 이런 경우 공격적 정규화 회피
    if _is_value_unit_mixed(u):
        return u  # 원문 보존

    # 0) 명시적 equals 오버라이드 (규칙으로 해결되지 않는 케이스 보완)
    eq = _apply_equals_overrides(u)
    if eq is not None:
        u = eq
    
    # 1) OCR 혼동 보정(우선 적용)
    #    - 단위 필드 전용: 유사-단위 형태 점수 및 패턴 검사를 통과한 경우에만 수행
    #    - 'mg/d1' → 'mg/dL', 'U/1' → 'U/L', 'ugD'/'ug/d1' → 'µg/dL', 'mmo1/L' → 'mmol/L' 등
    #    - liter/micro 접기 전에 숫자↔문자 혼동을 바로잡아, 후속 단계의 정규화가 안정적으로 작동하도록 함.
    u = _apply_ocr_confusion_fixes(u)

    # 2) micro 문자 통일 (µ, μ, u -> µ)
    u = fold_micro(u)

    # 3) liter 문자 통일 (l, L, ℓ -> L)
    u = fold_liter(u)

    # 3.5) equals 오버라이드(후행 1회 더 시도):
    #      fold_liter 이후 'ug/ml' -> 'ug/mL' 같은 중간 변환을 통과한 뒤 최종 보정 적용
    eq2 = _apply_equals_overrides(u)
    if eq2 is not None:
        u = eq2

    # 4) 조건화된 공백 처리 (단위 내부 공백만 제거)
    u = _normalize_unit_spaces(u)

    # 5) 접두어 및 지수형 정규화(K/M 일원화 포함)
    u = _normalize_prefixes(u)

    return u


def _clean_unit_ocr_noise(s: str) -> str:
    """단위 토큰에서 흔한 OCR 노이즈를 보수적으로 제거한다.

    규칙(보수적):
    - 전각/반각 파이프 문자 제거: '|'(U+007C), '｜'(U+FF5C)
    - 앞/뒤 가장자리의 구두점/장식 제거: , ; : · • … ~ _ - — – 등
    - 제로폭 공백류 제거
    - 내부 연속 공백은 한 칸으로 축소(최소화)

    주의: 알파벳, 숫자, '/', '%', '‰', '^', 'x', '×', 'µ', 'μ', 'L' 등 단위 관련 문자는 보존.
    """
    if not isinstance(s, str):
        return s
    t = s
    # 제로폭/비가시 공백 제거
    t = t.replace('\u200b', '').replace('\u200c', '').replace('\u200d', '')
    # 파이프류 제거
    t = t.replace('|', '').replace('｜', '')
    # 가장자리의 장식성 문자 제거
    t = re.sub(r'^[\s,;:·•…~_\-—–]+', '', t)
    t = re.sub(r'[\s,;:·•…~_\-—–]+$', '', t)
    # 내부 다중 공백 축소
    t = re.sub(r'\s+', ' ', t)
    return t.strip()


def _is_value_unit_mixed(s: str) -> bool:
    """
    값+단위 혼합 문자열인지 감지
    
    감지 패턴:
    - 'neg pos/n', 'pos neg/n' (정성값 + 단위)
    - '12.5 mg/dL' (숫자 + 공백 + 단위)
    - 공백이 있으면서 첫 토큰이 숫자이거나 정성값인 경우
    """
    if ' ' not in s:
        return False
    
    tokens = s.split()
    if len(tokens) < 2:
        return False
    
    first_token = tokens[0].lower()
    
    # 정성값 패턴
    qualitative_patterns = {'neg', 'pos', 'positive', 'negative', '양성', '음성', 'normal', 'high', 'low'}
    if first_token in qualitative_patterns:
        return True
    
    # 숫자값 패턴 (소수점, H/L/N 접미 포함)
    if re.match(r'^[-+]?\d+(?:[.,]\d+)?[HhLlNn]?$', first_token):
        return True
    
    return False


def _normalize_unit_spaces(s: str) -> str:
    """
    조건화된 공백 정규화 - 단위 내부 공백만 제거
    
    안전한 공백 제거:
    - 'K / µL' -> 'K/µL' 
    - 'mg / dL' -> 'mg/dL'
    - 'pos / n' -> 'pos/n' (보존)
    
    위험한 케이스는 제거하지 않음:
    - 'neg pos' (값 구분 공백)
    """
    # 단위 구분자 주변 공백만 제거
    s = re.sub(r'\s+/\s+', '/', s)  # ' / ' -> '/'
    s = re.sub(r'\s+\^\s*', '^', s)  # ' ^ ' -> '^'
    
    # 연속 공백을 단일 공백으로
    s = re.sub(r'\s+', ' ', s)
    
    return s.strip()


def _normalize_prefixes(unit: str) -> str:
    """
    접두어 정규화 - 주로 CBC 절대수 단위의 10^3 계열을 K로 변환
    
    변환 규칙:
    - 10^3/µL, 10³/µL, x10^3/µL, X10^3/µL -> K/µL
    - 10^6/µL, 10⁶/µL -> M/µL  
    - k/µL, K/µL -> K/µL (이미 정규화된 형태)
    """
    u = unit
    
    # 10^3/µL 계열 -> K/µL
    patterns_10_3 = [
        r'10\^3/µL',
        r'10³/µL', 
        r'x10\^3/µL',
        r'X10\^3/µL',
        r'10\^3/uL',
        r'10³/uL',
        r'x10\^3/uL', 
        r'X10\^3/uL'
    ]
    
    for pattern in patterns_10_3:
        if re.fullmatch(pattern, u, re.IGNORECASE):
            return "K/µL"
    
    # k/µL, k/uL -> K/µL  
    if re.fullmatch(r'k/µL', u, re.IGNORECASE) or re.fullmatch(r'k/uL', u, re.IGNORECASE):
        return "K/µL"
    
    # KµL, KuL, kuL -> K/µL (슬래시 없는 형태)
    if re.fullmatch(r'[Kk]µL', u) or re.fullmatch(r'[Kk]uL', u):
        return "K/µL"
    
    # 10^6/µL 계열 -> M/µL
    patterns_10_6 = [
        r'10\^6/µL',
        r'10⁶/µL',
        r'x10\^6/µL',
        r'X10\^6/µL',
        r'10\^6/uL',
        r'10⁶/uL',
        r'x10\^6/uL',
        r'X10\^6/uL'
    ]
    
    for pattern in patterns_10_6:
        if re.fullmatch(pattern, u, re.IGNORECASE):
            return "M/µL"
            
    # m/µL, m/uL -> M/µL
    if re.fullmatch(r'm/µL', u, re.IGNORECASE) or re.fullmatch(r'm/uL', u, re.IGNORECASE):
        return "M/µL"
    
    # MµL, MuL, muL -> M/µL (슬래시 없는 형태)  
    if re.fullmatch(r'[Mm]µL', u) or re.fullmatch(r'[Mm]uL', u):
        return "M/µL"
    
    # 기타 단위는 그대로 반환
    return u


def _apply_ocr_confusion_fixes(u: str) -> str:
    """OCR에서 빈번한 문자-숫자 혼동을 보정합니다.

    가드(모두 충족 또는 일부 조건 하에서만 적용):
    - 단위 필드 전용: 유사-단위 형태인지 간단 점수로 확인(_looks_like_unit)
    - 패턴·위치 제한: '/1'→'/L' 등 슬래시 뒤 위치, 전체 토큰 일치 등으로 한정
    - 렉시콘 검증: 보정 결과가 reference/unit_lexicon의 canonical로 해석(resolve) 가능해야 함
    - 최소 변경: 렉시콘 검증에 실패하면 원문 유지(가능한 가장 작은 변형만 허용)
    """
    if not u:
        return u

    s = u

    # 단위-유사 형태 점수로 1차 거르기: 너무 일반 텍스트면 보정 스킵
    if _looks_like_unit(s) < 1:
        return s

    def _resolve_canonical(token: str) -> Optional[str]:
        try:
            # 지연 임포트로 순환 의존 회피
            from .reference.unit_lexicon import resolve_unit, get_unit_lexicon  # type: ignore
            return resolve_unit(token, get_unit_lexicon())
        except Exception:
            return None

    def _apply_if_valid(before: str, after: str) -> Optional[str]:
        """보정 후보(after)가 렉시콘에서 해석 가능하면 after, 아니면 None 반환."""
        if before == after:
            return before
        resolved = _resolve_canonical(after)
        if resolved:
            return after
        return None

    # 1) 전체 토큰 일치 기반 보정 (최소 변경, 강한 가드)
    up = s.upper()
    # ugD, µgD, μgD → µg/dL (전체 토큰 일치만 허용)
    if up in {"UGD", "µGD", "ΜGD"}:  # 마지막은 그리스 문자 μ 대문자 취급 방어
        cand = _apply_if_valid(s, "µg/dL")
        if cand:
            return cand

    # ug/d1, ug/dl → µg/dL (전체 토큰 또는 분수 형태만)
    if re.fullmatch(r"(?i)ug/d[1l]", s):
        cand = _apply_if_valid(s, "µg/dL")
        if cand:
            return cand

    # ug/dL → µg/dL (fold_micro에서 놓친 경우 보정)
    if re.fullmatch(r"(?i)ug/dl", s):
        cand = _apply_if_valid(s, "µg/dL")
        if cand:
            return cand

    # 2) 위치 제한 보정: 분모의 '1'만 'L'로 교체
    # mg/d1 → mg/dL, g/d1 → g/dL (단, 단위 전체가 해당 형태일 때만)
    m = re.fullmatch(r"(?i)(mg|g)/d1", s)
    if m:
        base = m.group(1)
        cand = _apply_if_valid(s, f"{base}/dL")
        if cand:
            return cand

    # U/1, IU/1 → U/L, IU/L (전체 토큰 일치만)
    m = re.fullmatch(r"(?i)(iu|u)/1", s)
    if m:
        base = m.group(1).upper()
        cand = _apply_if_valid(s, f"{base}/L")
        if cand:
            return cand

    # mmo1/L → mmol/L (전체 토큰 일치만)
    if re.fullmatch(r"(?i)mmo1/l", s):
        cand = _apply_if_valid(s, "mmol/L")
        if cand:
            return cand

    # 위 보정들에 해당하지 않으면 원문 유지
    return s

def _apply_equals_overrides(u: str) -> Optional[str]:
    """규칙으로 처리되지 않는 특정 토큰을 문자열 일치로 보정합니다.

    요구사항 매핑(정확 일치):
    - 'mg/d'   -> 'mg/dL'
    - 'MG/'    -> 'mg/dL'
    - 'umol'   -> 'µmol/L'
    - 'mmol'   -> 'mmol/L'
    - 'ug/mL'  -> 'µg/mL'

    대소문자/공백은 그대로 비교(보수적).
    """
    if not isinstance(u, str):
        return None
    mapping = {
        "mg/d": "mg/dL",
        "MG/": "mg/dL",
        "umol": "µmol/L",
        "umol/": "µmol/L",
        "mmol": "mmol/L",
        "ug/mL": "µg/mL",
        "ug/ml": "µg/mL",
        # mg' d 류 오타 보정 → mg/d (이후 규칙으로 mg/dL 처리)
        "mg'd": "mg/d",
        "MG'D": "mg/d",
        # mmH → mmHg (g 유실 보정)
        "mmH": "mmHg",
        "MMH": "mmHg",
        # OCR g↔9 혼동 보정: Pg/pG/P9/p9 → pg
        "P9": "pg",
        "p9": "pg",
        "ug/D": "µg/dL",
        "UG/D": "µg/dL",
        "ug/d": "µg/dL",
        "UG/d": "µg/dL",
        "G/DL": "g/dL",
        "mEq/": "mEq/L",
        "MEQ/": "mEq/L",
        "meq/": "mEq/L",
        "mEq": "mEq/L",
        "Pg": "pg",
        "PG": "pg",
        "pG": "pg",
        "Pg/mL": "pg/mL",
        "PG/mL": "pg/mL",
        "pG/mL": "pg/mL",
        "Pg/L": "pg/L",
        "PG/L": "pg/L",
        "pG/L": "pg/L",
    }
    return mapping.get(u)

def _looks_like_unit(s: str) -> int:
    """문자열이 '단위'로 보이는지 간단 점수로 판단.

    반환 점수(0~2):
    - +1: 분수 구분자('/', 'per') 포함 또는 지수('10^', '10³', 'x10') 포함
    - +1: 알파벳+L(리터), micro(µ/μ/u) 또는 g/mg/ug 등 질량 접두 흔적 포함
    - 0: 그 외
    """
    if not isinstance(s, str) or not s.strip():
        return 0
    score = 0
    t = s.strip()
    if "/" in t or re.search(r"(?i)(per|x10|10\^)", t):
        score += 1
    if re.search(r"(?i)(mg|ug|g|mol|mmol|iu|u/l|µ|μ|L|/l)", t):
        score += 1
    return score


def test_normalize_unit_simple():
    """테스트 함수"""
    test_cases = [
        # 기본 접두어 정규화
        ("10^3/µL", "K/µL"),
        ("10³/µL", "K/µL"),
        ("x10^3/µL", "K/µL"),
        ("X10^3/uL", "K/µL"),
        ("k/ul", "K/µL"),
        ("K / UL", "K/µL"),  # 공백 있는 단위
        ("mg/dL", "mg/dL"),
        ("g/L", "g/L"),
        ("%", "%"),
        ("U/L", "U/L"),
        ("10^6/µL", "M/µL"),
            
        # 명시적 equals 오버라이드
        ("mg/d", "mg/dL"),
        ("MG/", "mg/dL"),
        ("umol", "µmol/L"),
        ("mmol", "mmol/L"),
        ("ug/mL", "µg/mL"),
        ("ug/ml", "µg/mL"),
        ("mEq/", "mEq/L"),
        ("MEQ/", "mEq/L"),
        ("meq/", "mEq/L"),
        ("mEq", "mEq/L"),
        ("|mg/d ", "mg/dL"),
    ("umol/", "µmol/L"),
    ("mg'd", "mg/dL"),  # ' → / 보정 후 mg/d → mg/dL 규칙 적용
    ("mmH", "mmHg"),
    ("P9", "pg"),
    ("p9", "pg"),
    ("10 x3/μ", "K/µL"),
    ("10 x3/μuL", "K/µL"),
    ("10 x6/", "M/µL"),
        ("ug/D", "µg/dL"),
        ("UG/D", "µg/dL"),
        ("ug/d", "µg/dL"),

        # Pg → pg 계열 (요청 사항)
        ("Pg", "pg"),
        ("PG", "pg"),
        ("pG", "pg"),
        ("Pg/mL", "pg/mL"),
        ("PG/mL", "pg/mL"),
        ("Pg/L", "pg/L"),

        # OCR 혼동 보정
        ("ugD", "µg/dL"),
        ("ug/d1", "µg/dL"),
        ("ug/dL", "µg/dL"),
        ("mg/d1", "mg/dL"),
        ("U/1", "U/L"),
        # IU/1 은 렉시콘에 IU/L 이 없으면 보정하지 않음(가드)
        # 기대값을 동적으로 설정해 검증 환경 의존성을 제거
        ("IU/1", (lambda: (lambda _r: ("IU/L" if _r else "IU/1"))(
            __import__('importlib').import_module('app.services.analysis.reference.unit_lexicon').resolve_unit('IU/L',
                __import__('importlib').import_module('app.services.analysis.reference.unit_lexicon').get_unit_lexicon())
        ))()),
        ("mmo1/L", "mmol/L"),
        
        # 값+단위 혼합 케이스 (보존되어야 함)
        ("neg pos/n", "neg pos/n"),  # ✓ 보존
        ("pos neg/n", "pos neg/n"),  # ✓ 보존  
        ("12.5 mg/dL", "12.5 mg/dL"),  # ✓ 보존
        ("7.2H K/µL", "7.2H K/µL"),  # ✓ 보존
        
        # 순수 단위 (정규화됨)
        ("pos/n", "pos/n"),
        ("mg / dL", "mg/dL"),  # 단위 내부 공백 제거
        
        # 엣지 케이스
        ("", None),
        ("UNKNOWN", None),
        (None, None)
    ]
    
    print("=== Enhanced Unit Normalizer Test ===")
    for input_unit, expected in test_cases:
        # 동적 기대값 람다 처리
        exp = expected() if callable(expected) else expected
        result = normalize_unit_simple(input_unit)
        status = "✓" if result == exp else "✗"
        print(f"{status} '{input_unit}' -> '{result}' (expected: '{exp}')")


__all__ = [
    "fold_micro",
    "fold_liter", 
    "normalize_unit_simple",
]


if __name__ == "__main__":
    test_normalize_unit_simple()