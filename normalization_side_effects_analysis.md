# 정규화 변경 부작용 분석 보고서

## 변경 사항 요약
1. **LinePreprocessor**: `normalize_units_first_pass=False` (1차 정규화 비활성화)
2. **LabTableExtractor**: `unit_lexicon` → `simple_unit_normalizer` (단일 정규화 포인트)
3. **결과**: 파편화 해결 + 단순화

## 상세 부작용 분석

### ✅ **1. Step 11 정규화 (안전함)**

**테스트 결과:**
```
WBC: '10^3/µL' -> 'K/µL'  ✓
RBC: '10³/uL' -> 'K/µL'   ✓
HGB: 'g/dL' -> 'g/dL'     ✓
PLT: 'k/ul' -> 'K/µL'     ✓
```

**분석:**
- `unit_canonical` 필드 정상 생성 (100% 커버리지)
- `result_norm` 필드 정상 생성 (UNKNOWN 제외 100%)
- 기존 `unit_lexicon` vs 새로운 `simple_unit_normalizer` 핵심 기능 동일

### ✅ **2. Step 12 필터링 (안전함)**

**코드 분석:**
```python
unit_canon = row.get("unit_canonical") if isinstance(row.get("unit_canonical"), str) else None
unit_final = unit_canon or unit_raw  # unit_canonical 우선 사용
```

**분석:**  
- `unit_final` 계산에서 `unit_canonical` 우선 사용
- 정규화된 단위로 최종 JSON 생성
- 단위 호환성 검증 정상 작동
- confidence 계산에서 단위 존재 여부 체크 정상

### ✅ **3. QA Summary (안전함)**

**테스트 결과:**
```
unit_canonical_coverage: 5/5 (100.0%)
result_norm_coverage: 4/5 (80.0%) 
```

**분석:**
- 정규화 커버리지 통계 정상 계산
- Step 12 필터링 통계 정상 생성
- 성능 지표 수집 정상

### ⚠️ **4. LinePreprocessor 중간 단계 (주의 필요)**

**변경 전후 비교:**
```
Before: normalize_units_first_pass=True
- '10^3/µL' -> 'K/µL' (1차 정규화)
- 중간 단계에서도 정규화된 형태

After: normalize_units_first_pass=False  
- '10^3/µL' -> '10^3/µL' (원문 유지)
- '10³/uL' -> '10³/uL' (원문 유지)
```

**잠재적 영향:**
- **중간 디버깅**: Step 6~10에서 다양한 단위 표기 혼재
- **열 매칭**: 원문 기반 매칭이므로 영향 없음
- **코드 해석**: 단위와 무관하므로 영향 없음

### ✅ **5. 최종 출력 (안전함)**

**Final JSON 테스트:**
```python
{"code": "WBC", "unit": "K/µL", "value": 12.5}  # unit_canonical 사용됨
{"code": "RBC", "unit": "K/µL", "value": 7.2}   # unit_canonical 사용됨
{"code": "HGB", "unit": "g/dL", "value": 14.2}  # 정규화 불필요한 경우
```

**분석:**
- 최종 사용자가 보는 결과는 동일
- API 응답 스키마 변경 없음
- 정규화 품질 유지

## 위험도 평가

### 🟢 **LOW 위험 (문제없음)**
- Step 11, 12 정규화 로직
- Final JSON 출력
- QA 통계 수집
- API 호환성

### 🟡 **MEDIUM 위험 (관찰 필요)**  
- 중간 단계 디버그 출력 혼란 가능성
- Step 6~10 중간 산출물에서 unit 표기 다양성 증가

### 🔴 **HIGH 위험 (없음)**

## 대응 방안

### 1. **모니터링 강화**
```python
# QA summary에서 정규화 커버리지 모니터링
unit_canonical_coverage = (unit_canon_cnt, n_rows)
if unit_canon_cnt / n_rows < 0.8:  # 80% 미만시 경고
    logger.warning(f"Low unit normalization coverage: {unit_canon_cnt}/{n_rows}")
```

### 2. **디버그 출력 개선**
- Step 6~10 디버그에서 "정규화 예정" 표시 추가
- 중간 단계에서 다양한 unit 표기 설명

### 3. **테스트 케이스 추가**
- 다양한 unit 변형에 대한 종단간 테스트
- 정규화 전후 결과 일관성 검증

## 결론

### ✅ **안전한 변경**
- 핵심 기능 영향 없음
- 최종 출력 품질 유지
- 성능 개선 (무거운 사전 로딩 제거)

### ⚠️ **제한적 주의사항**
- 중간 단계 디버그 출력에서 unit 표기 혼재
- 정규화 커버리지 모니터링 필요

### 🎯 **권장사항**
1. **즉시 배포 가능**: 핵심 기능 영향 없음
2. **모니터링 추가**: 정규화 품질 지속 확인  
3. **문서 업데이트**: 단일 정규화 포인트 설명

**전체 위험도: 🟢 LOW (안전)**