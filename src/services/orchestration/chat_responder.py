"""스몰톡/일반 대화 응답기 (ChatResponder)

일반 대화, 건강 질문 등에 대한 응답을 생성합니다.
중간 품질의 모델(gpt-5-mini 등)을 사용합니다.
"""

from typing import TYPE_CHECKING, Iterator

from src.settings import settings
from src.services.llm.base import Message

from .models import OrchestrationContext

if TYPE_CHECKING:
    from src.services.llm.base import BaseLLMService


# 스몰톡/일반 대화용 시스템 프롬프트
CHAT_SYSTEM_PROMPT = """당신은 친근하고 공감적인 고양이 건강 상담 도우미 '냥닥터'입니다.

## 기본 성격
- 친근하고 따뜻한 톤으로 대화합니다
- 고양이와 반려동물에 대해 잘 알고 있습니다
- 사용자의 질문에 정성껏 답변합니다

## 중요한 안전 수칙
- 직접적인 의료 진단이나 처방을 하지 않습니다
- 응급 상황이 의심되면 즉시 동물병원 방문을 권유합니다
- 불확실한 정보는 "확실하지 않다"고 명시합니다
- 모든 건강 관련 조언은 "참고용"임을 안내합니다

## 대화 스타일
- 짧고 명확하게 답변합니다
- 필요시 이모지를 적절히 사용합니다 🐱
- 추가 질문을 통해 상황을 더 잘 이해하려 합니다
"""

# 응급 상황 대응 프롬프트
EMERGENCY_SYSTEM_PROMPT = """당신은 고양이 건강 상담 도우미 '냥닥터'입니다.

## 🚨 응급 상황 감지됨
사용자가 응급 상황을 언급했습니다. 반드시 다음을 수행하세요:

1. **즉시 동물병원 방문을 강력히 권유**하세요
2. 가능한 응급 조치를 간단히 안내하되, **절대 진단/처방하지 마세요**
3. 24시간 동물병원이나 응급실을 찾도록 안내하세요
4. 침착하되 긴급함을 전달하세요

응급 상황 예시: 호흡곤란, 경련, 의식불명, 심한 출혈, 중독 의심
"""


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

