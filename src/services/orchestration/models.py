"""오케스트레이션 데이터 모델"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IntentType(Enum):
    """사용자 의도 유형"""

    SMALLTALK = "smalltalk"  # 일반 대화, 인사, 잡담
    LAB_ANALYSIS = "lab_analysis"  # 검사지/검진 결과 분석 요청
    HEALTH_QUESTION = "health_question"  # 건강 관련 일반 질문 (검사지 없이)
    UPLOAD_HELP = "upload_help"  # 업로드 방법 문의
    EMERGENCY = "emergency"  # 응급 상황 (즉시 병원 권유)
    OTHER = "other"  # 기타/분류 불가


@dataclass
class Intent:
    """의도 분류 결과"""

    intent_type: IntentType
    confidence: float = 1.0  # 0.0 ~ 1.0
    raw_response: str | None = None  # LLM 원본 응답 (디버깅용)
    metadata: dict = field(default_factory=dict)

    @property
    def is_analysis_request(self) -> bool:
        """검사지 분석 요청인지 여부"""
        return self.intent_type == IntentType.LAB_ANALYSIS

    @property
    def requires_document(self) -> bool:
        """문서가 필요한 의도인지 여부"""
        return self.intent_type == IntentType.LAB_ANALYSIS

    @property
    def is_emergency(self) -> bool:
        """응급 상황인지 여부"""
        return self.intent_type == IntentType.EMERGENCY


@dataclass
class OrchestrationContext:
    """오케스트레이션 컨텍스트 (라우팅 결정에 필요한 정보)"""

    user_input: str
    has_document: bool = False  # OCR 결과가 있는지
    document_context: str | None = None  # 포맷된 문서 컨텍스트
    chat_history: list[dict] = field(default_factory=list)  # 이전 대화
    session_metadata: dict = field(default_factory=dict)  # 세션 상태 정보

    # 오케스트레이션 결과
    intent: "Intent | None" = None
    response_model: str | None = None  # 사용된 모델명
    response_text: str | None = None  # 최종 응답


@dataclass
class ResponderResult:
    """Responder 응답 결과"""

    content: str
    model: str
    is_streaming: bool = False
    metadata: dict = field(default_factory=dict)

