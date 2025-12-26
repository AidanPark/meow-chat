"""테스트 픽스처 및 헬퍼 함수

이 모듈은 테스트에서 공통으로 사용하는 픽스처와 헬퍼 함수를 제공합니다.
"""

from pathlib import Path

# 테스트 픽스처 디렉토리 경로
FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURES_IMAGES_DIR = FIXTURES_DIR / "images"


def get_fixture_image_path(filename: str) -> Path:
    """픽스처 이미지 파일 경로를 반환합니다.

    Args:
        filename: 이미지 파일명 (예: "sample_checkup.jpg")

    Returns:
        Path: 픽스처 이미지 파일의 절대 경로

    Example:
        >>> path = get_fixture_image_path("sample_checkup.jpg")
        >>> print(path)
        /path/to/tests/fixtures/images/sample_checkup.jpg
    """
    return FIXTURES_IMAGES_DIR / filename


def list_fixture_images() -> list[Path]:
    """픽스처 이미지 디렉토리의 모든 이미지 파일을 반환합니다.

    Returns:
        list[Path]: 이미지 파일 경로 리스트

    Example:
        >>> images = list_fixture_images()
        >>> for img in images:
        ...     print(img.name)
        sample_checkup.jpg
        my_test_image.png
    """
    if not FIXTURES_IMAGES_DIR.exists():
        return []

    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp"}
    return [
        f for f in FIXTURES_IMAGES_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in image_extensions
    ]

