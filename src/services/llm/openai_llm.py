"""OpenAI API LLM 구현"""

from typing import Iterator

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
        """메시지를 기반으로 응답 생성 (동기, 논-스트리밍)

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

    def stream_generate(self, messages: list[Message], **kwargs) -> Iterator[str]:
        """메시지를 기반으로 응답 생성 (스트리밍)

        OpenAI Responses API 스트리밍을 사용하여 토큰 단위로 응답을 생성합니다.

        Args:
            messages: 대화 메시지 리스트
            **kwargs: 추가 파라미터

        Yields:
            응답 텍스트 조각(델타)
        """
        # Message 객체에서 input 구성 (Responses API 형식)
        # system 메시지는 instructions로, 나머지는 input으로 변환
        instructions = None
        input_messages = []

        for msg in messages:
            if msg.role == "system":
                instructions = msg.content
            else:
                input_messages.append({"role": msg.role, "content": msg.content})

        # input이 단일 문자열이면 그대로, 여러 메시지면 리스트로
        if len(input_messages) == 1 and input_messages[0]["role"] == "user":
            api_input = input_messages[0]["content"]
        else:
            api_input = input_messages

        # Responses API 스트리밍 호출
        stream_kwargs = {
            "model": self.model,
            "input": api_input,
        }
        if instructions:
            stream_kwargs["instructions"] = instructions

        # temperature 등 추가 파라미터 전달
        for key in ["temperature", "max_tokens", "max_output_tokens"]:
            if key in kwargs:
                # max_tokens -> max_output_tokens 변환 (Responses API 형식)
                if key == "max_tokens":
                    stream_kwargs["max_output_tokens"] = kwargs[key]
                else:
                    stream_kwargs[key] = kwargs[key]

        # 스트리밍 응답 처리
        with self.client.responses.stream(**stream_kwargs) as stream:
            for event in stream:
                # output_text.delta 이벤트에서 텍스트 조각 추출
                if hasattr(event, "type") and event.type == "response.output_text.delta":
                    if hasattr(event, "delta") and event.delta:
                        yield event.delta
