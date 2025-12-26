"""이미지 유틸리티 테스트"""

from io import BytesIO

from PIL import Image

from src.utils.images import (
    image_to_bytes,
    load_image_from_bytes,
    resize_image,
    validate_image_format,
)


def test_load_image_from_bytes():
    """바이트에서 이미지 로드 테스트"""
    # 샘플 이미지 생성
    img = Image.new("RGB", (100, 100), color="red")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    img_bytes = buffer.getvalue()

    # 바이트에서 로드
    loaded_img = load_image_from_bytes(img_bytes)

    assert loaded_img.size == (100, 100)
    assert loaded_img.mode == "RGB"


def test_image_to_bytes():
    """이미지를 바이트로 변환 테스트"""
    img = Image.new("RGB", (100, 100), color="blue")
    img_bytes = image_to_bytes(img, format="PNG")

    assert isinstance(img_bytes, bytes)
    assert len(img_bytes) > 0

    # 다시 로드해서 확인
    loaded_img = load_image_from_bytes(img_bytes)
    assert loaded_img.size == (100, 100)


def test_resize_image():
    """이미지 리사이즈 테스트"""
    img = Image.new("RGB", (3000, 2000), color="green")
    resized = resize_image(img, max_width=1000, max_height=1000)

    # 비율 유지하면서 리사이즈
    assert resized.width <= 1000
    assert resized.height <= 1000
    # 부동소수점 오차를 고려하여 비율이 거의 같은지 확인
    original_ratio = img.width / img.height
    resized_ratio = resized.width / resized.height
    assert abs(original_ratio - resized_ratio) < 0.01


def test_resize_image_no_change():
    """작은 이미지는 리사이즈 안 함 테스트"""
    img = Image.new("RGB", (500, 300), color="yellow")
    resized = resize_image(img, max_width=1000, max_height=1000)

    # 크기가 작으면 리사이즈 안 함
    assert resized.size == img.size


def test_validate_image_format():
    """이미지 형식 검증 테스트"""
    assert validate_image_format("test.jpg") is True
    assert validate_image_format("test.jpeg") is True
    assert validate_image_format("test.png") is True
    assert validate_image_format("test.PDF") is False
    assert validate_image_format("test.txt") is False

