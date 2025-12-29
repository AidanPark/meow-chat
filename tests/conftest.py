"""테스트 픽스처 및 설정"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from PIL import Image

from src.services.chat.chat_service import ChatService
from src.services.llm.dummy_llm import DummyLLM
from src.services.ocr.dummy_ocr import DummyOCR

# 프로젝트 루트의 .env 파일 로드
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


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

