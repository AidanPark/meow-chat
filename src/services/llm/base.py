"""LLM 서비스 기본 인터페이스"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Message:
    """채팅 메시지"""

    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    """LLM 응답 데이터 클래스"""

    content: str
    model: str | None = None
    usage: dict | None = None
    metadata: dict | None = None


class BaseLLMService(ABC):
    """LLM 서비스 기본 추상 클래스"""

    @abstractmethod
    def generate(self, messages: list[Message], **kwargs) -> LLMResponse:
        """메시지를 기반으로 응답 생성

        Args:
            messages: 대화 메시지 리스트
            **kwargs: 추가 파라미터 (temperature, max_tokens 등)

        Returns:
            LLMResponse 객체
        """
        pass

    def chat(self, user_message: str, system_message: str | None = None, **kwargs) -> str:
        """간단한 채팅 인터페이스

        Args:
            user_message: 사용자 메시지
            system_message: 시스템 메시지 (선택)
            **kwargs: 추가 파라미터

        Returns:
            응답 텍스트
        """
        messages = []
        if system_message:
            messages.append(Message(role="system", content=system_message))
        messages.append(Message(role="user", content=user_message))

        response = self.generate(messages, **kwargs)
        return response.content

