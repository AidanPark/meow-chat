# 🧪 meow-chat 테스트 가이드

> 테스트 실행, Pytest Fixture 이해, 각 테스트 파일 설명을 모두 포함한 통합 문서입니다.

## 📑 목차

1. [빠른 시작](#빠른-시작)
2. [Pytest Fixture 이해하기](#pytest-fixture-이해하기)
3. [기본 테스트 실행 방법](#기본-테스트-실행-방법)
4. [테스트 파일별 설명](#테스트-파일별-설명)
5. [주의사항](#주의사항)
6. [트러블슈팅](#트러블슈팅)

---

## 빠른 시작

### 자주 사용하는 명령어

```bash
# 모든 테스트 실행
poetry run pytest tests/ -v

# 특정 테스트 하나만 실행
poetry run pytest tests/test_ocr.py::test_dummy_ocr_extract_text -v

# API 비용 없이 테스트 (test_ocr_real.py 파일 제외)
poetry run pytest tests/ -v -k "not real"

# 커버리지 확인
poetry run pytest --cov=src --cov-report=html
```

---

## 📂 테스트 디렉토리 구조

```
tests/
├── fixtures/              # 테스트 데이터 (픽스처)
│   ├── __init__.py       # 픽스처 헬퍼 함수
│   └── images/           # 실제 OCR 테스트용 이미지
│       ├── .gitkeep
│       ├── README.md     # 이미지 가이드
│       ├── sample_checkup.jpg  # 기본 테스트 이미지 (심볼릭 링크)
│       └── *.jpg, *.png  # 실제 건강검진 이미지들
├── conftest.py           # pytest 설정 및 공통 fixture
├── test_ocr.py          # OCR 단위 테스트 (Dummy)
├── test_ocr_real.py     # 실제 Google Vision API 테스트
├── test_llm.py          # LLM Provider 테스트
├── test_chat.py         # ChatService 통합 테스트
└── test_utils.py        # 유틸리티 함수 테스트
```

**픽스처 관리**:
- 테스트 이미지는 `tests/fixtures/images/`에 저장
- `.gitignore`에 의해 이미지 파일은 자동으로 제외됨 (개인정보 보호)
- 자세한 안내: `tests/fixtures/images/README.md`

---

## Pytest Fixture 이해하기

### 테스트 함수의 파라미터는 어디서 오는가?

```python
def test_dummy_ocr_extract_text(dummy_ocr_service, sample_image):
    """더미 OCR 텍스트 추출 테스트"""
    result = dummy_ocr_service.extract_text(sample_image)
    # ...
```

**🤔 질문:** `dummy_ocr_service`와 `sample_image`는 어떻게 전달되는가?

**✨ 답:** pytest의 **Fixture 메커니즘**이 자동으로 주입합니다!

### Fixture 동작 원리

#### 1️⃣ `conftest.py`에 Fixture 정의
```python
# tests/conftest.py

@pytest.fixture
def dummy_ocr_service():
    """더미 OCR 서비스 픽스처"""
    return DummyOCR()  # 인스턴스 생성 후 반환

@pytest.fixture
def sample_image():
    """샘플 이미지 픽스처"""
    return Image.new("RGB", (100, 100), color="white")  # 이미지 생성 후 반환
```

#### 2️⃣ 테스트 함수에서 Fixture 사용
```python
# tests/test_ocr.py

def test_dummy_ocr_extract_text(dummy_ocr_service, sample_image):
    # pytest가 자동으로 수행:
    # 1. 파라미터 이름 'dummy_ocr_service' 확인
    # 2. conftest.py에서 같은 이름의 fixture 찾기
    # 3. fixture 함수 실행 → DummyOCR() 반환
    # 4. 반환된 객체를 dummy_ocr_service 파라미터에 주입
    # 5. 'sample_image'도 동일한 과정 반복
    
    result = dummy_ocr_service.extract_text(sample_image)
    # 이 시점에 dummy_ocr_service = DummyOCR 인스턴스
    #            sample_image = 100x100 흰색 이미지
```

#### 3️⃣ pytest 실행 시 자동 처리
```bash
poetry run pytest tests/test_ocr.py::test_dummy_ocr_extract_text -v
```

**내부 동작 순서:**
```
1. pytest가 test_dummy_ocr_extract_text 함수 발견
2. 함수 시그니처 분석: (dummy_ocr_service, sample_image)
3. 각 파라미터와 일치하는 fixture 검색
4. @pytest.fixture def dummy_ocr_service() 실행 → DummyOCR() 생성
5. @pytest.fixture def sample_image() 실행 → Image.new() 생성
6. 생성된 객체들을 테스트 함수에 주입
7. 테스트 함수 실행
```

### 💡 핵심 정리

| 항목 | 설명 |
|-----|------|
| **Fixture란?** | 테스트에 필요한 사전 준비물(객체, 데이터)을 자동으로 제공하는 함수 |
| **어디에 정의?** | `tests/conftest.py` (모든 테스트에서 공유) 또는 각 테스트 파일 내부 |
| **어떻게 사용?** | 테스트 함수의 **파라미터 이름**을 fixture 이름과 동일하게 작성 |
| **장점** | 중복 코드 제거, 테스트 격리, 자동 정리(teardown) |

### 실제 예시 비교

#### ❌ Fixture 없이 (중복 코드)
```python
def test_ocr_1():
    ocr = DummyOCR()  # 매번 생성
    img = Image.new("RGB", (100, 100), color="white")
    result = ocr.extract_text(img)
    assert result.text is not None

def test_ocr_2():
    ocr = DummyOCR()  # 또 생성
    img = Image.new("RGB", (100, 100), color="white")  # 또 생성
    result = ocr.extract_text(img)
    assert len(result.text) > 0
```

#### ✅ Fixture 사용 (깔끔)
```python
@pytest.fixture
def dummy_ocr_service():
    return DummyOCR()

@pytest.fixture
def sample_image():
    return Image.new("RGB", (100, 100), color="white")

def test_ocr_1(dummy_ocr_service, sample_image):
    result = dummy_ocr_service.extract_text(sample_image)
    assert result.text is not None

def test_ocr_2(dummy_ocr_service, sample_image):
    result = dummy_ocr_service.extract_text(sample_image)
    assert len(result.text) > 0
```

---

## 기본 테스트 실행 방법

### 1. 특정 테스트 함수 하나만 실행
```bash
poetry run pytest tests/test_ocr.py::test_dummy_ocr_extract_text -v
```

**옵션 설명:**
- `-v` (verbose): 자세한 출력
- `-s`: print 출력도 표시
- `--tb=short`: 에러 발생 시 짧은 traceback

**예제:**
```bash
# test_dummy_ocr_extract_text 테스트만 실행
poetry run pytest tests/test_ocr.py::test_dummy_ocr_extract_text -v

# 출력과 함께 실행
poetry run pytest tests/test_ocr.py::test_dummy_ocr_extract_text -v -s
```

### 2. 특정 파일의 모든 테스트 실행
```bash
poetry run pytest tests/test_ocr.py -v
```

### 3. 모든 테스트 실행
```bash
poetry run pytest tests/ -v
```

### 4. 테스트 커버리지 확인
```bash
poetry run pytest --cov=src --cov-report=html
```
실행 후 `htmlcov/index.html` 파일을 브라우저로 열어서 확인

### 5. 특정 테스트 패턴으로 필터링 (`-k` 옵션)
```bash
# "dummy"가 포함된 테스트만 실행 (함수명/클래스명/파일명 기준)
poetry run pytest tests/ -k "dummy" -v

# "real"이 포함된 테스트 제외 (test_ocr_real.py 파일 전체 제외됨)
poetry run pytest tests/ -v -k "not real"
```

**📌 `-k` 옵션 작동 원리:**
- pytest가 **테스트 함수명, 클래스명, 파일명**에서 키워드를 찾습니다
- `test_ocr_real.py` 파일은 파일명에 "real"이 포함되어 있어서 전체가 필터링됩니다
- **예약어가 아니라 단순 문자열 매칭**입니다
- 논리 연산자 사용 가능: `and`, `or`, `not`
  ```bash
  # "chat" 또는 "llm"이 포함된 테스트만
  pytest -k "chat or llm"
  
  # "dummy"이지만 "ocr"은 아닌 테스트
  pytest -k "dummy and not ocr"
  ```

**📊 실제 동작 확인:**
```bash
# 전체: 19개 테스트
poetry run pytest tests/ --collect-only -q

# "not real": test_ocr_real.py 제외 → 13개 선택
poetry run pytest tests/ -k "not real" --collect-only -q

# "real": test_ocr_real.py만 → 6개 선택
poetry run pytest tests/ -k "real" --collect-only -q
```

### 유용한 옵션 표

| 옵션 | 설명 | 예제 |
|-----|------|------|
| `-v` | 자세한 출력 | `pytest tests/ -v` |
| `-s` | print 출력 표시 | `pytest tests/ -s` |
| `-k` | 키워드 필터 | `pytest -k "chat"` |
| `--tb=short` | 짧은 traceback | `pytest --tb=short` |
| `--lf` | 실패한 테스트만 재실행 | `pytest --lf` |
| `--cov` | 커버리지 측정 | `pytest --cov=src` |
| `-x` | 첫 실패 시 중단 | `pytest -x` |

---

## 테스트 파일별 설명

### 📄 `test_ocr.py` - OCR 서비스 테스트

**테스트 대상:** `src/services/ocr/dummy.py` (DummyOCR)

#### 1️⃣ `test_dummy_ocr_extract_text`
**목적:** 더미 OCR이 이미지에서 텍스트를 추출하는지 테스트

**코드:**
```python
def test_dummy_ocr_extract_text(dummy_ocr_service, sample_image):
    """더미 OCR 텍스트 추출 테스트"""
    result = dummy_ocr_service.extract_text(sample_image)

    assert result.text is not None
    assert len(result.text) > 0
    assert result.confidence == 1.0
    assert result.metadata["source"] == "dummy"
```

**실행:**
```bash
poetry run pytest tests/test_ocr.py::test_dummy_ocr_extract_text -v
```

**검증 내용:**
- ✅ 텍스트가 추출되었는가 (`result.text is not None`)
- ✅ 텍스트 길이가 0보다 큰가 (`len(result.text) > 0`)
- ✅ 신뢰도가 1.0인가 (더미는 항상 100% 신뢰도)
- ✅ 메타데이터에 "dummy" 소스가 기록되었는가

**결과 예시:**
```
tests/test_ocr.py::test_dummy_ocr_extract_text PASSED [100%]
1 passed in 0.01s
```

#### 2️⃣ `test_dummy_ocr_extract_from_multiple_images`
**목적:** 여러 이미지를 동시에 처리할 수 있는지 테스트

**코드:**
```python
def test_dummy_ocr_extract_from_multiple_images(dummy_ocr_service):
    """더미 OCR 다중 이미지 추출 테스트"""
    images = [Image.new("RGB", (100, 100), color="white") for _ in range(3)]
    results = dummy_ocr_service.extract_text_from_images(images)

    assert len(results) == 3
    for result in results:
        assert result.text is not None
        assert len(result.text) > 0
```

**검증 내용:**
- ✅ 3개 이미지 입력 → 3개 결과 반환
- ✅ 각 결과에 텍스트가 포함되어 있음

---

### 📄 `test_llm.py` - LLM 서비스 테스트

**테스트 대상:** `src/services/llm/dummy_llm.py` (DummyLLM)

#### 1️⃣ `test_dummy_llm_generate`
**목적:** LLM이 메시지를 받아 응답을 생성하는지 테스트

**코드:**
```python
def test_dummy_llm_generate(dummy_llm_service):
    """더미 LLM 응답 생성 테스트"""
    messages = [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="Hello!"),
    ]

    response = dummy_llm_service.generate(messages)

    assert response.content is not None
    assert len(response.content) > 0
    assert response.model == "dummy-model"
    assert response.usage is not None
    assert response.metadata["provider"] == "dummy"
```

**실행:**
```bash
poetry run pytest tests/test_llm.py::test_dummy_llm_generate -v
```

**검증 내용:**
- ✅ 응답 내용이 있는가
- ✅ 모델명이 "dummy-model"인가
- ✅ 토큰 사용량(usage) 정보가 있는가
- ✅ 메타데이터에 "dummy" 제공자가 기록되었는가

#### 2️⃣ `test_dummy_llm_chat`
**목적:** 간단한 채팅 인터페이스가 작동하는지 테스트

**코드:**
```python
def test_dummy_llm_chat(dummy_llm_service):
    """더미 LLM 간단한 채팅 테스트"""
    response = dummy_llm_service.chat("Tell me about cats", system_message="You are a vet.")

    assert response is not None
    assert len(response) > 0
    assert isinstance(response, str)
```

**검증 내용:**
- ✅ 응답이 문자열로 반환되는가
- ✅ 응답 길이가 0보다 큰가

---

### 📄 `test_chat.py` - 채팅 서비스 통합 테스트

**테스트 대상:** `src/services/chat/chat_service.py` (ChatService)

이 테스트는 OCR과 LLM을 결합한 전체 파이프라인을 검증합니다.

#### 1️⃣ `test_chat_service_analyze_image`
**목적:** 이미지를 업로드하면 OCR → LLM 분석이 실행되는지 테스트

**코드:**
```python
def test_chat_service_analyze_image(chat_service, sample_image):
    """채팅 서비스 이미지 분석 테스트"""
    result = chat_service.analyze_image(sample_image)

    assert result is not None
    assert len(result) > 0
    assert chat_service.ocr_text is not None
    assert len(chat_service.get_history()) == 2  # user upload + assistant response
```

**실행:**
```bash
poetry run pytest tests/test_chat.py::test_chat_service_analyze_image -v
```

**검증 내용:**
- ✅ 분석 결과가 반환되는가
- ✅ OCR 텍스트가 저장되었는가
- ✅ 대화 히스토리에 2개 메시지가 있는가 (사용자 업로드 + 어시스턴트 응답)

**플로우:**
```
이미지 입력 → OCR 추출 → LLM 분석 → 결과 반환 + 히스토리 저장
```

#### 2️⃣ `test_chat_service_chat`
**목적:** 이미지 분석 후 추가 질문이 가능한지 테스트

**코드:**
```python
def test_chat_service_chat(chat_service, sample_image):
    """채팅 서비스 대화 테스트"""
    # 먼저 이미지 분석
    chat_service.analyze_image(sample_image)

    # 후속 질문
    response = chat_service.chat("고양이의 건강 상태는 어떤가요?")

    assert response is not None
    assert len(response) > 0
    assert len(chat_service.get_history()) == 4  # 이전 2개 + 새로운 2개
```

**검증 내용:**
- ✅ 후속 질문에 응답하는가
- ✅ 대화 히스토리가 누적되는가 (총 4개 메시지)

#### 3️⃣ `test_chat_service_clear_history`
**목적:** 대화 히스토리 초기화 기능 테스트

**코드:**
```python
def test_chat_service_clear_history(chat_service, sample_image):
    """채팅 서비스 히스토리 초기화 테스트"""
    chat_service.analyze_image(sample_image)
    chat_service.chat("질문")

    assert len(chat_service.get_history()) > 0

    chat_service.clear_history()

    assert len(chat_service.get_history()) == 0
    assert chat_service.ocr_text is None
```

**검증 내용:**
- ✅ 히스토리가 삭제되는가
- ✅ OCR 텍스트도 함께 초기화되는가

#### 4️⃣ `test_chat_service_analyze_multiple_images`
**목적:** 여러 페이지(이미지)를 동시에 분석하는지 테스트

**코드:**
```python
def test_chat_service_analyze_multiple_images(chat_service, sample_image):
    """채팅 서비스 다중 이미지 분석 테스트"""
    images = [sample_image, sample_image]
    result = chat_service.analyze_images(images)

    assert result is not None
    assert len(result) > 0
    assert "다음 페이지" in chat_service.ocr_text
```

**검증 내용:**
- ✅ 여러 이미지가 처리되는가
- ✅ OCR 텍스트에 페이지 구분자가 포함되는가

---

### 📄 `test_utils.py` - 이미지 유틸리티 테스트

**테스트 대상:** `src/utils/images.py`

#### 1️⃣ `test_load_image_from_bytes`
**목적:** 바이트 데이터를 PIL 이미지로 변환하는지 테스트

**코드:**
```python
def test_load_image_from_bytes():
    """바이트에서 이미지 로드 테스트"""
    img = Image.new("RGB", (100, 100), color="red")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    img_bytes = buffer.getvalue()

    loaded_img = load_image_from_bytes(img_bytes)

    assert loaded_img.size == (100, 100)
    assert loaded_img.mode == "RGB"
```

**검증 내용:**
- ✅ 바이트 → 이미지 변환이 성공하는가
- ✅ 이미지 크기와 모드가 유지되는가

#### 2️⃣ `test_image_to_bytes`
**목적:** PIL 이미지를 바이트로 변환하는지 테스트

#### 3️⃣ `test_resize_image`
**목적:** 큰 이미지를 비율을 유지하며 리사이즈하는지 테스트

**코드:**
```python
def test_resize_image():
    """이미지 리사이즈 테스트"""
    img = Image.new("RGB", (3000, 2000), color="green")
    resized = resize_image(img, max_width=1000, max_height=1000)

    assert resized.width <= 1000
    assert resized.height <= 1000
    # 비율이 유지되는지 확인
    original_ratio = img.width / img.height
    resized_ratio = resized.width / resized.height
    assert abs(original_ratio - resized_ratio) < 0.01
```

**검증 내용:**
- ✅ 최대 크기를 초과하지 않는가
- ✅ 가로세로 비율이 유지되는가

#### 4️⃣ `test_resize_image_no_change`
**목적:** 이미 작은 이미지는 리사이즈하지 않는지 테스트

#### 5️⃣ `test_validate_image_format`
**목적:** 이미지 파일 확장자 검증

**코드:**
```python
def test_validate_image_format():
    """이미지 형식 검증 테스트"""
    assert validate_image_format("test.jpg") is True
    assert validate_image_format("test.jpeg") is True
    assert validate_image_format("test.png") is True
    assert validate_image_format("test.PDF") is False
    assert validate_image_format("test.txt") is False
```

---

### 📄 `test_ocr_real.py` - 실제 Google Vision API 테스트

**⚠️ 주의:** 이 테스트는 실제 API를 호출하여 비용이 발생할 수 있습니다.

**실행:**
```bash
# test_ocr_real.py 파일만 실행
poetry run pytest tests/test_ocr_real.py -v

# 또는 -k 옵션으로 "real"이 포함된 테스트만 실행
poetry run pytest tests/ -k "real" -v

# 실제 OCR 테스트 제외하고 실행 (파일명에 "real" 포함된 것 제외)
poetry run pytest tests/ -v -k "not real"
```

#### 테스트 목록
1. `test_google_vision_extract_text` - 텍스트 이미지 인식
2. `test_google_vision_korean_text` - 한글 텍스트 인식
3. `test_google_vision_english_text` - 영문 텍스트 인식
4. `test_google_vision_empty_image` - 빈 이미지 처리
5. `test_google_vision_multiple_images` - 다중 이미지 처리
6. `test_google_vision_real_image_file` - **실제 파일 테스트**

**6번 테스트 (실제 파일 테스트) 사용법:**
```bash
# 1. 이미지 추가 (tests/fixtures/images/ 폴더에)
cp /path/to/checkup.jpg tests/fixtures/images/sample_checkup.jpg

# 2. 테스트 실행
poetry run pytest tests/test_ocr_real.py::test_google_vision_real_image_file -v -s

# 출력 예시:
📁 테스트 이미지: sample_checkup.jpg

✅ 실제 이미지 OCR 결과:
⏱️  처리 시간: 46.63초
📐 이미지 크기: 794 x 1123 px
📍 텍스트 영역: (41, 43) → (753, 1080)  [712 x 1037 px]
📊 텍스트 길이: 1043 글자
📦 텍스트 블록: 285개

📄 추출된 전체 텍스트:
================================================================================
  1 │ LYMPHO(%)
  2 │ Mono(%)
  3 │ 20.7 %
...
================================================================================

📦 개별 텍스트 블록 정보 (상위 10개):
────────────────────────────────────────────────────────────────────────────────
 1. [  44,  84 →   46, 100]   2x16px │ 
 2. [  47,  83 →   99, 101]  52x18px │ LYMPHO
 3. [ 101,  84 →  107, 100]   6x16px │ (
...
────────────────────────────────────────────────────────────────────────────────
```

💡 **자세한 가이드**: `tests/fixtures/images/README.md` 참고

**결과 예시:**
```
tests/test_ocr_real.py::test_google_vision_extract_text PASSED [47%]
추출된 텍스트:
고양이 건강검진 결과
혈액검사 (CBC)
- WBC: 8.5 K/uL
- RBC: 7.2 M/uL
...
```

---

## 전체 테스트 결과 요약

```bash
poetry run pytest tests/ -v
```

**결과:**
```
tests/test_chat.py::test_chat_service_analyze_image PASSED               [  5%]
tests/test_chat.py::test_chat_service_chat PASSED                        [ 10%]
tests/test_chat.py::test_chat_service_clear_history PASSED               [ 15%]
tests/test_chat.py::test_chat_service_analyze_multiple_images PASSED     [ 21%]
tests/test_llm.py::test_dummy_llm_generate PASSED                        [ 26%]
tests/test_llm.py::test_dummy_llm_chat PASSED                            [ 31%]
tests/test_ocr.py::test_dummy_ocr_extract_text PASSED                    [ 36%]
tests/test_ocr.py::test_dummy_ocr_extract_from_multiple_images PASSED    [ 42%]
tests/test_ocr_real.py::test_google_vision_extract_text PASSED           [ 47%]
tests/test_ocr_real.py::test_google_vision_korean_text PASSED            [ 52%]
tests/test_ocr_real.py::test_google_vision_english_text PASSED           [ 57%]
tests/test_ocr_real.py::test_google_vision_empty_image PASSED            [ 63%]
tests/test_ocr_real.py::test_google_vision_multiple_images PASSED        [ 68%]
tests/test_ocr_real.py::test_google_vision_real_image_file SKIPPED       [ 73%]
tests/test_utils.py::test_load_image_from_bytes PASSED                   [ 78%]
tests/test_utils.py::test_image_to_bytes PASSED                          [ 84%]
tests/test_utils.py::test_resize_image PASSED                            [ 89%]
tests/test_utils.py::test_resize_image_no_change PASSED                  [ 94%]
tests/test_utils.py::test_validate_image_format PASSED                   [100%]

================== 18 passed, 1 skipped in 18.33s ===================
```

---

## 테스트 작성 가이드

### Fixture 활용 (`conftest.py`)
프로젝트에서 사용하는 공통 fixture:

```python
@pytest.fixture
def dummy_ocr_service():
    """더미 OCR 서비스 픽스처"""
    return DummyOCR()

@pytest.fixture
def dummy_llm_service():
    """더미 LLM 서비스 픽스처"""
    return DummyLLM()

@pytest.fixture
def chat_service(dummy_ocr_service, dummy_llm_service):
    """채팅 서비스 픽스처"""
    return ChatService(dummy_ocr_service, dummy_llm_service)

@pytest.fixture
def sample_image():
    """샘플 이미지 픽스처"""
    return Image.new("RGB", (100, 100), color="white")
```

### 새 테스트 작성 시 체크리스트
- [ ] 타입 힌트 작성
- [ ] Docstring 작성 (Google Style)
- [ ] 필요한 fixture 선언
- [ ] assert 문으로 명확한 검증
- [ ] 실제 API 호출하는 테스트는 별도 파일로 분리

### 프로젝트 Fixture 목록

#### `conftest.py` (공통)

| Fixture 이름 | 반환 타입 | 설명 |
|-------------|----------|------|
| `dummy_ocr_service` | `DummyOCR` | 더미 OCR 서비스 |
| `dummy_llm_service` | `DummyLLM` | 더미 LLM 서비스 |
| `chat_service` | `ChatService` | OCR + LLM 통합 서비스 |
| `sample_image` | `PIL.Image` | 100x100 테스트 이미지 |

#### `test_ocr_real.py` (실제 API 테스트용)

| Fixture 이름 | 반환 타입 | 설명 |
|-------------|----------|------|
| `google_vision_ocr` | `GoogleVisionOCR` | Google Vision OCR 서비스 |
| `text_image` | `PIL.Image` | 의료 용어가 포함된 테스트 이미지 |
| `korean_image` | `PIL.Image` | 한글 텍스트 이미지 |
| `english_image` | `PIL.Image` | 영문 텍스트 이미지 |

---

## 주의사항

### 실제 API 테스트 (`test_ocr_real.py`)
- **API 비용 발생**: Google Vision API는 월 1,000건 무료, 초과 시 유료
- **환경변수 필요**:
  ```bash
  export GOOGLE_APPLICATION_CREDENTIALS=".credentials/google-vision-key.json"
  ```
- **네트워크 필요**: 실제 Google Cloud에 요청을 보냄

### 한글 폰트 문제
- PIL의 기본 폰트는 한글을 제대로 렌더링하지 못합니다
- 테스트 이미지에 한글을 넣어도 Google Vision이 인식하지 못할 수 있습니다
- 해결책:
  1. 실제 한글 폰트 사용 (예: NanumGothic.ttf)
  2. 영문/숫자로 검증 (현재 방식)
  3. 실제 의료 문서 이미지 사용

---

## 트러블슈팅

### 1. Fixture 관련 에러
```
fixture 'my_ocr' not found
```
**원인:** 파라미터 이름이 fixture 이름과 불일치

**해결:**
```python
# ❌ 잘못된 예
def test_something(my_ocr):  # fixture 이름과 다름
    pass

# ✅ 올바른 예
def test_something(dummy_ocr_service):  # conftest.py의 fixture 이름과 일치
    pass
```

### 2. `GOOGLE_APPLICATION_CREDENTIALS` 오류
```
ValueError: GOOGLE_APPLICATION_CREDENTIALS not set
```
**해결:** `.env` 파일에 환경변수 설정
```bash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

```bash
# 서비스 계정 키 확인
cat .credentials/google-vision-key.json | grep '"type"'
# 출력: "type": "service_account" 가 나와야 함
```

### 3. Poetry 가상환경 활성화 안 됨
```bash
# 가상환경 활성화
poetry shell

# 또는 직접 실행
poetry run pytest tests/ -v
```

### 4. 특정 테스트만 스킵하고 싶을 때
```bash
# "real" 키워드가 있는 테스트 제외
poetry run pytest tests/ -v -k "not real"

# @pytest.mark.skip 데코레이터 사용
@pytest.mark.skip(reason="아직 구현 중")
def test_something():
    pass
```

### 5. "AssertionError: assert ... in result.text"
- PIL 기본 폰트가 한글을 렌더링하지 못해서 발생
- 테스트 코드를 영문/숫자 검증으로 수정하거나 실제 한글 폰트 사용

---

## 테스트 파일 구조

```
tests/
├── conftest.py              # Fixture 정의 (공통)
├── test_ocr.py             # OCR 기본 테스트 (2개)
├── test_llm.py             # LLM 기본 테스트 (2개)
├── test_chat.py            # 통합 테스트 (4개)
├── test_utils.py           # 유틸리티 테스트 (5개)
├── test_ocr_real.py        # 실제 API 테스트 (5개)
├── streamlit_camera_demo.py # Streamlit 카메라 데모
└── OCR_TEST_SETUP.md       # Google Vision API 설정 가이드
```

### 데모 실행
```bash
# Streamlit 카메라 데모
poetry run streamlit run tests/streamlit_camera_demo.py
```

---

## 마지막 업데이트
**날짜:** 2025-12-25  
**테스트 통과율:** 18 passed, 1 skipped (94.7%)

