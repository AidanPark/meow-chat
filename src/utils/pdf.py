"""PDF 처리 유틸리티"""

from pathlib import Path

from pdf2image import convert_from_bytes, convert_from_path
from PIL import Image


def pdf_to_images(
    file_path: str | Path, dpi: int = 300, first_page: int | None = None, last_page: int | None = None
) -> list[Image.Image]:
    """PDF 파일을 이미지 리스트로 변환

    Args:
        file_path: PDF 파일 경로
        dpi: 해상도 (기본 300)
        first_page: 시작 페이지 (1부터 시작, None이면 첫 페이지)
        last_page: 끝 페이지 (None이면 마지막 페이지)

    Returns:
        이미지 리스트
    """
    return convert_from_path(
        file_path,
        dpi=dpi,
        first_page=first_page,
        last_page=last_page,
    )


def pdf_bytes_to_images(
    pdf_bytes: bytes, dpi: int = 300, first_page: int | None = None, last_page: int | None = None
) -> list[Image.Image]:
    """PDF 바이트 데이터를 이미지 리스트로 변환

    Args:
        pdf_bytes: PDF 바이트 데이터
        dpi: 해상도 (기본 300)
        first_page: 시작 페이지
        last_page: 끝 페이지

    Returns:
        이미지 리스트
    """
    return convert_from_bytes(
        pdf_bytes,
        dpi=dpi,
        first_page=first_page,
        last_page=last_page,
    )


def is_pdf(file_path: str | Path) -> bool:
    """PDF 파일인지 확인"""
    return Path(file_path).suffix.lower() == ".pdf"

