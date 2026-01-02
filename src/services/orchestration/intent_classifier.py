"""의도 분류기 (IntentClassifier)

사용자 입력의 의도를 LLM으로 분류합니다.
빠른 응답을 위해 경량 모델(gpt-5-nano 등)을 사용합니다.
"""

import json
import re
from typing import TYPE_CHECKING

from src.settings import settings
from src.services.llm.base import Message

from .models import Intent, IntentType

if TYPE_CHECKING:
    from src.services.llm.base import BaseLLMService


# 의도 분류용 시스템 프롬프트
INTENT_CLASSIFICATION_PROMPT = """당신은 고양이 건강 상담 챗봇의 의도 분류기입니다.
사용자 입력을 분석하여 아래 의도 중 하나로 분류하세요.

## 의도 유형
1. **lab_analysis**: 검사지/검진 결과 분석 요청
   - 예: "이 검사 결과 분석해줘", "혈액검사 수치가 높은데", "결과지 해석해줘"
2. **health_question**: 건강 관련 일반 질문 (검사지 없이)
   - 예: "고양이가 밥을 안 먹어요", "구토를 자주 해요", "정상 체온이 몇 도예요?"
3. **emergency**: 응급 상황 (즉시 병원 권유 필요)
   - 예: "숨을 못 쉬어요", "경련을 해요", "피를 토해요", "의식이 없어요"
4. **upload_help**: 업로드 방법 문의
   - 예: "파일 어떻게 올려요?", "사진 첨부 방법", "결과지 어디서 업로드?"
5. **smalltalk**: 일반 대화, 인사, 잡담
   - 예: "안녕", "고마워", "넌 뭐야?", "오늘 날씨 좋다"
6. **other**: 위 어디에도 해당하지 않음

## 응답 형식 (반드시 JSON만 출력)
{"intent": "의도유형", "confidence": 0.0-1.0}

예시:
- 입력: "혈액검사 결과 좀 봐줘" → {"intent": "lab_analysis", "confidence": 0.95}
- 입력: "안녕하세요!" → {"intent": "smalltalk", "confidence": 0.99}
- 입력: "고양이가 경련을 해요 어떡해요" → {"intent": "emergency", "confidence": 0.98}
"""


class IntentClassifier:
    """LLM 기반 의도 분류기"""

    def __init__(self, llm_service: "BaseLLMService"):
        """
        Args:
            llm_service: LLM 서비스 인스턴스
        """
        self.llm_service = llm_service
        self.model = settings.openai_model_intent

    def classify(self, user_input: str, context: dict | None = None) -> Intent:
        """사용자 입력의 의도를 분류

        Args:
            user_input: 사용자 입력 텍스트
            context: 추가 컨텍스트 (선택, 예: 이전 대화 요약)

        Returns:
            Intent 객체
        """
        # 메시지 구성
        messages = [
            Message(role="system", content=INTENT_CLASSIFICATION_PROMPT),
            Message(role="user", content=user_input),
        ]

        try:
            # LLM 호출 (경량 모델 사용)
            # Note: gpt-5-nano 등 일부 모델은 temperature를 지원하지 않음
            response = self.llm_service.generate(
                messages=messages,
                model=self.model,
                max_tokens=100,  # 짧은 응답
            )

            # JSON 파싱
            intent = self._parse_response(response.content)
            intent.raw_response = response.content
            return intent

        except Exception as e:
            # 실패 시 폴백: 키워드 기반 분류
            return self._fallback_classify(user_input, error=str(e))

    def _parse_response(self, response_text: str) -> Intent:
        """LLM 응답을 Intent 객체로 파싱

        Args:
            response_text: LLM 응답 텍스트

        Returns:
            Intent 객체
        """
        try:
            # JSON 추출 (응답에 다른 텍스트가 섞여있을 수 있음)
            json_match = re.search(r'\{[^}]+\}', response_text)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response_text)

            intent_str = data.get("intent", "other").lower()
            confidence = float(data.get("confidence", 0.5))

            # IntentType 매핑
            intent_type = self._map_intent_type(intent_str)

            return Intent(
                intent_type=intent_type,
                confidence=confidence,
            )

        except (json.JSONDecodeError, KeyError, ValueError):
            # 파싱 실패 시 OTHER로 분류
            return Intent(
                intent_type=IntentType.OTHER,
                confidence=0.3,
                metadata={"parse_error": True},
            )

    def _map_intent_type(self, intent_str: str) -> IntentType:
        """문자열을 IntentType으로 매핑"""
        mapping = {
            "lab_analysis": IntentType.LAB_ANALYSIS,
            "health_question": IntentType.HEALTH_QUESTION,
            "emergency": IntentType.EMERGENCY,
            "upload_help": IntentType.UPLOAD_HELP,
            "smalltalk": IntentType.SMALLTALK,
            "other": IntentType.OTHER,
        }
        return mapping.get(intent_str, IntentType.OTHER)

    def _fallback_classify(self, user_input: str, error: str | None = None) -> Intent:
        """키워드 기반 폴백 분류 (LLM 실패 시)

        Args:
            user_input: 사용자 입력
            error: 에러 메시지 (디버깅용)

        Returns:
            Intent 객체
        """
        user_input_lower = user_input.lower()

        # 응급 키워드
        emergency_keywords = ["경련", "숨을 못", "호흡곤란", "의식", "피를 토", "쓰러", "발작"]
        if any(kw in user_input_lower for kw in emergency_keywords):
            return Intent(
                intent_type=IntentType.EMERGENCY,
                confidence=0.8,
                metadata={"fallback": True, "error": error},
            )

        # 검사 분석 키워드
        analysis_keywords = [
            "분석", "해석", "검사결과", "건강검진", "혈액검사",
            "결과지", "검진", "수치", "정상범위", "이상",
            "검사", "진단", "판독", "리포트", "결과"
        ]
        if any(kw in user_input_lower for kw in analysis_keywords):
            return Intent(
                intent_type=IntentType.LAB_ANALYSIS,
                confidence=0.7,
                metadata={"fallback": True, "error": error},
            )

        # 업로드 관련 키워드
        upload_keywords = ["업로드", "올리", "첨부", "파일", "사진"]
        if any(kw in user_input_lower for kw in upload_keywords):
            return Intent(
                intent_type=IntentType.UPLOAD_HELP,
                confidence=0.7,
                metadata={"fallback": True, "error": error},
            )

        # 건강 질문 키워드
        health_keywords = ["아파", "아프", "구토", "설사", "밥을 안", "식욕", "증상"]
        if any(kw in user_input_lower for kw in health_keywords):
            return Intent(
                intent_type=IntentType.HEALTH_QUESTION,
                confidence=0.6,
                metadata={"fallback": True, "error": error},
            )

        # 기본값: 스몰톡
        return Intent(
            intent_type=IntentType.SMALLTALK,
            confidence=0.5,
            metadata={"fallback": True, "error": error},
        )

