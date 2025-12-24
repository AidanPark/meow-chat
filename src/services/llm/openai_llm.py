"""OpenAI API LLM 구현"""

from openai import OpenAI

from src.settings import settings

from .base import BaseLLMService, LLMResponse, Message


class OpenAILLM(BaseLLMService):
    """OpenAI API를 사용한 LLM 서비스"""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        """OpenAI 클라이언트 초기화

        Args:
            api_key: OpenAI API 키 (None이면 환경변수 사용)
            model: 모델명 (None이면 설정값 사용)
        """
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        self.client = OpenAI(api_key=self.api_key)

    def generate(self, messages: list[Message], **kwargs) -> LLMResponse:
        """메시지를 기반으로 응답 생성

        Args:
            messages: 대화 메시지 리스트
            **kwargs: 추가 파라미터 (temperature, max_tokens 등)

        Returns:
            LLMResponse 객체
        """
        # Message 객체를 OpenAI 형식으로 변환
        openai_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

        # API 호출
        response = self.client.chat.completions.create(
            model=self.model, messages=openai_messages, **kwargs
        )

        # 응답 변환
        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            metadata={"provider": "openai"},
        )

