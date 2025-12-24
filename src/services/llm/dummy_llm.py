"""더미 LLM 구현 (테스트용)"""

import time

from .base import BaseLLMService, LLMResponse, Message


class DummyLLM(BaseLLMService):
    """테스트용 더미 LLM 서비스"""

    def generate(self, messages: list[Message], **kwargs) -> LLMResponse:
        """더미 응답 생성

        Args:
            messages: 대화 메시지 리스트
            **kwargs: 추가 파라미터 (무시됨)

        Returns:
            LLMResponse 객체
        """
        # 마지막 사용자 메시지 추출
        user_message = ""
        for msg in reversed(messages):
            if msg.role == "user":
                user_message = msg.content
                break

        # 간단한 응답 생성
        if "ocr" in user_message.lower() or "결과" in user_message:
            response_text = """
안녕하세요! 🐱 냥닥터입니다.

업로드하신 검진 결과지를 분석했습니다.

**주요 소견:**
- 전반적인 건강 상태는 양호합니다
- 체중과 체온이 정상 범위 내에 있습니다
- 혈액 검사 수치도 모두 정상입니다

**권장 사항:**
1. 현재 상태를 잘 유지하고 계십니다
2. 정기적인 건강검진을 권장합니다
3. 수분 섭취를 충분히 하도록 해주세요

더 궁금하신 점이 있으시면 언제든 물어보세요! 😊
""".strip()
        else:
            response_text = f"""
안녕하세요! 🐱 냥닥터입니다.

질문하신 내용에 대해 답변드리겠습니다.

[더미 응답 모드 - 실제 LLM 대신 테스트용 응답입니다]

사용자 질문: {user_message[:100]}...

실제 환경에서는 OpenAI GPT-4 또는 Anthropic Claude가
전문적인 고양이 건강 상담을 제공합니다.

더 궁금하신 점이 있으시면 말씀해주세요! 😊
""".strip()

        # 응답 시뮬레이션을 위한 약간의 지연
        time.sleep(0.5)

        return LLMResponse(
            content=response_text,
            model="dummy-model",
            usage={"prompt_tokens": 100, "completion_tokens": 150, "total_tokens": 250},
            metadata={"provider": "dummy"},
        )

