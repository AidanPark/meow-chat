"""라우터/오케스트레이터 (Router)

의도 분류 결과와 컨텍스트를 기반으로 적절한 Responder로 라우팅합니다.
"""

from typing import TYPE_CHECKING, Iterator, Callable

from .models import Intent, IntentType, OrchestrationContext
from .intent_classifier import IntentClassifier
from .chat_responder import ChatResponder
from .lab_analysis_responder import LabAnalysisResponder

if TYPE_CHECKING:
    from src.services.llm.base import BaseLLMService


class Router:
    """오케스트레이션 라우터

    의도분류 → 라우팅 → 응답생성 파이프라인을 관리합니다.
    """

    def __init__(self, llm_service: "BaseLLMService"):
        """
        Args:
            llm_service: LLM 서비스 인스턴스
        """
        self.llm_service = llm_service

        # 각 컴포넌트 초기화
        self.intent_classifier = IntentClassifier(llm_service)
        self.chat_responder = ChatResponder(llm_service)
        self.lab_analysis_responder = LabAnalysisResponder(llm_service)

    def classify_intent(self, user_input: str) -> Intent:
        """사용자 입력의 의도를 분류

        Args:
            user_input: 사용자 입력

        Returns:
            Intent 객체
        """
        return self.intent_classifier.classify(user_input)

    def route(
        self,
        context: OrchestrationContext,
    ) -> tuple[str, Callable[[], Iterator[str]]]:
        """컨텍스트를 기반으로 적절한 Responder로 라우팅

        Args:
            context: 오케스트레이션 컨텍스트

        Returns:
            (route_type, stream_generator_factory) 튜플
            - route_type: "chat", "analysis", "upload_guide", "emergency" 중 하나
            - stream_generator_factory: 스트리밍 응답 생성기를 반환하는 함수
        """
        intent = context.intent

        if intent is None:
            # 의도 분류가 안 되어 있으면 먼저 분류
            intent = self.classify_intent(context.user_input)
            context.intent = intent

        # 라우팅 결정
        route_type, stream_factory = self._decide_route(context)

        return route_type, stream_factory

    def _decide_route(
        self,
        context: OrchestrationContext,
    ) -> tuple[str, Callable[[], Iterator[str]]]:
        """라우팅 결정 로직

        Args:
            context: 오케스트레이션 컨텍스트

        Returns:
            (route_type, stream_generator_factory) 튜플
        """
        intent = context.intent
        intent_type = intent.intent_type

        # 1. 응급 상황 → 응급 대응 (ChatResponder with emergency flag)
        if intent_type == IntentType.EMERGENCY:
            return "emergency", lambda: self.chat_responder.stream_generate(
                context, is_emergency=True
            )

        # 2. 검사지 분석 요청
        if intent_type == IntentType.LAB_ANALYSIS:
            # 문서가 있으면 분석 수행
            if context.has_document:
                return "analysis", lambda: self.lab_analysis_responder.stream_generate(
                    context
                )
            # 문서가 없으면 업로드 안내
            else:
                return "upload_guide", lambda: iter([self._get_upload_guide_message()])

        # 3. 업로드 방법 문의
        if intent_type == IntentType.UPLOAD_HELP:
            return "upload_guide", lambda: iter([self._get_upload_help_message()])

        # 4. 일반 건강 질문 (문서 있으면 참조)
        if intent_type == IntentType.HEALTH_QUESTION:
            return "chat", lambda: self.chat_responder.stream_generate(context)

        # 5. 스몰톡 / 기타
        return "chat", lambda: self.chat_responder.stream_generate(context)

    def process(self, context: OrchestrationContext) -> Iterator[str]:
        """전체 오케스트레이션 파이프라인 실행 (스트리밍)

        Args:
            context: 오케스트레이션 컨텍스트

        Yields:
            응답 텍스트 조각
        """
        # 1. 의도 분류
        if context.intent is None:
            context.intent = self.classify_intent(context.user_input)

        # 2. 라우팅 및 응답 생성
        route_type, stream_factory = self.route(context)

        # 3. 스트리밍 응답 반환
        yield from stream_factory()

    def process_sync(self, context: OrchestrationContext) -> str:
        """전체 오케스트레이션 파이프라인 실행 (논-스트리밍)

        Args:
            context: 오케스트레이션 컨텍스트

        Returns:
            응답 텍스트
        """
        # 스트리밍 결과를 모아서 반환
        chunks = list(self.process(context))
        return "".join(chunks)

    def _get_upload_guide_message(self) -> str:
        """검사지 분석 요청 시 업로드 안내 메시지"""
        return (
            "🔍 **검사 결과 분석을 도와드릴게요!**\n\n"
            "검진 결과지를 분석하려면 먼저 이미지를 업로드해 주세요.\n\n"
            "**업로드 방법:**\n"
            "1. 아래 '📎 검진 결과지 첨부' 버튼을 클릭\n"
            "2. 검진 결과지 이미지(JPG, PNG) 또는 PDF 선택\n"
            "3. '🚀 Send' 버튼으로 전송\n\n"
            "일반적인 건강 상담을 원하시면 그냥 질문해 주세요! 😊"
        )

    def _get_upload_help_message(self) -> str:
        """업로드 방법 안내 메시지"""
        return (
            "📎 **파일 업로드 방법을 안내해 드릴게요!**\n\n"
            "1. 화면 아래쪽의 '📎 검진 결과지 첨부' 버튼을 클릭하세요\n"
            "2. 고양이 건강검진 결과지 이미지나 PDF를 선택하세요\n"
            "   - 지원 형식: JPG, JPEG, PNG, PDF, WEBP\n"
            "3. 질문을 입력하고 '🚀 Send' 버튼을 누르세요\n\n"
            "**팁:** 📷 사진은 밝고 선명하게 찍어주세요!\n"
            "글씨가 잘 보일수록 더 정확한 분석이 가능해요 🐱"
        )

    def get_route_info(self, context: OrchestrationContext) -> dict:
        """라우팅 정보 반환 (디버깅/로깅용)

        Args:
            context: 오케스트레이션 컨텍스트

        Returns:
            라우팅 정보 딕셔너리
        """
        if context.intent is None:
            context.intent = self.classify_intent(context.user_input)

        route_type, _ = self.route(context)

        return {
            "intent_type": context.intent.intent_type.value,
            "confidence": context.intent.confidence,
            "has_document": context.has_document,
            "route_type": route_type,
            "intent_model": self.intent_classifier.model,
            "chat_model": self.chat_responder.model,
            "analysis_model": self.lab_analysis_responder.model,
        }

