"""오케스트레이션 레이어 테스트"""

import pytest
from unittest.mock import Mock

from src.services.orchestration import (
    Router,
    OrchestrationContext,
    IntentType,
    Intent,
    IntentClassifier,
    ChatResponder,
    LabAnalysisResponder,
)
from src.services.llm.base import LLMResponse


class TestIntentType:
    """IntentType Enum 테스트"""

    def test_intent_types_exist(self):
        """모든 의도 유형이 정의되어 있는지 확인"""
        assert IntentType.SMALLTALK.value == "smalltalk"
        assert IntentType.LAB_ANALYSIS.value == "lab_analysis"
        assert IntentType.HEALTH_QUESTION.value == "health_question"
        assert IntentType.UPLOAD_HELP.value == "upload_help"
        assert IntentType.EMERGENCY.value == "emergency"
        assert IntentType.OTHER.value == "other"


class TestIntent:
    """Intent 데이터클래스 테스트"""

    def test_intent_creation(self):
        """Intent 객체 생성"""
        intent = Intent(intent_type=IntentType.LAB_ANALYSIS, confidence=0.9)
        assert intent.intent_type == IntentType.LAB_ANALYSIS
        assert intent.confidence == 0.9

    def test_is_analysis_request(self):
        """분석 요청 여부 확인"""
        intent = Intent(intent_type=IntentType.LAB_ANALYSIS)
        assert intent.is_analysis_request is True

        intent2 = Intent(intent_type=IntentType.SMALLTALK)
        assert intent2.is_analysis_request is False

    def test_is_emergency(self):
        """응급 상황 여부 확인"""
        intent = Intent(intent_type=IntentType.EMERGENCY)
        assert intent.is_emergency is True

        intent2 = Intent(intent_type=IntentType.SMALLTALK)
        assert intent2.is_emergency is False


class TestOrchestrationContext:
    """OrchestrationContext 데이터클래스 테스트"""

    def test_context_creation(self):
        """컨텍스트 객체 생성"""
        context = OrchestrationContext(
            user_input="안녕하세요",
            has_document=False,
        )
        assert context.user_input == "안녕하세요"
        assert context.has_document is False
        assert context.document_context is None
        assert context.chat_history == []

    def test_context_with_document(self):
        """문서가 있는 컨텍스트"""
        context = OrchestrationContext(
            user_input="분석해줘",
            has_document=True,
            document_context="| WBC | 10.5 | K/L |",
        )
        assert context.has_document is True
        assert "WBC" in context.document_context


class TestIntentClassifier:
    """IntentClassifier 테스트"""

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM 서비스"""
        service = Mock()
        service.generate = Mock(return_value=LLMResponse(
            content='{"intent": "smalltalk", "confidence": 0.95}',
            model="gpt-4o-mini",
        ))
        return service

    def test_classify_smalltalk(self, mock_llm_service):
        """스몰톡 분류"""
        classifier = IntentClassifier(mock_llm_service)
        intent = classifier.classify("안녕하세요!")

        assert intent.intent_type == IntentType.SMALLTALK
        assert intent.confidence >= 0.9

    def test_classify_lab_analysis(self, mock_llm_service):
        """검사 분석 분류"""
        mock_llm_service.generate.return_value = LLMResponse(
            content='{"intent": "lab_analysis", "confidence": 0.92}',
            model="gpt-4o-mini",
        )
        classifier = IntentClassifier(mock_llm_service)
        intent = classifier.classify("혈액검사 결과 분석해줘")

        assert intent.intent_type == IntentType.LAB_ANALYSIS

    def test_fallback_on_llm_error(self, mock_llm_service):
        """LLM 오류 시 폴백 분류"""
        mock_llm_service.generate.side_effect = Exception("API 오류")
        classifier = IntentClassifier(mock_llm_service)

        # 응급 키워드 → 폴백으로 EMERGENCY
        intent = classifier.classify("고양이가 경련을 해요")
        assert intent.intent_type == IntentType.EMERGENCY
        assert intent.metadata.get("fallback") is True

    def test_fallback_analysis_keywords(self, mock_llm_service):
        """폴백: 분석 키워드"""
        mock_llm_service.generate.side_effect = Exception("API 오류")
        classifier = IntentClassifier(mock_llm_service)

        intent = classifier.classify("검사결과 봐주세요")
        assert intent.intent_type == IntentType.LAB_ANALYSIS


class TestChatResponder:
    """ChatResponder 테스트"""

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM 서비스"""
        service = Mock()
        service.stream_generate = Mock(return_value=iter(["안녕", "하세요", "!"]))
        return service

    def test_stream_generate(self, mock_llm_service):
        """스트리밍 응답 생성"""
        responder = ChatResponder(mock_llm_service)
        context = OrchestrationContext(user_input="안녕")

        chunks = list(responder.stream_generate(context))
        assert "".join(chunks) == "안녕하세요!"

    def test_build_messages_includes_language_mirroring_system_hint(self, mock_llm_service):
        """시스템 프롬프트 직후 언어 미러링 보강 system 메시지가 포함되는지 확인"""
        responder = ChatResponder(mock_llm_service)
        context = OrchestrationContext(user_input="hi")

        messages = responder._build_messages(context)

        assert messages[0].role == "system"
        assert messages[1].role == "system"
        assert "사용자가 마지막으로 입력한 언어" in messages[1].content


class TestLabAnalysisResponder:
    """LabAnalysisResponder 테스트"""

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM 서비스"""
        service = Mock()
        service.stream_generate = Mock(return_value=iter([
            "검사 결과를 ", "분석해 ", "드리겠습니다."
        ]))
        return service

    def test_stream_generate(self, mock_llm_service):
        """검사 분석 스트리밍 응답"""
        responder = LabAnalysisResponder(mock_llm_service)
        context = OrchestrationContext(
            user_input="분석해줘",
            has_document=True,
            document_context="| WBC | 10.5 |",
        )

        chunks = list(responder.stream_generate(context))
        assert "분석" in "".join(chunks)

    def test_build_messages_includes_language_mirroring_system_hint(self, mock_llm_service):
        """시스템 프롬프트 직후 언어 미러링 보강 system 메시지가 포함되는지 확인"""
        responder = LabAnalysisResponder(mock_llm_service)
        context = OrchestrationContext(
            user_input="hi",
            has_document=True,
            document_context="| WBC | 10.5 |",
        )

        messages = responder._build_messages(context)

        assert messages[0].role == "system"
        assert messages[1].role == "system"
        assert "사용자가 마지막으로 입력한 언어" in messages[1].content


class TestRouter:
    """Router 테스트"""

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM 서비스"""
        service = Mock()
        service.generate = Mock(return_value=LLMResponse(
            content='{"intent": "smalltalk", "confidence": 0.95}',
            model="gpt-4o-mini",
        ))
        service.stream_generate = Mock(return_value=iter(["응답", "입니다"]))
        return service

    def test_router_creation(self, mock_llm_service):
        """Router 생성"""
        router = Router(mock_llm_service)
        assert router.intent_classifier is not None
        assert router.chat_responder is not None
        assert router.lab_analysis_responder is not None

    def test_classify_intent(self, mock_llm_service):
        """의도 분류"""
        router = Router(mock_llm_service)
        intent = router.classify_intent("안녕")
        assert intent.intent_type == IntentType.SMALLTALK

    def test_route_smalltalk(self, mock_llm_service):
        """스몰톡 라우팅"""
        router = Router(mock_llm_service)
        context = OrchestrationContext(user_input="안녕")
        context.intent = Intent(intent_type=IntentType.SMALLTALK)

        route_type, stream_factory = router.route(context)
        assert route_type == "chat"

    def test_route_analysis_with_document(self, mock_llm_service):
        """문서가 있을 때 분석 라우팅"""
        router = Router(mock_llm_service)
        context = OrchestrationContext(
            user_input="분석해줘",
            has_document=True,
            document_context="| WBC | 10.5 |",
        )
        context.intent = Intent(intent_type=IntentType.LAB_ANALYSIS)

        route_type, stream_factory = router.route(context)
        assert route_type == "analysis"

    def test_route_analysis_without_document(self, mock_llm_service):
        """문서가 없을 때 업로드 안내"""
        router = Router(mock_llm_service)
        context = OrchestrationContext(
            user_input="분석해줘",
            has_document=False,
        )
        context.intent = Intent(intent_type=IntentType.LAB_ANALYSIS)

        route_type, stream_factory = router.route(context)
        assert route_type == "upload_guide"

    def test_route_emergency(self, mock_llm_service):
        """응급 상황 라우팅"""
        router = Router(mock_llm_service)
        context = OrchestrationContext(user_input="경련을 해요")
        context.intent = Intent(intent_type=IntentType.EMERGENCY)

        route_type, stream_factory = router.route(context)
        assert route_type == "emergency"

    def test_get_route_info(self, mock_llm_service):
        """라우팅 정보 조회"""
        router = Router(mock_llm_service)
        context = OrchestrationContext(user_input="안녕")

        info = router.get_route_info(context)
        assert "intent_type" in info
        assert "route_type" in info
        assert "intent_model" in info
        assert "chat_model" in info
        assert "analysis_model" in info

