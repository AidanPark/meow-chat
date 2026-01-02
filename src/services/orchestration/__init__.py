"""오케스트레이션 레이어

의도분류 → 라우팅 → 응답생성 파이프라인을 관리합니다.

구성:
- IntentClassifier: 사용자 입력의 의도를 분류 (gpt-5-nano 등 경량 모델)
- ChatResponder: 스몰톡/일반 대화 응답 생성 (gpt-5-mini 등)
- LabAnalysisResponder: 검사지 분석 응답 생성 (gpt-4.1 등 고품질 모델)
- Router: 의도/문서유무/세션상태 기반으로 적절한 Responder로 라우팅
"""

from .models import Intent, IntentType, OrchestrationContext
from .intent_classifier import IntentClassifier
from .chat_responder import ChatResponder
from .lab_analysis_responder import LabAnalysisResponder
from .router import Router

__all__ = [
    "Intent",
    "IntentType",
    "OrchestrationContext",
    "IntentClassifier",
    "ChatResponder",
    "LabAnalysisResponder",
    "Router",
]

