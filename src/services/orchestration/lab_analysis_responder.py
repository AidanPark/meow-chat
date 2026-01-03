"""검사지 분석 응답기 (LabAnalysisResponder)

OCR로 추출된 검진 결과를 분석하고 설명합니다.
고품질 모델(gpt-4.1 등)을 사용합니다.
"""

from typing import TYPE_CHECKING, Iterator

from src.settings import settings
from src.services.llm.base import Message
from src.prompts import LAB_ANALYSIS_SYSTEM_PROMPT

from .models import OrchestrationContext

if TYPE_CHECKING:
    from src.services.llm.base import BaseLLMService



class LabAnalysisResponder:
    """검사지 분석 응답 생성기"""

    def __init__(self, llm_service: "BaseLLMService"):
        """
        Args:
            llm_service: LLM 서비스 인스턴스
        """
        self.llm_service = llm_service
        self.model = settings.openai_model_analysis

    def generate(self, context: OrchestrationContext) -> str:
        """응답 생성 (논-스트리밍)

        Args:
            context: 오케스트레이션 컨텍스트 (document_context 필수)

        Returns:
            응답 텍스트
        """
        messages = self._build_messages(context)

        response = self.llm_service.generate(
            messages=messages,
            model=self.model,
        )

        return response.content

    def stream_generate(self, context: OrchestrationContext) -> Iterator[str]:
        """응답 생성 (스트리밍)

        Args:
            context: 오케스트레이션 컨텍스트 (document_context 필수)

        Yields:
            응답 텍스트 조각
        """
        messages = self._build_messages(context)

        yield from self.llm_service.stream_generate(
            messages=messages,
            model=self.model,
        )

    def _build_messages(self, context: OrchestrationContext) -> list[Message]:
        """LLM 메시지 구성

        Args:
            context: 오케스트레이션 컨텍스트

        Returns:
            Message 리스트
        """
        messages = []

        # 1. 시스템 프롬프트
        messages.append(Message(role="system", content=LAB_ANALYSIS_SYSTEM_PROMPT))

        # 1.1 언어 미러링 보강(짧은 질문/혼합 언어에서도 일관성 강화)
        messages.append(
            Message(
                role="system",
                content=(
                    "답변은 항상 사용자가 마지막으로 입력한 언어로 작성하세요. "
                    "입력 언어가 불명확하면 직전 사용자 메시지의 언어를 따르고, 그것도 없으면 한국어로 답하세요."
                ),
            )
        )

        # 2. 문서 컨텍스트 (필수)
        if context.document_context:
            messages.append(Message(
                role="user",
                content=f"[검진 결과지 데이터]\n{context.document_context}"
            ))
            messages.append(Message(
                role="assistant",
                content="검진 결과지를 확인했습니다. 분석해 드릴게요."
            ))

        # 3. 최근 대화 히스토리
        for msg in context.chat_history:
            messages.append(Message(role=msg["role"], content=msg["content"]))

        # 4. 현재 사용자 입력
        messages.append(Message(role="user", content=context.user_input))

        return messages

