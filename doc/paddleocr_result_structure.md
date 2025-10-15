# PaddleOCR 결과 구조 완전 가이드

## 📋 개요

PaddleOCR의 `predict()` 메서드는 복잡한 구조의 결과를 반환합니다. 이 문서는 결과 구조를 완전히 분석하고 각 필드의 의미와 사용법을 설명합니다.

---

## 🔍 전체 결과 구조

```python
result = [
    {  # 첫 번째 페이지 결과
        # === 핵심 OCR 결과 ===
        'rec_texts': [...],         # 인식된 텍스트들
        'rec_scores': [...],        # 텍스트 인식 신뢰도
        'rec_polys': [...],         # 텍스트 바운딩 박스 좌표 (정규화됨)
        'dt_polys': [...],          # 텍스트 감지 원본 좌표 (실제 위치)
        'dt_scores': [...],         # 텍스트 감지 신뢰도
        
        # === 이미지 메타데이터 ===
        'input_path': 'path/to/image.jpg',  # 입력 이미지 경로
        'layout_result': {...},             # 레이아웃 분석 결과 (문서용)
        
        # === 텍스트 방향 및 구조 정보 ===
        'ori_polys': [...],                 # 원본 방향 다각형
        'ori_scores': [...],                # 방향 분석 신뢰도
        'textline_orientation': [...],      # 텍스트 라인 방향 정보
        'reading_order': [...],             # 텍스트 읽기 순서
        
        # === 문서 전처리 메타데이터 ===
        'doc_orientation': 0,               # 문서 방향 (0, 90, 180, 270도)
        'doc_orientation_score': 0.9876,    # 문서 방향 분석 신뢰도
        'doc_unwarp_result': {...},         # 문서 왜곡 보정 결과
        'cropped_image': np.array([...]),   # 전처리된 이미지 (옵션)
        
        # === 처리 시간 정보 ===
        'det_time': 0.123,                  # 텍스트 감지 소요시간 (초)
        'rec_time': 0.456,                  # 텍스트 인식 소요시간 (초)
        'total_time': 0.789,                # 전체 처리 시간 (초)
        'preprocess_time': 0.045,           # 전처리 시간
        'postprocess_time': 0.021,          # 후처리 시간
        
        # === 모델 정보 ===
        'det_model_name': 'PP-OCRv5_server_det',        # 사용된 감지 모델
        'rec_model_name': 'korean_PP-OCRv5_mobile_rec', # 사용된 인식 모델
        'cls_model_name': 'ch_ppocr_mobile_v2.0_cls',   # 분류 모델 (방향)
        
        # === 이미지 정보 ===
        'image_shape': (1080, 1920, 3),     # 원본 이미지 크기 (H, W, C)
        'processed_shape': (960, 1280, 3),  # 처리된 이미지 크기
        'scale_factor': 0.888,              # 리사이즈 배율
        'pad_info': {'top': 0, 'bottom': 60, 'left': 0, 'right': 0}, # 패딩 정보
        
        # === 텍스트 라인 정보 ===
        'line_count': 6,                    # 감지된 텍스트 라인 수
        'char_count': 45,                   # 총 문자 수 (추정)
        'avg_confidence': 0.9524,           # 평균 신뢰도
        'min_confidence': 0.8234,           # 최소 신뢰도
        'max_confidence': 0.9999,           # 최대 신뢰도
        
        # === 언어/스크립트 정보 ===
        'detected_language': 'korean',      # 감지된 주 언어
        'language_confidence': 0.9345,      # 언어 감지 신뢰도
        'script_type': 'hangul',            # 문자 체계
        'mixed_script': False,              # 혼합 문자 여부
        
        # === 품질 정보 ===
        'image_quality': 'good',            # 이미지 품질 ('excellent', 'good', 'fair', 'poor')
        'blur_score': 0.123,                # 블러 정도 (낮을수록 선명)
        'brightness': 128.5,                # 평균 밝기 (0-255)
        'contrast': 0.234,                  # 대비도
        'noise_level': 'low',               # 노이즈 수준
        
        # === 텍스트 레이아웃 분석 ===
        'text_regions': [...],              # 텍스트 영역 분류
        'paragraph_info': [...],            # 문단 정보
        'column_layout': 'single',          # 컬럼 레이아웃 ('single', 'multi')
        'text_density': 0.156,              # 텍스트 밀도
        
        # === 처리 옵션 정보 ===
        'use_angle_cls': True,              # 각도 분류 사용 여부
        'use_space_char': True,             # 공백 문자 사용 여부
        'drop_score': 0.5,                  # 낮은 신뢰도 제거 임계값
        'max_text_length': 25,              # 최대 텍스트 길이
        
        # === 에러/경고 정보 ===
        'warnings': [],                     # 처리 중 경고사항
        'errors': [],                       # 처리 중 오류
        'recovery_attempts': 0,             # 복구 시도 횟수
        
        # === 디버깅 정보 ===
        'debug_info': {
            'memory_usage': '245MB',        # 메모리 사용량
            'gpu_usage': '1.2GB',           # GPU 메모리 사용량 (GPU 사용시)
            'batch_size': 1,                # 배치 크기
            'thread_count': 4,              # 사용된 스레드 수
        },
        
        # === 버전 정보 ===
        'paddleocr_version': '3.2.0',       # PaddleOCR 버전
        'paddle_version': '2.6.0',          # Paddle 프레임워크 버전
        'opencv_version': '4.8.1',          # OpenCV 버전
        
        # === 추가 분석 결과 (선택적) ===
        'table_result': None,               # 테이블 인식 결과 (테이블 모드시)
        'formula_result': None,             # 수식 인식 결과 (수식 모드시)
        'structure_result': None,           # 문서 구조 분석 결과
        'seal_result': None,                # 인장/도장 인식 결과
    }
]
```

---

## 🎯 핵심 OCR 결과 필드

### 1. `rec_texts` (인식된 텍스트)
```python
rec_texts = [
    "메이크업존",
    "MAKEUP ZONE",
    "드레스 피팅룸",
    "DRESS FITTING ROOM",
    "포토존",
    "PHOTO ZONE"
]
```
- **타입**: `list[str]`
- **설명**: 실제로 인식된 텍스트 문자열들
- **용도**: 최종 OCR 결과, API 응답에 주로 사용

### 2. `rec_scores` (텍스트 인식 신뢰도)
```python
rec_scores = [
    0.9995,   # "메이크업존"의 신뢰도
    0.9999,   # "MAKEUP ZONE"의 신뢰도
    0.9984,   # "드레스 피팅룸"의 신뢰도
    0.9841,   # "DRESS FITTING ROOM"의 신뢰도
    0.9998,   # "포토존"의 신뢰도
    0.9554    # "PHOTO ZONE"의 신뢰도
]
```
- **타입**: `list[float]`
- **범위**: 0.0 ~ 1.0 (높을수록 신뢰도 높음)
- **용도**: 품질 검증, 낮은 신뢰도 결과 필터링

### 3. `rec_polys` vs `dt_polys` (좌표 정보)

#### `rec_polys` (인식용 정규화된 좌표)
```python
rec_polys = [
    np.array([[318, 238], [484, 238], [484, 268], [318, 268]]),  # 정사각형에 가까움
    np.array([[318, 297], [484, 297], [484, 327], [318, 327]]),
    # ...
]
```
- **특징**: 텍스트 인식을 위해 정규화된 좌표
- **형태**: 일반적으로 정사각형에 가까움
- **용도**: 일반적인 바운딩 박스 표시

#### `dt_polys` (감지 단계 원본 좌표)
```python
dt_polys = [
    np.array([[318.2, 237.8], [484.1, 238.2], [483.9, 268.1], [317.8, 267.7]]),  # 실제 기울어진 형태
    # 더 정확한 실제 위치 반영
]
```
- **특징**: 텍스트 감지 단계에서 찾은 실제 좌표
- **형태**: 회전, 기울어진 텍스트의 실제 형태 반영
- **용도**: 정확한 시각화, 레이아웃 분석

### 4. 좌표 형식 설명

```python
# 바운딩 박스 좌표 순서 (시계방향)
poly = [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]

# 시각적 표현:
# [0] 좌상단 ────── [1] 우상단
#  │                    │
#  │       텍스트        │
#  │                    │
# [3] 좌하단 ────── [2] 우하단
```

---

## ⏱️ 성능 메타데이터

### 처리 시간 정보
```python
{
    'det_time': 0.123,          # 텍스트 감지 시간
    'rec_time': 0.456,          # 텍스트 인식 시간
    'total_time': 0.789,        # 전체 처리 시간
    'preprocess_time': 0.045,   # 전처리 시간
    'postprocess_time': 0.021   # 후처리 시간
}
```

### 모델 정보
```python
{
    'det_model_name': 'PP-OCRv5_server_det',
    'rec_model_name': 'korean_PP-OCRv5_mobile_rec',
    'cls_model_name': 'ch_ppocr_mobile_v2.0_cls'
}
```

---

## 🖼️ 이미지 관련 메타데이터

### 이미지 크기 및 변환 정보
```python
{
    'image_shape': (1080, 1920, 3),     # 원본 크기 (H, W, C)
    'processed_shape': (960, 1280, 3),  # 처리된 크기
    'scale_factor': 0.888,              # 리사이즈 비율
    'pad_info': {                       # 패딩 정보
        'top': 0, 'bottom': 60, 
        'left': 0, 'right': 0
    }
}
```

### 품질 평가 정보
```python
{
    'image_quality': 'good',            # 이미지 품질 등급
    'blur_score': 0.123,                # 블러 정도 (낮을수록 선명)
    'brightness': 128.5,                # 평균 밝기 (0-255)
    'contrast': 0.234,                  # 대비도
    'noise_level': 'low'                # 노이즈 수준
}
```

---

## 📊 통계 정보

### 텍스트 통계
```python
{
    'line_count': 6,                    # 감지된 텍스트 라인 수
    'char_count': 45,                   # 총 문자 수 (추정)
    'avg_confidence': 0.9524,           # 평균 신뢰도
    'min_confidence': 0.8234,           # 최소 신뢰도
    'max_confidence': 0.9999            # 최대 신뢰도
}
```

### 언어 감지 정보
```python
{
    'detected_language': 'korean',      # 감지된 주 언어
    'language_confidence': 0.9345,     # 언어 감지 신뢰도
    'script_type': 'hangul',            # 문자 체계
    'mixed_script': False               # 혼합 문자 여부
}
```

---

## 💻 실제 사용 예시

### 1. 기본 텍스트 추출
```python
def extract_texts(result):
    """텍스트만 간단히 추출"""
    if result and len(result) > 0:
        page_result = result[0]
        return page_result.get('rec_texts', [])
    return []

# 사용
result = ocr.run_ocr_from_path('image.jpg')
texts = extract_texts(result)
print(f"인식된 텍스트: {texts}")
```

### 2. 신뢰도와 함께 추출
```python
def extract_text_with_confidence(result, min_confidence=0.8):
    """신뢰도 임계값 이상의 텍스트만 추출"""
    if not result or len(result) == 0:
        return []
    
    page_result = result[0]
    texts = page_result.get('rec_texts', [])
    scores = page_result.get('rec_scores', [])
    
    filtered_texts = []
    for text, score in zip(texts, scores):
        if score >= min_confidence:
            filtered_texts.append((text, score))
    
    return filtered_texts

# 사용
reliable_texts = extract_text_with_confidence(result, min_confidence=0.9)
for text, confidence in reliable_texts:
    print(f"'{text}' (신뢰도: {confidence:.4f})")
```

### 3. 좌표와 함께 추출
```python
def extract_text_with_positions(result, use_accurate_coords=True):
    """텍스트와 위치 정보를 함께 추출"""
    if not result or len(result) == 0:
        return []
    
    page_result = result[0]
    texts = page_result.get('rec_texts', [])
    
    # 더 정확한 좌표 사용 여부 선택
    coord_key = 'dt_polys' if use_accurate_coords else 'rec_polys'
    polys = page_result.get(coord_key, [])
    scores = page_result.get('rec_scores', [])
    
    results = []
    for i in range(min(len(texts), len(polys), len(scores))):
        # 바운딩 박스의 좌상단, 우하단 좌표 계산
        poly = polys[i]
        if isinstance(poly, np.ndarray) and poly.shape == (4, 2):
            x_coords = poly[:, 0]
            y_coords = poly[:, 1]
            bbox = {
                'left': int(min(x_coords)),
                'top': int(min(y_coords)),
                'right': int(max(x_coords)),
                'bottom': int(max(y_coords))
            }
        else:
            bbox = None
        
        results.append({
            'text': texts[i],
            'confidence': scores[i],
            'bbox': bbox,
            'polygon': poly.tolist() if isinstance(poly, np.ndarray) else poly
        })
    
    return results

# 사용
text_positions = extract_text_with_positions(result)
for item in text_positions:
    print(f"텍스트: '{item['text']}'")
    print(f"위치: {item['bbox']}")
    print(f"신뢰도: {item['confidence']:.4f}")
    print("-" * 30)
```

### 4. 성능 분석
```python
def analyze_performance(result):
    """OCR 성능 분석"""
    if not result or len(result) == 0:
        return None
    
    page_result = result[0]
    
    # 처리 시간 분석
    times = {
        'total': page_result.get('total_time', 0),
        'detection': page_result.get('det_time', 0),
        'recognition': page_result.get('rec_time', 0),
        'preprocessing': page_result.get('preprocess_time', 0),
        'postprocessing': page_result.get('postprocess_time', 0)
    }
    
    # 품질 분석
    scores = page_result.get('rec_scores', [])
    quality = {
        'text_count': len(page_result.get('rec_texts', [])),
        'avg_confidence': sum(scores) / len(scores) if scores else 0,
        'min_confidence': min(scores) if scores else 0,
        'max_confidence': max(scores) if scores else 0,
        'low_confidence_count': sum(1 for s in scores if s < 0.8)
    }
    
    # 모델 정보
    models = {
        'detection': page_result.get('det_model_name', 'Unknown'),
        'recognition': page_result.get('rec_model_name', 'Unknown'),
        'version': page_result.get('paddleocr_version', 'Unknown')
    }
    
    return {
        'performance': times,
        'quality': quality,
        'models': models
    }

# 사용
analysis = analyze_performance(result)
if analysis:
    print(f"⏱️  총 처리시간: {analysis['performance']['total']:.3f}초")
    print(f"📊 평균 신뢰도: {analysis['quality']['avg_confidence']:.4f}")
    print(f"📝 인식 텍스트 수: {analysis['quality']['text_count']}개")
    print(f"🤖 사용 모델: {analysis['models']['recognition']}")
```

---

