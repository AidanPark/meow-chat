"""애플리케이션 설정 관리"""

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# .env 파일 로드
load_dotenv()

# 프로젝트 루트 디렉토리
ROOT_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # OCR 설정
    ocr_provider: Literal["google", "easyocr", "paddle", "dummy"] = Field(
        default="easyocr", description="OCR 제공자 (google | easyocr | paddle | dummy)"
    )
    ocr_use_gpu: bool = Field(
        default=False, description="OCR GPU 사용 여부 (Paddle/EasyOCR)"
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

    # 모델 설정 (기본값 - 하위호환용)
    openai_model: str = Field(default="gpt-4o", description="OpenAI 기본 모델명 (하위호환)")
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022", description="Anthropic 기본 모델명"
    )

    # 용도별 모델 설정 (오케스트레이션용)
    openai_model_intent: str = Field(
        default="gpt-5-nano", description="의도분류용 모델 (빠르고 저렴한 모델 권장)"
    )
    openai_model_chat: str = Field(
        default="gpt-5-mini", description="스몰톡/일반대화용 모델"
    )
    openai_model_analysis: str = Field(
        default="gpt-4.1", description="검사지 분석용 모델 (고품질 모델 권장)"
    )
    openai_model_metadata: str = Field(
        default="gpt-4o-mini", description="메타데이터 추출용 모델 (빠르고 저렴한 모델 권장)"
    )

    # 검사지 추출 설정
    lab_extraction_use_llm_metadata: bool = Field(
        default=False, description="patient_name 추출 실패 시 LLM 폴백 사용"
    )

    # 앱 설정
    app_debug: bool = Field(default=False, description="디버그 모드")
    log_level: str = Field(default="INFO", description="로그 레벨")
    max_upload_size_mb: int = Field(default=10, description="최대 업로드 크기 (MB)")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


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

