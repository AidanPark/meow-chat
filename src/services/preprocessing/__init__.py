"""이미지 전처리 패키지
OCR 수행 전 이미지 품질 개선을 위한 전처리 기능을 제공합니다.
주요 모듈:
- image_preprocessor: 이미지 전처리 (회전 보정, 대비 조정, 샤프닝 등)
"""
from .image_preprocessor import (
    ImagePreprocessor,
    Settings,
    # 로드/저장
    open_with_exif,
    save_png_bytes,
    # 기본 변환
    flatten_transparency,
    normalize_mode,
    to_grayscale,
    # 크롭/리사이즈
    auto_crop_with_margin,
    upscale_min_resolution,
    downscale_target_long_edge,
    # 대비/샤프닝
    weak_autocontrast,
    apply_clahe,
    conservative_sharpen,
)
__all__ = [
    "ImagePreprocessor",
    "Settings",
    "open_with_exif",
    "save_png_bytes",
    "flatten_transparency",
    "normalize_mode",
    "to_grayscale",
    "auto_crop_with_margin",
    "upscale_min_resolution",
    "downscale_target_long_edge",
    "weak_autocontrast",
    "apply_clahe",
    "conservative_sharpen",
]
