"""이미지 처리 유틸리티"""

import io
from pathlib import Path

from PIL import Image


def load_image(file_path: str | Path) -> Image.Image:
    """이미지 파일 로드"""
    return Image.open(file_path)


def load_image_from_bytes(data: bytes) -> Image.Image:
    """바이트 데이터에서 이미지 로드"""
    return Image.open(io.BytesIO(data))


def image_to_bytes(image: Image.Image, format: str = "PNG") -> bytes:
    """이미지를 바이트로 변환"""
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    return buffer.getvalue()


def resize_image(
    image: Image.Image, max_width: int = 2048, max_height: int = 2048
) -> Image.Image:
    """이미지 리사이즈 (비율 유지)"""
    if image.width <= max_width and image.height <= max_height:
        return image

    ratio = min(max_width / image.width, max_height / image.height)
    new_size = (int(image.width * ratio), int(image.height * ratio))

    return image.resize(new_size, Image.Resampling.LANCZOS)


def validate_image_format(file_path: str | Path) -> bool:
    """지원되는 이미지 형식인지 확인"""
    supported_formats = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
    return Path(file_path).suffix.lower() in supported_formats

