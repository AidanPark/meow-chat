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
    """liter 표기를 대문자 L로 통일"""
    out = s
    # l, ℓ -> L
    out = out.replace("l", "L").replace("ℓ", "L")
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
    
    # 값+단위 혼합 문자열 감지 (예: 'neg pos/n', '12.5 mg/dL')
    # 이런 경우 공격적 정규화 회피
    if _is_value_unit_mixed(u):
        return u  # 원문 보존
    
    # 1. micro 문자 통일 (µ, μ, u -> µ)
    u = fold_micro(u)
    
    # 2. liter 문자 통일 (l, L, ℓ -> L)
    u = fold_liter(u)
    
    # 3. 조건화된 공백 처리 (단위 내부 공백만 제거)
    u = _normalize_unit_spaces(u)
    
    # 4. 접두어 정규화
    u = _normalize_prefixes(u)
    
    return u


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
        result = normalize_unit_simple(input_unit)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{input_unit}' -> '{result}' (expected: '{expected}')")


__all__ = [
    "fold_micro",
    "fold_liter", 
    "normalize_unit_simple",
]


if __name__ == "__main__":
    test_normalize_unit_simple()