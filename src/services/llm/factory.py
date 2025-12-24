"""LLM 서비스 팩토리"""

from src.settings import settings

from .anthropic_llm import AnthropicLLM
from .base import BaseLLMService
from .dummy_llm import DummyLLM
from .openai_llm import OpenAILLM


def get_llm_service() -> BaseLLMService:
    """설정에 따라 적절한 LLM 서비스 반환

    Returns:
        BaseLLMService 인스턴스
    """
    if settings.llm_provider == "openai":
        return OpenAILLM()
    elif settings.llm_provider == "anthropic":
        return AnthropicLLM()
    elif settings.llm_provider == "dummy":
        return DummyLLM()
    else:
        raise ValueError(f"지원하지 않는 LLM 제공자: {settings.llm_provider}")

