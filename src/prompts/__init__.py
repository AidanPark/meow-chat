"""
Lab extraction prompts module.

이 패키지는 검사지 추출 및 챗봇 응답에 사용되는 LLM 프롬프트를 중앙 관리합니다.
"""

from .metadata_extraction import (
    PATIENT_NAME_SYSTEM_PROMPT,
    PATIENT_NAME_USER_TEMPLATE,
)

from .header_inference import (
    HEADER_INFERENCE_SYSTEM_PROMPT,
    HEADER_INFERENCE_USER_TEMPLATE,
)

from .chat import (
    CHAT_SYSTEM_PROMPT,
    EMERGENCY_SYSTEM_PROMPT,
)

from .lab_analysis import (
    LAB_ANALYSIS_SYSTEM_PROMPT,
)

from .intent_classification import (
    INTENT_CLASSIFICATION_SYSTEM_PROMPT,
)

__all__ = [
    # 메타데이터 추출
    "PATIENT_NAME_SYSTEM_PROMPT",
    "PATIENT_NAME_USER_TEMPLATE",
    # 헤더 추론
    "HEADER_INFERENCE_SYSTEM_PROMPT",
    "HEADER_INFERENCE_USER_TEMPLATE",
    # 스몰톡/일반 대화
    "CHAT_SYSTEM_PROMPT",
    "EMERGENCY_SYSTEM_PROMPT",
    # 검사지 분석
    "LAB_ANALYSIS_SYSTEM_PROMPT",
    # 의도 분류
    "INTENT_CLASSIFICATION_SYSTEM_PROMPT",
]

