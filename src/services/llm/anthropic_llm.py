"""Anthropic API LLM 구현"""

from anthropic import Anthropic

from src.settings import settings

from .base import BaseLLMService, LLMResponse, Message


class AnthropicLLM(BaseLLMService):
    """Anthropic API를 사용한 LLM 서비스"""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        """Anthropic 클라이언트 초기화

        Args:
            api_key: Anthropic API 키 (None이면 환경변수 사용)
            model: 모델명 (None이면 설정값 사용)
        """
        self.api_key = api_key or settings.anthropic_api_key
        self.model = model or settings.anthropic_model
        self.client = Anthropic(api_key=self.api_key)

    def generate(self, messages: list[Message], **kwargs) -> LLMResponse:
        """메시지를 기반으로 응답 생성

        Args:
            messages: 대화 메시지 리스트
            **kwargs: 추가 파라미터 (temperature, max_tokens 등)

        Returns:
            LLMResponse 객체
        """
        # system 메시지 분리
        system_message = None
        conversation_messages = []

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                conversation_messages.append({"role": msg.role, "content": msg.content})

        # API 호출
        response = self.client.messages.create(
            model=self.model,
            max_tokens=kwargs.pop("max_tokens", 4096),
            system=system_message,
            messages=conversation_messages,
            **kwargs,
        )

        # 응답 변환
        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            metadata={"provider": "anthropic", "stop_reason": response.stop_reason},
        )

