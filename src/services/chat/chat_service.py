"""채팅 서비스 - OCR과 LLM을 연결하는 오케스트레이션"""

from dataclasses import dataclass

from PIL import Image

from src.services.llm.base import BaseLLMService, Message
from src.services.llm.prompts import (
    SYSTEM_PROMPT,
    get_followup_prompt,
    get_ocr_analysis_prompt,
)
from src.services.ocr.base import BaseOCRService


@dataclass
class ChatMessage:
    """채팅 메시지"""

    role: str  # "user" | "assistant"
    content: str


class ChatService:
    """채팅 서비스 - OCR과 LLM을 통합 관리"""

    def __init__(self, ocr_service: BaseOCRService, llm_service: BaseLLMService):
        """ChatService 초기화

        Args:
            ocr_service: OCR 서비스 인스턴스
            llm_service: LLM 서비스 인스턴스
        """
        self.ocr_service = ocr_service
        self.llm_service = llm_service
        self.conversation_history: list[ChatMessage] = []
        self.ocr_text: str | None = None

    def analyze_image(self, image: Image.Image) -> str:
        """이미지를 OCR로 분석하고 LLM으로 해석

        Args:
            image: PIL Image 객체

        Returns:
            분석 결과 텍스트
        """
        # 1. OCR로 텍스트 추출
        ocr_result = self.ocr_service.extract_text(image)
        self.ocr_text = ocr_result.text

        # 2. LLM으로 분석
        analysis_prompt = get_ocr_analysis_prompt(self.ocr_text)
        messages = [
            Message(role="system", content=SYSTEM_PROMPT),
            Message(role="user", content=analysis_prompt),
        ]

        response = self.llm_service.generate(messages, temperature=0.7)

        # 3. 대화 히스토리에 추가
        self.conversation_history.append(
            ChatMessage(role="user", content="[검진 결과지 업로드]")
        )
        self.conversation_history.append(
            ChatMessage(role="assistant", content=response.content)
        )

        return response.content

    def analyze_images(self, images: list[Image.Image]) -> str:
        """여러 이미지를 OCR로 분석 (다중 페이지 지원)

        Args:
            images: PIL Image 객체 리스트

        Returns:
            분석 결과 텍스트
        """
        # 1. OCR로 모든 페이지 텍스트 추출
        ocr_results = self.ocr_service.extract_text_from_images(images)
        combined_text = "\n\n=== 다음 페이지 ===\n\n".join(
            [result.text for result in ocr_results]
        )
        self.ocr_text = combined_text

        # 2. LLM으로 분석
        analysis_prompt = get_ocr_analysis_prompt(combined_text)
        messages = [
            Message(role="system", content=SYSTEM_PROMPT),
            Message(role="user", content=analysis_prompt),
        ]

        response = self.llm_service.generate(messages, temperature=0.7)

        # 3. 대화 히스토리에 추가
        self.conversation_history.append(
            ChatMessage(role="user", content=f"[검진 결과지 업로드 - {len(images)}페이지]")
        )
        self.conversation_history.append(
            ChatMessage(role="assistant", content=response.content)
        )

        return response.content

    def chat(self, user_message: str) -> str:
        """사용자 질문에 대한 응답 생성

        Args:
            user_message: 사용자 메시지

        Returns:
            AI 응답 텍스트
        """
        # 대화 히스토리 구성
        conversation_text = "\n\n".join(
            [f"[{msg.role}]: {msg.content}" for msg in self.conversation_history[-5:]]
        )

        # OCR 텍스트가 있으면 컨텍스트에 포함
        if self.ocr_text:
            conversation_text = f"[검진 결과지 내용]\n{self.ocr_text[:500]}...\n\n{conversation_text}"

        # 프롬프트 생성
        prompt = get_followup_prompt(conversation_text, user_message)
        messages = [
            Message(role="system", content=SYSTEM_PROMPT),
            Message(role="user", content=prompt),
        ]

        # LLM 호출
        response = self.llm_service.generate(messages, temperature=0.7)

        # 대화 히스토리에 추가
        self.conversation_history.append(ChatMessage(role="user", content=user_message))
        self.conversation_history.append(
            ChatMessage(role="assistant", content=response.content)
        )

        return response.content

    def get_history(self) -> list[ChatMessage]:
        """대화 히스토리 반환"""
        return self.conversation_history

    def clear_history(self):
        """대화 히스토리 초기화"""
        self.conversation_history = []
        self.ocr_text = None

