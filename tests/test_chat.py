"""채팅 서비스 테스트"""

from src.services.chat.chat_service import ChatService


def test_chat_service_analyze_image(chat_service, sample_image):
    """채팅 서비스 이미지 분석 테스트"""
    result = chat_service.analyze_image(sample_image)

    assert result is not None
    assert len(result) > 0
    assert chat_service.ocr_text is not None
    assert len(chat_service.get_history()) == 2  # user upload + assistant response


def test_chat_service_chat(chat_service, sample_image):
    """채팅 서비스 대화 테스트"""
    # 먼저 이미지 분석
    chat_service.analyze_image(sample_image)

    # 후속 질문
    response = chat_service.chat("고양이의 건강 상태는 어떤가요?")

    assert response is not None
    assert len(response) > 0
    assert len(chat_service.get_history()) == 4  # 이전 2개 + 새로운 2개


def test_chat_service_clear_history(chat_service, sample_image):
    """채팅 서비스 히스토리 초기화 테스트"""
    chat_service.analyze_image(sample_image)
    chat_service.chat("질문")

    assert len(chat_service.get_history()) > 0

    chat_service.clear_history()

    assert len(chat_service.get_history()) == 0
    assert chat_service.ocr_text is None


def test_chat_service_analyze_multiple_images(chat_service, sample_image):
    """채팅 서비스 다중 이미지 분석 테스트"""
    images = [sample_image, sample_image]
    result = chat_service.analyze_images(images)

    assert result is not None
    assert len(result) > 0
    assert "다음 페이지" in chat_service.ocr_text

