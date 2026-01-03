"""스몰톡/일반 대화 응답기 (ChatResponder)

일반 대화, 건강 질문 등에 대한 응답을 생성합니다.
중간 품질의 모델(gpt-5-mini 등)을 사용합니다.
"""

from typing import TYPE_CHECKING, Iterator

from src.settings import settings
from src.services.llm.base import Message
from src.prompts import (
    CHAT_SYSTEM_PROMPT,
    EMERGENCY_SYSTEM_PROMPT,
)

from .models import OrchestrationContext

if TYPE_CHECKING:
    from src.services.llm.base import BaseLLMService



class ChatResponder:
    """스몰톡/일반 대화 응답 생성기"""

    def __init__(self, llm_service: "BaseLLMService"):
        """
        Args:
            llm_service: LLM 서비스 인스턴스
        """
        self.llm_service = llm_service
        self.model = settings.openai_model_chat

    def generate(
        self,
        context: OrchestrationContext,
        is_emergency: bool = False,
    ) -> str:
        """응답 생성 (논-스트리밍)

        Args:
            context: 오케스트레이션 컨텍스트
            is_emergency: 응급 상황 여부

        Returns:
            응답 텍스트
        """
        messages = self._build_messages(context, is_emergency)

        response = self.llm_service.generate(
            messages=messages,
            model=self.model,
        )

        return response.content

    def stream_generate(
        self,
        context: OrchestrationContext,
        is_emergency: bool = False,
    ) -> Iterator[str]:
        """응답 생성 (스트리밍)

        Args:
            context: 오케스트레이션 컨텍스트
            is_emergency: 응급 상황 여부

        Yields:
            응답 텍스트 조각
        """
        messages = self._build_messages(context, is_emergency)

        yield from self.llm_service.stream_generate(
            messages=messages,
            model=self.model,
        )

    def _build_messages(
        self,
        context: OrchestrationContext,
        is_emergency: bool = False,
    ) -> list[Message]:
        """LLM 메시지 구성

        Args:
            context: 오케스트레이션 컨텍스트
            is_emergency: 응급 상황 여부

        Returns:
            Message 리스트
        """
        messages = []

        # 1. 시스템 프롬프트
        system_prompt = EMERGENCY_SYSTEM_PROMPT if is_emergency else CHAT_SYSTEM_PROMPT
        messages.append(Message(role="system", content=system_prompt))

        # 1.1 언어 미러링 보강(짧은 입력/혼합 언어에서도 일관성 강화)
        messages.append(
            Message(
                role="system",
                content=(
                    "답변은 항상 사용자가 마지막으로 입력한 언어로 작성하세요. "
                    "입력 언어가 불명확하면 직전 사용자 메시지의 언어를 따르고, 그것도 없으면 한국어로 답하세요."
                ),
            )
        )

        # 2. 문서 컨텍스트가 있으면 포함 (일반 대화에서도 참조 가능)
        if context.has_document and context.document_context:
            messages.append(Message(
                role="user",
                content=f"[참고: 업로드된 검진 결과]\n{context.document_context}"
            ))
            messages.append(Message(
                role="assistant",
                content="네, 검진 결과를 참고하겠습니다."
            ))

        # 3. 최근 대화 히스토리
        for msg in context.chat_history:
            messages.append(Message(role=msg["role"], content=msg["content"]))

        # 4. 현재 사용자 입력
        messages.append(Message(role="user", content=context.user_input))

        return messages
