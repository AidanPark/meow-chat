"""애플리케이션 설정 관리"""

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# .env 파일 로드
load_dotenv()

# 프로젝트 루트 디렉토리
ROOT_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # OCR 설정
    ocr_provider: Literal["google", "dummy"] = Field(
        default="google", description="OCR 제공자 (google | dummy)"
    )
    google_application_credentials: str | None = Field(
        default=None, description="Google Cloud 서비스 계정 JSON 경로"
    )

    # LLM 설정
    llm_provider: Literal["openai", "anthropic", "dummy"] = Field(
        default="openai", description="LLM 제공자 (openai | anthropic | dummy)"
    )
    openai_api_key: str | None = Field(default=None, description="OpenAI API 키")
    anthropic_api_key: str | None = Field(default=None, description="Anthropic API 키")

    # 모델 설정
    openai_model: str = Field(default="gpt-4o", description="OpenAI 모델명")
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022", description="Anthropic 모델명"
    )

    # 앱 설정
    app_debug: bool = Field(default=False, description="디버그 모드")
    log_level: str = Field(default="INFO", description="로그 레벨")
    max_upload_size_mb: int = Field(default=10, description="최대 업로드 크기 (MB)")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 전역 설정 인스턴스
settings = Settings()


def validate_settings() -> dict[str, str]:
    """설정 유효성 검사 및 경고 메시지 반환"""
    warnings = {}

    # OCR 설정 검증
    if settings.ocr_provider == "google":
        if not settings.google_application_credentials:
            warnings["ocr"] = (
                "Google Cloud Vision API 사용을 위해서는 "
                "GOOGLE_APPLICATION_CREDENTIALS 환경변수가 필요합니다."
            )
        elif not Path(settings.google_application_credentials).exists():
            warnings["ocr"] = (
                f"서비스 계정 파일을 찾을 수 없습니다: "
                f"{settings.google_application_credentials}"
            )

    # LLM 설정 검증
    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            warnings["llm"] = "OpenAI API 사용을 위해서는 OPENAI_API_KEY가 필요합니다."
    elif settings.llm_provider == "anthropic":
        if not settings.anthropic_api_key:
            warnings["llm"] = (
                "Anthropic API 사용을 위해서는 ANTHROPIC_API_KEY가 필요합니다."
            )

    return warnings

