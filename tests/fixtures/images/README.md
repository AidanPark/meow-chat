# 테스트 이미지 가이드

## 📂 폴더 구조

```
tests/
├── fixtures/           # 테스트 데이터 (픽스처)
│   ├── images/        # 실제 OCR 테스트용 이미지
│   │   ├── .gitkeep
│   │   ├── README.md  (이 파일)
│   │   ├── sample_checkup.jpg      # 고양이 건강검진 이미지
│   │   ├── my_test_image.png       # 기타 테스트 이미지
│   │   └── ...
│   └── data/          # (향후) JSON, CSV 등 테스트 데이터
├── test_ocr.py        # OCR 단위 테스트
├── test_ocr_real.py   # 실제 Google Vision API 테스트
└── ...
```

## 📸 이미지 추가 방법

### Windows 탐색기에서
```
\\wsl.localhost\ubuntu-24.04\home\aidan\projects\meow-chat\tests\fixtures\images\
```
위 경로에 이미지 파일을 복사하세요.

### 터미널에서
```bash
# 이미지 복사
cp /path/to/your/checkup-image.jpg tests/fixtures/images/sample_checkup.jpg

# 또는
cd /home/aidan/projects/meow-chat/tests/fixtures/images
# 파일을 여기에 복사
```

## 📝 권장 파일명

테스트 코드가 자동으로 찾는 파일명:
- `sample_checkup.jpg` ⭐ (권장)
- `sample_checkup.png`
- `my_test_image.jpg`
- `my_test_image.png`
- `test_image.jpg`
- `test_image.png`

> 💡 다른 파일명을 사용해도 되지만, 위 파일명 중 하나가 있으면 테스트가 자동으로 실행됩니다.

## 🚀 테스트 실행

```bash
# 실제 이미지 테스트 (fixtures/images/ 폴더의 이미지 사용)
poetry run pytest tests/test_ocr_real.py::test_google_vision_real_image_file -v -s

# 모든 Google Vision 테스트 실행
poetry run pytest tests/test_ocr_real.py -v -s

# "real" 키워드가 포함된 테스트만 실행
poetry run pytest tests/ -k "real" -v -s
```

## 📋 지원 형식

- **이미지**: JPG, JPEG, PNG, GIF, BMP
- **문서**: PDF (향후 지원 예정)
- **권장 사양**:
  - 해상도: 1000x1000px 이상
  - 파일 크기: 10MB 이하
  - 텍스트가 선명하게 보이는 이미지

## 🔒 보안 및 개인정보 보호

- ✅ `.gitignore`에 의해 이미지 파일들은 자동으로 제외됩니다
- ✅ 실제 환자(반려동물) 정보가 포함된 이미지는 Git에 커밋되지 않습니다
- ⚠️ 테스트 후 민감한 이미지는 삭제하는 것을 권장합니다

## 💡 사용 예시

### 1. 고양이 건강검진 결과 이미지 테스트
```bash
# 1. 이미지 추가
cp ~/Downloads/cat_checkup_2024.jpg tests/fixtures/images/sample_checkup.jpg

# 2. 테스트 실행
poetry run pytest tests/test_ocr_real.py::test_google_vision_real_image_file -v -s

# 3. 결과 확인 (OCR 추출 텍스트가 터미널에 출력됨)
```

### 2. 여러 이미지 비교 테스트
```bash
# 여러 이미지를 추가하고 순차적으로 테스트
cp image1.jpg tests/fixtures/images/sample_checkup.jpg
poetry run pytest tests/test_ocr_real.py::test_google_vision_real_image_file -s

cp image2.jpg tests/fixtures/images/sample_checkup.jpg
poetry run pytest tests/test_ocr_real.py::test_google_vision_real_image_file -s
```

## 📊 예상 출력

```
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
  4 │ 12.1
  5 │ %
...
================================================================================

📦 개별 텍스트 블록 정보 (상위 10개):
────────────────────────────────────────────────────────────────────────────────
 1. [  44,  84 →   46, 100]   2x16px │ 
 2. [  47,  83 →   99, 101]  52x18px │ LYMPHO
 3. [ 101,  84 →  107, 100]   6x16px │ (
 4. [ 111,  84 →  116, 100]   5x16px │ %
 5. [ 117,  84 →  120, 100]   3x16px │ )
...
────────────────────────────────────────────────────────────────────────────────
```

**출력 정보 설명:**
- ⏱️ **처리 시간**: OCR API 호출 소요 시간
- 📐 **이미지 크기**: 원본 이미지의 픽셀 크기
- 📍 **텍스트 영역**: 전체 텍스트가 차지하는 바운딩 박스 좌표
- 📦 **텍스트 블록**: Google Vision이 인식한 개별 단어/문장 개수
- 📄 **추출된 전체 텍스트**: 줄 번호와 함께 포맷팅된 텍스트
- 📦 **개별 텍스트 블록**: 각 단어의 좌표(x,y)와 크기(width x height)

## 🛠️ 트러블슈팅

### 이미지를 찾을 수 없다는 에러
```
SKIPPED - 테스트 이미지를 찾을 수 없습니다.
```
→ `tests/fixtures/images/` 폴더에 권장 파일명으로 이미지를 추가하세요.

### OCR 결과가 이상함
- 이미지 해상도를 확인하세요 (너무 작거나 흐릿하면 인식률 저하)
- 이미지 회전이 필요한지 확인하세요
- 텍스트 부분이 명확하게 보이는지 확인하세요

### API 에러
```
google.api_core.exceptions.Unauthenticated
```
→ `GOOGLE_APPLICATION_CREDENTIALS` 환경변수가 설정되어 있는지 확인하세요.

## 📚 추가 문서

- 전체 테스트 가이드: `docs/TEST_GUIDE.md`
- API 키 설정: `docs/API_KEYS_SETUP.md`
- 빠른 시작: `docs/QUICKSTART.md`

