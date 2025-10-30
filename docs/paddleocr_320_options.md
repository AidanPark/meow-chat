# PaddleOCR 3.2.0 옵션 가이드

## 개요

PaddleOCR 3.2.0에서는 기존의 `use_doc_preprocessor` 옵션이 제거되고, 각 전처리 기능별로 세분화된 옵션들로 변경되었습니다.

## 전처리 관련 옵션

### 1. 문서 방향 분류 (Document Orientation Classification)

```python
use_doc_orientation_classify: bool = None           # 문서 방향 분류 활성화/비활성화
doc_orientation_classify_model_name: str = None     # 사용자 정의 모델명
doc_orientation_classify_model_dir: str = None      # 사용자 정의 모델 경로
```

**기능:**
- 전체 문서/페이지의 방향을 감지 (0°/90°/180°/270°)
- 회전된 문서를 올바른 방향으로 자동 보정
- 스캔된 문서나 사진에서 유용

**사용 예시:**
```python
# 활성화 (권장 - 문서 처리)
use_doc_orientation_classify=True

# 비활성화 (고속 처리)
use_doc_orientation_classify=False
```

### 2. 문서 언워핑 (Document Unwarping)

```python
use_doc_unwarping: bool = None                      # 문서 언워핑 활성화/비활성화
doc_unwarping_model_name: str = None                # 사용자 정의 모델명 (예: UVDoc)
doc_unwarping_model_dir: str = None                 # 사용자 정의 모델 경로
```

**기능:**
- 휘어진/구겨진 종이를 평면으로 보정
- 원근 왜곡 보정
- 카메라로 촬영한 문서에서 유용

**사용 예시:**
```python
# 활성화 (카메라 촬영 문서)
use_doc_unwarping=True

# 비활성화 (스캔 문서 또는 고속 처리)
use_doc_unwarping=False
```

### 3. 텍스트라인 방향 분류 (Textline Orientation)

```python
use_textline_orientation: bool = None               # 텍스트라인 방향 분류 활성화/비활성화
textline_orientation_model_name: str = None         # 사용자 정의 모델명
textline_orientation_model_dir: str = None          # 사용자 정의 모델 경로
textline_orientation_batch_size: int = None         # 배치 크기 (기본: 6)
```

**기능:**
- 개별 텍스트라인의 0°/180° 회전을 감지하고 보정
- 일부 텍스트만 뒤집힌 경우에 유용
- 문서 방향 분류와는 별개로 동작

**사용 예시:**
```python
# 활성화 (일반적으로 권장)
use_textline_orientation=True

# 비활성화 (고속 처리)
use_textline_orientation=False
```

## 텍스트 감지 옵션

### 모델 관련

```python
text_detection_model_name: str = None               # 사용자 정의 감지 모델명
text_detection_model_dir: str = None                # 사용자 정의 감지 모델 경로
```

### 이미지 전처리

```python
text_det_limit_side_len: int = None                 # 이미지 최대 변 길이 제한 (기본: 960)
text_det_limit_type: str = None                     # 크기 제한 방식 (기본: 'max')
text_det_input_shape: tuple = None                  # 감지 모델 입력 크기
```

**설명:**
- `text_det_limit_side_len`: 이미지의 긴 변을 지정된 픽셀로 제한
- `text_det_limit_type`: 
  - `'max'`: 긴 변 기준으로 제한 (기본값)
  - `'min'`: 짧은 변 기준으로 제한
  - `'none'`: 크기 제한 없음

### 감지 임계값

```python
text_det_thresh: float = None                       # 텍스트 감지 임계값 (기본: 0.3)
text_det_box_thresh: float = None                   # 박스 필터링 임계값 (기본: 0.6)
text_det_unclip_ratio: float = None                 # 박스 확장 비율 (기본: 1.5)
```

**설정 가이드:**

| 설정 목적 | det_thresh | box_thresh | unclip_ratio |
|----------|------------|------------|--------------|
| 고민감도 (작은 글씨) | 0.1-0.2 | 0.4-0.5 | 1.8-2.0 |
| 균형 (권장) | 0.3 | 0.6 | 1.5 |
| 고정확도 (노이즈 제거) | 0.4-0.5 | 0.7-0.8 | 1.2-1.3 |

## 텍스트 인식 옵션

### 모델 관련

```python
text_recognition_model_name: str = None             # 사용자 정의 인식 모델명
text_recognition_model_dir: str = None              # 사용자 정의 인식 모델 경로
text_recognition_batch_size: int = None             # 텍스트 인식 배치 크기 (기본: 6)
```

### 인식 설정

```python
text_rec_score_thresh: float = None                 # 인식 신뢰도 임계값 (기본: 0.5)
text_rec_input_shape: tuple = None                  # 인식 모델 입력 크기
return_word_box: bool = None                        # 단어별 박스 반환 여부 (기본: False)
```

**설정 가이드:**

| 용도 | rec_score_thresh | batch_size | return_word_box |
|------|------------------|------------|-----------------|
| 고속 처리 | 0.3-0.4 | 8-12 | False |
| 균형 | 0.5 | 6 | False |
| 고정확도 | 0.7-0.8 | 4 | True |

## 기타 옵션

```python
lang: str = None                                    # 인식 언어 (예: 'korean', 'en', 'ch')
ocr_version: str = None                             # OCR 버전 ('PP-OCRv3', 'PP-OCRv4')
```

## 용도별 권장 설정

### 1. 고속 처리용 (실시간, 배치 처리)

```python
fast_ocr = PaddleOCR(
    lang='korean',
    use_doc_orientation_classify=False,      # 문서 방향 분류 비활성화
    use_doc_unwarping=False,                 # 문서 언워핑 비활성화
    use_textline_orientation=False,          # 텍스트라인 방향 분류 비활성화
    text_det_thresh=0.4,                     # 감지 임계값 높임 (빠르게)
    text_rec_score_thresh=0.4,               # 인식 임계값 낮춤 (빠르게)
    text_recognition_batch_size=8,           # 배치 크기 증가
    text_det_limit_side_len=640,             # 이미지 크기 제한 (빠르게)
    return_word_box=False                    # 라인별 박스만
)
```

### 2. 고정확도용 (품질 우선)

```python
accurate_ocr = PaddleOCR(
    lang='korean',
    use_doc_orientation_classify=True,       # 문서 방향 분류 활성화
    use_doc_unwarping=True,                  # 문서 언워핑 활성화
    use_textline_orientation=True,           # 텍스트라인 방향 분류 활성화
    text_det_thresh=0.2,                     # 감지 임계값 낮춤 (정확하게)
    text_rec_score_thresh=0.7,               # 인식 임계값 높임 (정확하게)
    text_recognition_batch_size=4,           # 배치 크기 감소
    text_det_limit_side_len=1280,            # 이미지 크기 여유롭게
    text_det_unclip_ratio=1.8,               # 박스 확장 여유롭게
    return_word_box=True                     # 단어별 박스도 반환
)
```

### 3. 문서 전용 (스캔/사진 문서)

```python
document_ocr = PaddleOCR(
    lang='korean',
    use_doc_orientation_classify=True,       # 문서 방향 분류 (필수)
    use_doc_unwarping=True,                  # 문서 언워핑 (카메라 촬영시 필수)
    use_textline_orientation=True,           # 텍스트라인 방향 분류
    text_det_thresh=0.3,                     # 균형잡힌 설정
    text_rec_score_thresh=0.6,               # 적당한 필터링
    text_recognition_batch_size=6,           # 기본 배치 크기
    text_det_limit_side_len=960,             # 표준 크기
    return_word_box=False                    # 라인별 처리 (문서에 적합)
)
```

### 4. 균형잡힌 설정 (일반 용도)

```python
balanced_ocr = PaddleOCR(
    lang='korean',
    use_doc_orientation_classify=True,       # 문서 방향 분류
    use_doc_unwarping=False,                 # 문서 언워핑 (필요시에만)
    use_textline_orientation=True,           # 텍스트라인 방향 분류
    text_det_thresh=0.3,                     # 기본 감지 임계값
    text_rec_score_thresh=0.5,               # 기본 인식 임계값
    text_recognition_batch_size=6,           # 기본 배치 크기
    text_det_limit_side_len=960,             # 기본 크기 제한
    return_word_box=False                    # 라인별 박스
)
```

## 전처리 파이프라인 순서

PaddleOCR 3.2.0의 전처리는 다음 순서로 실행됩니다:

```
1. 이미지 로드 및 기본 전처리
   ↓
2. 문서 방향 분류 (use_doc_orientation_classify)
   → 전체 이미지 회전 보정 (0°/90°/180°/270°)
   ↓
3. 문서 언워핑 (use_doc_unwarping)
   → 휘어진 문서 평면 보정
   ↓
4. 텍스트 감지 (Text Detection)
   → 텍스트 영역 찾기
   ↓
5. 텍스트라인 방향 분류 (use_textline_orientation)
   → 개별 라인 방향 보정 (0°/180°)
   ↓
6. 텍스트 인식 (Text Recognition)
   → 실제 글자 읽기
   ↓
7. 후처리 및 결과 반환
```

## 성능 vs 정확도 트레이드오프

| 기능 | 처리 시간 영향 | 정확도 향상 | 권장 사용 케이스 |
|------|---------------|-------------|------------------|
| `use_doc_orientation_classify` | 높음 | 높음 | 스캔 문서, 회전된 이미지 |
| `use_doc_unwarping` | 중간 | 중간 | 카메라 촬영 문서 |
| `use_textline_orientation` | 낮음 | 중간 | 일반적인 모든 경우 |
| `text_det_thresh` 낮춤 | 중간 | 높음 (작은 글씨) | 정밀한 텍스트 감지 |
| `text_rec_score_thresh` 높임 | 낮음 | 높음 | 고품질 결과 필요시 |
| `batch_size` 증가 | 감소 | 동일 | 대량 처리시 |

## 주의사항

1. **호환성**: PaddleOCR 3.2.0에서는 `use_doc_preprocessor` 옵션이 제거되었습니다.
2. **메모리**: 모든 전처리 기능을 활성화하면 메모리 사용량이 증가합니다.
3. **GPU**: GPU 사용시 배치 크기를 조정하여 성능을 최적화할 수 있습니다.
4. **언어**: 한국어의 경우 `lang='korean'` 또는 `lang='ko'`를 사용합니다.

## 디버깅 팁

```python
# 현재 설정 확인
from paddleocr import PaddleOCR
import inspect

ocr = PaddleOCR(lang='korean')
signature = inspect.signature(PaddleOCR.__init__)
print("지원하는 파라미터:")
for param_name, param in signature.parameters.items():
    if param_name != 'self':
        default = param.default if param.default != inspect.Parameter.empty else "필수"
        print(f"   {param_name}: {default}")
```

이 문서를 참고하여 용도에 맞는 PaddleOCR 3.2.0 설정을 선택하시기 바랍니다.