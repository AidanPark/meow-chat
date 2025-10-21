# Unit 정규화 'neg pos/n' 문제 해결 완료 보고서

## 🔍 **문제 상황**
- **원본**: `'neg pos/n'` (OCR 결과)
- **이전**: `'negpos/n'` (공백 제거로 의미 왜곡)
- **문제**: 값(`neg`)과 단위(`pos/n`)가 잘못 병합됨

## 🚨 **근본 원인**
1. **무분별한 공백 제거**: `re.sub(r'\s+', '', u)` 
2. **값+단위 구분 실패**: 전체 문자열에 단위 정규화 적용
3. **처리 순서 오류**: 토큰 분리 전에 정규화 수행

## 🛠️ **해결 방법**

### 1. 값+단위 혼합 감지 추가
```python
def _is_value_unit_mixed(s: str) -> bool:
    """값+단위 혼합 문자열 감지"""
    if ' ' not in s:
        return False
    
    tokens = s.split()
    first_token = tokens[0].lower()
    
    # 정성값 패턴
    qualitative_patterns = {'neg', 'pos', 'positive', 'negative', '양성', '음성'}
    if first_token in qualitative_patterns:
        return True
    
    # 숫자값 패턴
    if re.match(r'^[-+]?\d+(?:[.,]\d+)?[HhLlNn]?$', first_token):
        return True
    
    return False
```

### 2. 조건화된 공백 처리
```python 
def _normalize_unit_spaces(s: str) -> str:
    """안전한 공백 정규화"""
    # 단위 구분자 주변 공백만 제거
    s = re.sub(r'\s+/\s+', '/', s)  # 'K / µL' -> 'K/µL'
    s = re.sub(r'\s+\^\s*', '^', s)  # '10 ^ 3' -> '10^3'
    s = re.sub(r'\s+', ' ', s)  # 연속 공백 정리
    return s.strip()
```

### 3. 보수적 정규화 로직
```python
def normalize_unit_simple(unit: str) -> Optional[str]:
    # 값+단위 혼합 감지 시 원문 보존
    if _is_value_unit_mixed(u):
        return u  # 🔥 핵심: 원문 그대로 반환
    
    # 순수 단위만 정규화 수행
    u = _fold_micro(u)
    u = _fold_liter(u) 
    u = _normalize_unit_spaces(u)  # 조건화된 공백 처리
    u = _normalize_prefixes(u)
    return u
```

## ✅ **테스트 결과**

### 문제 해결 검증
```
✅ 'neg pos/n' -> 'neg pos/n' (의미 보존)
✅ 'pos neg/n' -> 'pos neg/n' (의미 보존)  
✅ '12.5 mg/dL' -> '12.5 mg/dL' (값+단위 혼합 보존)
```

### 기존 기능 유지
```
✅ '10^3/µL' -> 'K/µL' (접두어 정규화)
✅ 'k/ul' -> 'K/µL' (표준화)
✅ 'mg / dL' -> 'mg/dL' (단위 내부 공백 제거)
```

## 🎯 **핵심 개선점**

### 1. **의미 보존 우선**
- 애매한 경우 공격적 정규화보다 원문 보존
- 값과 단위가 혼재된 경우 안전 회피

### 2. **조건화된 처리**
- 순수 단위: 정규화 수행
- 혼합 문자열: 원문 보존
- 단위 내부 공백: 제거
- 의미 구분 공백: 보존

### 3. **견고성 향상**  
- OCR 오인식에 대한 견고성
- 다양한 표기법 대응
- 예외 케이스 안전 처리

## 📊 **Before vs After**

| 케이스 | 이전 결과 | 현재 결과 | 상태 |
|--------|----------|----------|------|
| `'neg pos/n'` | `'negpos/n'` ❌ | `'neg pos/n'` ✅ | **해결** |
| `'10^3/µL'` | `'K/µL'` ✅ | `'K/µL'` ✅ | **유지** |
| `'mg / dL'` | `'mg/dL'` ✅ | `'mg/dL'` ✅ | **유지** |
| `'12.5 mg/dL'` | `'12.5mg/dL'` ⚠️ | `'12.5 mg/dL'` ✅ | **개선** |

## 🔮 **향후 고려사항**

1. **토큰 분리 우선 처리**: OCR → 토큰 분리 → 단위만 정규화
2. **문맥 기반 검증**: 검사 코드별 허용 단위 매칭
3. **패턴 확장**: 추가적인 정성값 패턴 지원

## ✨ **결론**
**'neg pos/n' → 'negpos/n' 문제 완전 해결!**
- 의미 왜곡 방지
- 기존 정규화 기능 유지  
- 더 안전하고 견고한 처리