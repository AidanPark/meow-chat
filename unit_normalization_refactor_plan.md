"""
통합 Unit 정규화 전략 및 리팩토링 계획
===========================================

## 문제 상황
현재 unit 정규화 기능이 여러 곳에 파편화되어 있음:

1. LinePreprocessor: normalize_units_first_pass + unit_lexicon.py
2. LabTableExtractor: _normalize_unit_and_result + simple_unit_normalizer.py  
3. 두 가지 정규화 모듈이 동시 존재하여 혼란

## 제안하는 통합 전략

### Option 1: 단일 정규화 포인트 (권장)
- LabTableExtractor에서만 정규화 수행
- LinePreprocessor의 normalize_units_first_pass=False로 설정
- 장점: 단일 책임, 디버깅 용이
- 단점: 늦은 정규화로 중간 단계 혼란 가능

### Option 2: 2단계 정규화 (현재 유지 + 개선)
- 1단계: LinePreprocessor에서 기본 정규화
- 2단계: LabTableExtractor에서 최종 정규화
- 동일한 정규화 로직 사용하여 일관성 확보

### Option 3: 하이브리드 정규화기
- 간단한 정규화 + 선택적 사전 검증
- 빠른 처리 + 품질 보장 균형

## 권장 구현: Option 1 (단일 포인트)

### 1단계: 설정 통일
```python
# line_preprocessor.py 설정 변경
class LinePreprocessorSettings:
    normalize_units_first_pass: bool = False  # 비활성화
```

### 2단계: 정규화 모듈 선택
- simple_unit_normalizer.py 사용 (가볍고 빠름)
- 필요시 unit_lexicon.py 로직 일부 흡수

### 3단계: LabTableExtractor 정규화 강화
- 현재 _normalize_unit_and_result 개선
- 에러 핸들링 강화
- 로깅 추가

## 구현 단계별 계획

### Step 1: 현재 상태 정리
- [ ] LinePreprocessor normalize_units_first_pass 비활성화
- [ ] unit_lexicon import 정리
- [ ] simple_unit_normalizer 위치 최적화

### Step 2: 단일 정규화 로직 구현  
- [ ] enhanced_unit_normalizer.py 생성
- [ ] 기존 로직들 통합
- [ ] 테스트 케이스 작성

### Step 3: 기존 코드 마이그레이션
- [ ] LabTableExtractor 업데이트
- [ ] LinePreprocessor 정리
- [ ] 테스트 및 검증

### Step 4: 정리 작업
- [ ] 사용하지 않는 모듈 제거
- [ ] 문서 업데이트
- [ ] 성능 검증
"""