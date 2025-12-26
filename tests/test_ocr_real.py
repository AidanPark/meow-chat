"""실제 OCR API 테스트 (Google Vision)

주의: 이 테스트는 실제 Google Cloud Vision API를 호출합니다.
- GOOGLE_APPLICATION_CREDENTIALS 환경변수가 설정되어 있어야 합니다.
- API 호출 비용이 발생할 수 있습니다.
- 네트워크 연결이 필요합니다.

실행:
    poetry run pytest tests/test_ocr_real.py -v

스킵하고 싶다면:
    poetry run pytest tests/ -v -k "not real"
"""

import io

import pytest
from PIL import Image, ImageDraw, ImageFont

from src.services.ocr.google_vision import GoogleVisionOCR


@pytest.fixture
def google_vision_ocr():
    """Google Vision OCR 서비스 픽스처"""
    try:
        return GoogleVisionOCR()
    except Exception as e:
        pytest.skip(f"Google Vision API 초기화 실패: {e}")


@pytest.fixture
def text_image():
    """텍스트가 포함된 테스트 이미지 생성"""
    # 800x400 흰색 배경 이미지 생성
    img = Image.new("RGB", (800, 400), color="white")
    draw = ImageDraw.Draw(img)

    # 텍스트 작성 (기본 폰트 사용)
    test_text = """고양이 건강검진 결과

혈액검사 (CBC)
- WBC: 8.5 K/uL
- RBC: 7.2 M/uL
- HGB: 12.3 g/dL

화학검사
- BUN: 25 mg/dL
- Creatinine: 1.2 mg/dL
- ALT: 45 U/L"""

    # 폰트 크기를 조정하여 텍스트 작성
    draw.text((50, 50), test_text, fill="black")

    return img


@pytest.fixture
def korean_image():
    """한글 텍스트 이미지"""
    img = Image.new("RGB", (600, 300), color="white")
    draw = ImageDraw.Draw(img)

    korean_text = """고양이 이름: 나비
나이: 3세
성별: 암컷(중성화)
체중: 4.2kg"""

    draw.text((50, 50), korean_text, fill="black")
    return img


@pytest.fixture
def english_image():
    """영문 텍스트 이미지"""
    img = Image.new("RGB", (600, 200), color="white")
    draw = ImageDraw.Draw(img)

    english_text = """Cat Name: Nabi
Age: 3 years
Weight: 4.2kg
Status: Healthy"""

    draw.text((50, 50), english_text, fill="black")
    return img


def test_google_vision_extract_text(google_vision_ocr, text_image):
    """Google Vision으로 텍스트 추출 테스트"""
    result = google_vision_ocr.extract_text(text_image)

    # 기본 검증
    assert result.text is not None
    assert len(result.text) > 0
    assert result.metadata["source"] == "google_vision"

    # 텍스트 내용 검증 (PIL 기본 폰트는 한글을 제대로 렌더링하지 못하므로 영문/숫자 검증)
    text_upper = result.text.upper()
    # CBC, WBC, RBC 등 의료 용어나 숫자가 포함되어 있는지 확인
    assert "CBC" in text_upper or "WBC" in text_upper or "8.5" in result.text or "BUN" in text_upper

    print(f"\n추출된 텍스트:\n{result.text}")
    print(f"메타데이터: {result.metadata}")


def test_google_vision_korean_text(google_vision_ocr, korean_image):
    """한글 텍스트 인식 테스트"""
    result = google_vision_ocr.extract_text(korean_image)

    assert result.text is not None
    assert len(result.text) > 0

    # PIL 기본 폰트는 한글을 제대로 렌더링하지 못하므로 숫자로 검증
    # "나이: 3세", "체중: 4.2kg" → "3", "4.2kg" 등이 추출될 것으로 예상
    assert "3" in result.text or "4.2" in result.text or "kg" in result.text.lower()

    print(f"\n한글 추출 결과:\n{result.text}")


def test_google_vision_english_text(google_vision_ocr, english_image):
    """영문 텍스트 인식 테스트"""
    result = google_vision_ocr.extract_text(english_image)

    assert result.text is not None
    assert len(result.text) > 0

    # 영문 키워드 검증 (대소문자 무시)
    text_lower = result.text.lower()
    assert "cat" in text_lower or "nabi" in text_lower or "healthy" in text_lower

    print(f"\n영문 추출 결과:\n{result.text}")


def test_google_vision_empty_image(google_vision_ocr):
    """빈 이미지 처리 테스트"""
    # 텍스트가 없는 순수 흰색 이미지
    empty_image = Image.new("RGB", (200, 200), color="white")

    result = google_vision_ocr.extract_text(empty_image)

    # 텍스트가 없어도 오류가 발생하지 않아야 함
    assert result is not None
    assert result.text == ""
    assert result.confidence == 0.0


def test_google_vision_multiple_images(google_vision_ocr, korean_image, english_image):
    """다중 이미지 추출 테스트"""
    images = [korean_image, english_image]
    results = google_vision_ocr.extract_text_from_images(images)

    assert len(results) == 2

    # 각 결과 검증
    for i, result in enumerate(results):
        assert result.text is not None
        assert result.metadata["source"] == "google_vision"
        print(f"\n이미지 {i+1} 추출 결과:\n{result.text}")


def test_google_vision_real_image_file(google_vision_ocr):
    """실제 이미지 파일 테스트 (수동 실행용)

    사용법:
    1. tests/fixtures/images/ 폴더에 실제 이미지 파일을 추가:
       - sample_checkup.jpg (또는 .png, .jpeg)
       - my_test_image.jpg
       - 다른 이미지 파일명도 가능

    2. 테스트 실행:
       # 특정 테스트만 실행
       poetry run pytest tests/test_ocr_real.py::test_google_vision_real_image_file -v -s

       # 모든 real 테스트 실행
       poetry run pytest tests/ -k "real" -v -s
    """
    from pathlib import Path
    from src.utils.images import load_image

    # 테스트 이미지 경로 (fixtures/images/ 폴더에서 찾기)
    fixtures_dir = Path(__file__).parent / "fixtures" / "images"

    # fixtures 디렉토리가 없으면 안내 메시지와 함께 skip
    if not fixtures_dir.exists():
        pytest.skip(
            f"테스트 픽스처 폴더가 없습니다.\n"
            f"다음 명령으로 생성하세요:\n"
            f"mkdir -p {fixtures_dir}"
        )

    possible_names = [
        "sample_checkup.jpg",
        "sample_checkup.png",
        "sample_checkup.jpeg",
        "my_test_image.jpg",
        "my_test_image.png",
        "test_image.jpg",
        "test_image.png",
    ]

    test_image_path = None
    for name in possible_names:
        path = fixtures_dir / name
        if path.exists():
            test_image_path = path
            break

    if test_image_path is None:
        pytest.skip(
            f"테스트 이미지를 찾을 수 없습니다.\n"
            f"{fixtures_dir}/ 폴더에 다음 중 하나를 추가하세요:\n"
            f"{', '.join(possible_names)}\n"
            f"\n자세한 안내: tests/fixtures/images/README.md"
        )

    print(f"\n📁 테스트 이미지: {test_image_path.name}")

    # 이미지 로드 및 dimension 확인
    image = load_image(test_image_path)
    img_width, img_height = image.size

    # OCR 요청 시간 측정
    import time
    start_time = time.time()
    result = google_vision_ocr.extract_text(image)
    end_time = time.time()
    elapsed_time = end_time - start_time

    print(f"\n✅ 실제 이미지 OCR 결과:")
    print(f"⏱️  처리 시간: {elapsed_time:.2f}초")
    print(f"📐 이미지 크기: {img_width} x {img_height} px")

    # 전체 텍스트 영역 바운딩 박스
    full_bounds = result.metadata.get('full_bounds')
    if full_bounds:
        width = full_bounds['x_max'] - full_bounds['x_min']
        height = full_bounds['y_max'] - full_bounds['y_min']
        print(f"📍 텍스트 영역: ({full_bounds['x_min']}, {full_bounds['y_min']}) → ({full_bounds['x_max']}, {full_bounds['y_max']})  [{width} x {height} px]")

    print(f"📊 텍스트 길이: {len(result.text)} 글자")
    print(f"📦 텍스트 블록: {result.metadata.get('num_blocks', 0)}개")

    print(f"\n📄 추출된 전체 텍스트:")
    print('=' * 80)
    # 텍스트를 줄 단위로 포맷팅 (빈 줄 정리)
    lines = result.text.strip().split('\n')
    for i, line in enumerate(lines, 1):
        if line.strip():  # 빈 줄이 아닌 경우만 출력
            print(f"{i:3d} │ {line}")
    print('=' * 80)

    # 개별 텍스트 블록 정보 (처음 10개만)
    text_blocks = result.metadata.get('text_blocks', [])
    if text_blocks:
        print(f"\n📦 개별 텍스트 블록 정보 (상위 {len(text_blocks)}개):")
        print('─' * 80)
        for i, block in enumerate(text_blocks, 1):
            bounds = block['bounds']
            text = block['text']
            width = bounds['x_max'] - bounds['x_min']
            height = bounds['y_max'] - bounds['y_min']
            # 텍스트가 너무 길면 줄임
            display_text = text if len(text) <= 30 else text[:27] + "..."
            print(f"{i:2d}. [{bounds['x_min']:4d},{bounds['y_min']:4d} → {bounds['x_max']:4d},{bounds['y_max']:4d}] {width:3d}x{height:2d}px │ {display_text}")
        print('─' * 80)

    assert result.text is not None
    assert len(result.text) > 0


if __name__ == "__main__":
    # 직접 실행 시 간단한 테스트
    print("Google Vision OCR 테스트 시작...")

    ocr = GoogleVisionOCR()

    # 간단한 테스트 이미지 생성
    img = Image.new("RGB", (400, 200), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((50, 50), "고양이 건강검진\nCat Health Check", fill="black")

    result = ocr.extract_text(img)
    print(f"\n추출된 텍스트:\n{result.text}")
    print(f"메타데이터: {result.metadata}")

