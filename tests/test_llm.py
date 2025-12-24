"""LLM 서비스 테스트"""

from src.services.llm.base import Message
from src.services.llm.dummy_llm import DummyLLM


def test_dummy_llm_generate(dummy_llm_service):
    """더미 LLM 응답 생성 테스트"""
    messages = [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="Hello!"),
    ]

    response = dummy_llm_service.generate(messages)

    assert response.content is not None
    assert len(response.content) > 0
    assert response.model == "dummy-model"
    assert response.usage is not None
    assert response.metadata["provider"] == "dummy"


def test_dummy_llm_chat(dummy_llm_service):
    """더미 LLM 간단한 채팅 테스트"""
    response = dummy_llm_service.chat("Tell me about cats", system_message="You are a vet.")

    assert response is not None
    assert len(response) > 0
    assert isinstance(response, str)

