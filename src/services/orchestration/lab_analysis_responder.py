"""검사지 분석 응답기 (LabAnalysisResponder)

OCR로 추출된 검진 결과를 분석하고 설명합니다.
고품질 모델(gpt-4.1 등)을 사용합니다.
"""

from typing import TYPE_CHECKING, Iterator

from src.settings import settings
from src.services.llm.base import Message

from .models import OrchestrationContext

if TYPE_CHECKING:
    from src.services.llm.base import BaseLLMService


# 검사지 분석용 시스템 프롬프트
LAB_ANALYSIS_SYSTEM_PROMPT = """당신은 친근하고 공감적인 고양이 건강 상담 도우미 '냥닥터'입니다.
사용자가 고양이의 건강검진 결과지를 업로드했고, 이에 대한 분석을 요청했습니다.

## 역할
- OCR로 추출된 검사 결과 데이터를 기반으로 **이해하기 쉬운 언어**로 설명합니다
- 각 검사 항목이 무엇을 의미하는지, 정상 범위와 비교해 어떤 상태인지 설명합니다
- 수치가 높거나 낮은 항목이 있다면 **무엇을 의미할 수 있는지** 일반적인 정보를 제공합니다

수의 내과 전문의로서, 제공된 검사결과 표를 기반으로 안정적이고 재현 가능한 해석을 작성합니다.
반드시 아래 출력 형식을 지키세요.

## 출력 형식
1) **데이터프레임 표** (마크다운 표 허용): 컬럼 = [항목, 값, 단위, 참고범위, 정상여부, 방향, 중증도]
   - 정상여부: 정상 | 비정상 | 불명(범위 없음)
   - 방향: ↑(상) | ↓(하) | -
   - 중증도: 경도 | 중등도 | 중증 (필요 시)

2) **종합 임상 판단과 소견**:
   - 병태생리
   - 감별진단 후보
   - 권장 추가검사 및 관리
   - 주의사항 및 한계

## 판정 규칙
- 우선 리포트에 포함된 참고범위(reference_min/max 또는 low/high/reference_range)를 기준으로 정상/이상 판정
- 범위가 누락되면 '불명(범위 없음)'으로 표기하고 소견에서 출처 부족을 명시
- 단위가 의심되면 변환 후보만 제시하고, 원 단위를 유지하여 신중히 기술
- 응급/중증 임계값은 보수적으로 표시하되 과장 금지

## 중요한 안전 수칙 (반드시 지켜주세요)
1. **절대로 직접 진단하지 마세요**: "~병입니다", "~질환이 있습니다" 같은 확정적 진단 금지
2. **절대로 처방하지 마세요**: 약물, 치료법, 용량 등을 권하지 않습니다
3. **응급 징후 시 즉시 병원 권유**: 위험해 보이는 수치가 있으면 "동물병원 방문을 권장합니다"
4. **불확실성 명시**: "~일 수 있습니다", "수의사와 상담이 필요합니다" 등으로 표현
5. **참고용임을 안내**: 마지막에 "이 정보는 참고용이며, 정확한 진단은 수의사와 상담하세요"


## 대화 스타일
- 보호자가 이해하기 쉬운 언어로 설명합니다
- 필요시 이모지를 적절히 사용합니다 🐱
- 공감적이고 안심시키는 톤을 유지합니다
"""


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

