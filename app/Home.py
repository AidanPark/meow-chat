"""냥닥터 (Meow Chat) - 고양이 건강검진 OCR 챗봇

메인 Streamlit 애플리케이션 - Step 5: 스몰톡 + 단기 메모리 + 의도분석 + OCR + 검사 분석
st.write_stream()을 사용한 스트리밍 채팅 인터페이스입니다.
이전 대화 히스토리를 모델에 전달하여 멀티턴 대화를 지원합니다.
사용자 입력에서 '검사 분석 요청' 의도를 감지하여 확인 메시지를 출력합니다.
검진 결과지 이미지를 업로드하면 OCR로 텍스트를 추출하고 구조화된 테이블로 표시합니다.
문서 컨텍스트를 기반으로 LLM이 맞춤형 건강 상담을 제공합니다.
"""

import sys
from pathlib import Path

import streamlit as st
import pandas as pd

# src 모듈 임포트를 위한 경로 추가
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.services.llm.base import Message
from src.services.llm.factory import get_llm_service
from src.services.ocr.factory import get_ocr_service
from src.services.lab_extraction import LabTableExtractor
from src.services.lab_extraction.line_preprocessor import LinePreprocessor
from src.settings import settings
from src.utils.images import load_image_from_bytes, resize_image
from src.utils.pdf import is_pdf, pdf_bytes_to_images

# 페이지 설정
st.set_page_config(
    page_title="냥닥터 🐱 - 고양이 건강검진 챗봇",
    page_icon="🐱",
    layout="centered",
    initial_sidebar_state="expanded",
)

# 단기 메모리 설정
MAX_HISTORY_TURNS = 20  # 최근 N개 메시지만 유지 (user+assistant 합쳐서)

# Step 3: 의도분석 키워드 설정
ANALYSIS_INTENT_KEYWORDS = [
    "분석", "해석", "검사결과", "건강검진", "혈액검사",
    "결과지", "검진", "수치", "정상범위", "이상",
    "검사", "진단", "판독", "리포트", "결과"
]


def init_session_state():
    """세션 상태 초기화"""
    if "llm_service" not in st.session_state:
        try:
            st.session_state.llm_service = get_llm_service()
            st.session_state.llm_error = None
        except Exception as e:
            st.session_state.llm_service = None
            st.session_state.llm_error = str(e)

    if "ocr_service" not in st.session_state:
        try:
            st.session_state.ocr_service = get_ocr_service()
            st.session_state.ocr_error = None
        except Exception as e:
            st.session_state.ocr_service = None
            st.session_state.ocr_error = str(e)

    if "line_preprocessor" not in st.session_state:
        try:
            st.session_state.line_preprocessor = LinePreprocessor()
        except Exception:
            st.session_state.line_preprocessor = None

    if "lab_extractor" not in st.session_state:
        try:
            st.session_state.lab_extractor = LabTableExtractor()
        except Exception:
            st.session_state.lab_extractor = None

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Step 3: 분석 모드 상태
    if "analysis_mode_pending" not in st.session_state:
        st.session_state.analysis_mode_pending = False

    # Step 4: OCR 결과 저장
    if "ocr_text" not in st.session_state:
        st.session_state.ocr_text = None

    if "ocr_structured" not in st.session_state:
        st.session_state.ocr_structured = None

    if "ocr_debug_output" not in st.session_state:
        st.session_state.ocr_debug_output = None

    if "uploaded_image" not in st.session_state:
        st.session_state.uploaded_image = None


def display_chat_history():
    """대화 히스토리 표시"""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def get_system_prompt() -> str:
    """시스템 프롬프트 반환 (일반 스몰톡용)"""
    return """당신은 친근하고 공감적인 고양이 건강 상담 도우미 '냥닥터'입니다.

기본 성격:
- 친근하고 따뜻한 톤으로 대화합니다
- 고양이와 반려동물에 대해 잘 알고 있습니다
- 사용자의 질문에 정성껏 답변합니다

중요한 안전 수칙:
- 직접적인 의료 진단이나 처방을 하지 않습니다
- 응급 상황이 의심되면 즉시 동물병원 방문을 권유합니다
- 불확실한 정보는 "확실하지 않다"고 명시합니다
- 모든 건강 관련 조언은 "참고용"임을 안내합니다

대화 스타일:
- 짧고 명확하게 답변합니다
- 필요시 이모지를 적절히 사용합니다
- 추가 질문을 통해 상황을 더 잘 이해하려 합니다"""


def get_analysis_system_prompt() -> str:
    """검사 결과 분석용 시스템 프롬프트 (Step 5)"""
    return """당신은 친근하고 공감적인 고양이 건강 상담 도우미 '냥닥터'입니다.
지금 사용자가 고양이의 건강검진 결과지를 업로드했고, 이에 대한 분석을 요청했습니다.

## 역할
- OCR로 추출된 검사 결과 데이터를 기반으로 **이해하기 쉬운 언어**로 설명합니다
- 각 검사 항목이 무엇을 의미하는지, 정상 범위와 비교해 어떤 상태인지 설명합니다
- 수치가 높거나 낮은 항목이 있다면 **무엇을 의미할 수 있는지** 일반적인 정보를 제공합니다

## 중요한 안전 수칙 (반드시 지켜주세요)
1. **절대로 직접 진단하지 마세요**: "~병입니다", "~질환이 있습니다" 같은 확정적 진단 금지
2. **절대로 처방하지 마세요**: 약물, 치료법, 용량 등을 권하지 않습니다
3. **응급 징후 시 즉시 병원 권유**: 위험해 보이는 수치가 있으면 "동물병원 방문을 권장합니다"
4. **불확실성 명시**: "~일 수 있습니다", "수의사와 상담이 필요합니다" 등으로 표현
5. **참고용임을 안내**: 마지막에 "이 정보는 참고용이며, 정확한 진단은 수의사와 상담하세요"

## 응답 형식 가이드
1. **전체 요약**: 검사 결과 전반에 대한 간단한 요약 (1-2문장)
2. **주요 항목 설명**: 정상 범위를 벗어난 항목이 있다면 먼저 설명
3. **일반적인 해석**: 해당 수치가 의미할 수 있는 것들
4. **권장 사항**: 추가 검사나 병원 방문이 필요한지
5. **안전 문구**: 참고용 정보임을 명시

## 대화 스타일
- 보호자가 이해하기 쉬운 언어로 설명합니다
- 필요시 이모지를 적절히 사용합니다
- 공감적이고 안심시키는 톤을 유지합니다"""


def detect_analysis_intent(user_input: str) -> bool:
    """사용자 입력에서 '검사 분석 요청' 의도를 감지

    Args:
        user_input: 사용자 입력 텍스트

    Returns:
        분석 의도가 감지되면 True
    """
    user_input_lower = user_input.lower()
    for keyword in ANALYSIS_INTENT_KEYWORDS:
        if keyword in user_input_lower:
            return True
    return False


def process_ocr_result(ocr_result) -> tuple:
    """OCR 결과를 처리하여 구조화된 데이터와 디버그 출력을 반환

    노트북의 Step 4 → Step 13 파이프라인을 따릅니다:
    1. OCR 결과 → LinePreprocessor로 라인 정렬
    2. 정렬된 라인 → LabTableExtractor로 구조화
    3. debug_step13으로 최종 출력 생성

    Args:
        ocr_result: OCRResultEnvelope 객체

    Returns:
        (structured_data: dict, debug_output: str, raw_text: str)
    """
    if not ocr_result or not ocr_result.data or not ocr_result.data.items:
        return None, None, ""

    # 원본 텍스트 추출
    all_texts = []
    for item in ocr_result.data.items:
        all_texts.extend(item.rec_texts)
    raw_text = "\n".join(all_texts)

    # LinePreprocessor와 LabTableExtractor가 없으면 텍스트만 반환
    if st.session_state.line_preprocessor is None or st.session_state.lab_extractor is None:
        return None, None, raw_text

    try:
        # Step 4: LinePreprocessor로 라인 정렬
        # OCR 결과의 첫 페이지(item)를 처리
        page = ocr_result.data.items[0]
        lined_data = st.session_state.line_preprocessor.extract_and_group_lines(page)

        if not lined_data:
            return None, None, raw_text

        # Step 5-13: LabTableExtractor로 구조화 추출
        doc_result, intermediates = st.session_state.lab_extractor.extract_from_lines(
            lined_data,
            return_intermediates=True
        )

        # debug_step13 출력 생성 (노트북 Step 13 형식)
        debug_output = st.session_state.lab_extractor.debug_step13(intermediates)

        return doc_result, debug_output, raw_text

    except Exception as e:
        st.warning(f"구조화 추출 중 오류: {str(e)}")
        return None, None, raw_text


def extract_text_from_ocr_result(ocr_result) -> str:
    """OCR 결과에서 텍스트 추출

    Args:
        ocr_result: OCRResultEnvelope 객체

    Returns:
        추출된 텍스트 (줄바꿈으로 연결)
    """
    if not ocr_result.data.items:
        return ""

    all_texts = []
    for item in ocr_result.data.items:
        all_texts.extend(item.rec_texts)

    return "\n".join(all_texts)


def display_structured_result(structured_data: dict, debug_output: str):
    """구조화된 검사 결과를 표시

    Args:
        structured_data: LabTableExtractor에서 반환된 구조화 데이터
        debug_output: debug_step13 출력 (노트북 Step 13 형식)
    """
    if debug_output:
        # 노트북 Step 13 형식 그대로 출력
        st.text(debug_output)
    elif structured_data:
        # 폴백: structured_data를 직접 표시
        st.json(structured_data)
    else:
        st.info("추출된 검사 항목이 없습니다.")


def handle_image_upload(uploaded_file):
    """이미지 업로드 처리 및 OCR 실행

    Args:
        uploaded_file: Streamlit UploadedFile 객체
    """
    if st.session_state.ocr_service is None:
        st.error("⚠️ OCR 서비스를 사용할 수 없습니다.")
        return False

    try:
        file_bytes = uploaded_file.read()

        # PDF 또는 이미지 처리
        if is_pdf(uploaded_file.name):
            images = pdf_bytes_to_images(file_bytes, dpi=300)
            st.session_state.uploaded_image = images[0]  # 첫 페이지 표시용

            # 첫 페이지만 OCR (Step 4 MVP)
            ocr_result = st.session_state.ocr_service.extract_text(images[0])
        else:
            image = load_image_from_bytes(file_bytes)
            image = resize_image(image, max_width=2048, max_height=2048)
            st.session_state.uploaded_image = image

            # OCR 실행
            ocr_result = st.session_state.ocr_service.extract_text(image)

        # OCR 결과 처리 (노트북 파이프라인)
        structured, debug_output, raw_text = process_ocr_result(ocr_result)
        st.session_state.ocr_structured = structured
        st.session_state.ocr_debug_output = debug_output
        st.session_state.ocr_text = raw_text

        return True
    except Exception as e:
        st.error(f"⚠️ 이미지 처리 중 오류: {str(e)}")
        return False


def build_messages_for_llm(user_input: str, include_document_context: bool = False) -> list[Message]:
    """LLM에 전달할 메시지 리스트 구성 (멀티턴 지원)

    Args:
        user_input: 현재 사용자 입력
        include_document_context: 문서 컨텍스트를 포함할지 여부 (Step 5)

    Returns:
        Message 객체 리스트 (system + 문서컨텍스트 + 최근 히스토리 + 현재 입력)
    """
    messages = []

    # 1. 시스템 프롬프트 (문서 분석 모드 vs 일반 스몰톡)
    if include_document_context and st.session_state.ocr_structured:
        messages.append(Message(role="system", content=get_analysis_system_prompt()))

        # 2. 문서 컨텍스트를 user 메시지로 추가 (Step 5)
        document_context = format_document_context()
        if document_context:
            messages.append(Message(
                role="user",
                content=f"[검진 결과지 데이터]\n{document_context}"
            ))
            messages.append(Message(
                role="assistant",
                content="검진 결과지를 확인했습니다. 분석해 드릴게요."
            ))
    else:
        messages.append(Message(role="system", content=get_system_prompt()))

    # 3. 최근 N개의 대화 히스토리 (토큰 제한을 위해)
    recent_history = st.session_state.messages[-MAX_HISTORY_TURNS:]
    for msg in recent_history:
        messages.append(Message(role=msg["role"], content=msg["content"]))

    # 4. 현재 사용자 입력
    messages.append(Message(role="user", content=user_input))

    return messages


def format_document_context() -> str:
    """OCR 구조화 데이터를 LLM 컨텍스트용 문자열로 포맷

    Returns:
        포맷된 문서 컨텍스트 문자열
    """
    doc = st.session_state.ocr_structured
    tests = doc.get("tests", []) if doc else []

    # 구조화 데이터에 tests가 없으면 원문 텍스트 사용
    if not tests:
        if st.session_state.ocr_text:
            return f"[OCR 원문]\n{st.session_state.ocr_text[:3000]}"
        return ""

    lines = []

    # 메타데이터
    if doc.get("hospital_name"):
        lines.append(f"병원: {doc['hospital_name']}")
    if doc.get("patient_name"):
        lines.append(f"환자: {doc['patient_name']}")
    if doc.get("inspection_date"):
        lines.append(f"검사일: {doc['inspection_date']}")

    # 검사 결과 테이블
    lines.append("\n검사 결과:")
    lines.append("| 검사항목 | 결과값 | 단위 | 정상범위(min-max) |")
    lines.append("|----------|--------|------|-------------------|")
    for test in tests:
        code = test.get("code", "")
        value = test.get("value", "-")
        unit = test.get("unit", "")
        ref_min = test.get("reference_min", "")
        ref_max = test.get("reference_max", "")
        ref_range = f"{ref_min}-{ref_max}" if ref_min or ref_max else "-"
        lines.append(f"| {code} | {value} | {unit} | {ref_range} |")

    return "\n".join(lines)


def handle_user_input(user_input: str):
    """사용자 입력 처리 및 스트리밍 응답 생성 (멀티턴 + 의도분석 + 문서분석)"""
    # 사용자 메시지 표시 및 저장
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Step 3 + Step 5: 분석 의도 감지
    if detect_analysis_intent(user_input):
        # Step 5: 문서가 업로드되어 있으면 바로 분석 응답 생성
        # ocr_structured에 tests가 있거나, ocr_text가 있으면 문서가 있는 것으로 판단
        has_document = (
            (st.session_state.ocr_structured and st.session_state.ocr_structured.get("tests"))
            or st.session_state.ocr_text
        )

        if has_document:
            # 문서 컨텍스트 포함하여 LLM 호출
            handle_analysis_response(user_input)
            return
        else:
            # 문서가 없으면 업로드 안내
            with st.chat_message("assistant"):
                confirm_msg = (
                    "🔍 **검사 결과 분석 의도가 감지되었습니다!**\n\n"
                    "검진 결과지를 분석해 드릴 수 있어요. "
                    "사이드바에서 결과지 이미지를 업로드해 주세요.\n\n"
                    "일반적인 건강 상담을 원하시면 그냥 질문해 주세요! 😊"
                )
                st.info(confirm_msg)
            st.session_state.messages.append({"role": "assistant", "content": confirm_msg})
            st.session_state.analysis_mode_pending = True
            return

    # 일반 스몰톡: LLM 서비스 확인
    if st.session_state.llm_service is None:
        with st.chat_message("assistant"):
            error_msg = "⚠️ LLM 서비스에 연결할 수 없습니다. API 키를 확인해주세요."
            if st.session_state.llm_error:
                error_msg += f"\n\n오류: {st.session_state.llm_error}"
            st.error(error_msg)
        st.session_state.messages.append({"role": "assistant", "content": error_msg})
        return

    # 일반 스몰톡: 어시스턴트 응답 생성 (st.write_stream 사용)
    with st.chat_message("assistant"):
        try:
            # 멀티턴: 이전 대화 히스토리를 포함한 메시지 구성
            # 문서가 있으면 컨텍스트에 포함 (일반 대화에서도 참조 가능)
            include_doc = bool(st.session_state.ocr_structured or st.session_state.ocr_text)
            llm_messages = build_messages_for_llm(user_input, include_document_context=include_doc)

            # 스트리밍 제너레이터 생성
            def stream_generator():
                for chunk in st.session_state.llm_service.stream_generate(
                    messages=llm_messages,
                    temperature=0.7,
                ):
                    yield chunk

            # st.write_stream()으로 스트리밍 출력
            full_response = st.write_stream(stream_generator())

        except Exception as e:
            error_msg = f"⚠️ 응답 생성 중 오류가 발생했습니다: {str(e)}"
            st.error(error_msg)
            full_response = error_msg

    # 스트리밍 완료 후 최종 응답을 히스토리에 저장
    st.session_state.messages.append({"role": "assistant", "content": full_response})

    # 히스토리가 너무 길어지면 오래된 것 제거 (토큰 절약)
    if len(st.session_state.messages) > MAX_HISTORY_TURNS * 2:
        st.session_state.messages = st.session_state.messages[-MAX_HISTORY_TURNS:]


def handle_analysis_response(user_input: str):
    """검사 결과 분석 응답 생성 (Step 5)

    Args:
        user_input: 사용자 입력 (분석 요청)
    """
    if st.session_state.llm_service is None:
        with st.chat_message("assistant"):
            error_msg = "⚠️ LLM 서비스에 연결할 수 없습니다. API 키를 확인해주세요."
            st.error(error_msg)
        st.session_state.messages.append({"role": "assistant", "content": error_msg})
        return

    with st.chat_message("assistant"):
        try:
            # 문서 컨텍스트를 포함한 메시지 구성
            llm_messages = build_messages_for_llm(user_input, include_document_context=True)

            # 스트리밍 제너레이터 생성
            def stream_generator():
                for chunk in st.session_state.llm_service.stream_generate(
                    messages=llm_messages,
                    temperature=0.7,
                ):
                    yield chunk

            # st.write_stream()으로 스트리밍 출력
            full_response = st.write_stream(stream_generator())

        except Exception as e:
            error_msg = f"⚠️ 분석 중 오류가 발생했습니다: {str(e)}"
            st.error(error_msg)
            full_response = error_msg

    # 스트리밍 완료 후 최종 응답을 히스토리에 저장
    st.session_state.messages.append({"role": "assistant", "content": full_response})


def main():
    """메인 애플리케이션"""
    init_session_state()

    # 헤더
    st.title("🐱 냥닥터")
    st.caption("고양이 건강 상담 도우미와 대화해보세요")

    # 사이드바 - 설정 및 컨트롤
    with st.sidebar:
        st.subheader("⚙️ 설정")
        st.info(f"**LLM:** {settings.llm_provider}")
        st.info(f"**OCR:** {settings.ocr_provider}")
        st.caption(f"대화 히스토리: 최근 {MAX_HISTORY_TURNS}개 유지")

        if st.session_state.llm_error:
            st.error(f"LLM 오류: {st.session_state.llm_error}")
        if st.session_state.ocr_error:
            st.error(f"OCR 오류: {st.session_state.ocr_error}")

        st.divider()

        # 대화 초기화 버튼
        if st.button("🗑️ 대화 초기화", use_container_width=True):
            st.session_state.messages = []
            st.session_state.analysis_mode_pending = False
            st.session_state.ocr_text = None
            st.session_state.ocr_structured = None
            st.session_state.ocr_debug_output = None
            st.session_state.uploaded_image = None
            st.rerun()

        # Step 4: 결과지 업로드
        st.divider()
        st.subheader("📄 검사 결과지")

        uploaded_file = st.file_uploader(
            "이미지 또는 PDF 업로드",
            type=["jpg", "jpeg", "png", "pdf", "webp"],
            help="고양이 건강검진 결과지를 업로드하세요",
        )

        if uploaded_file:
            with st.spinner("🔍 OCR 처리 중..."):
                if handle_image_upload(uploaded_file):
                    st.success("✅ OCR 완료!")

        # OCR 결과가 있으면 삭제 버튼 표시
        if st.session_state.ocr_text:
            if st.button("🗑️ 결과지 삭제", use_container_width=True):
                st.session_state.ocr_text = None
                st.session_state.ocr_structured = None
                st.session_state.ocr_debug_output = None
                st.session_state.uploaded_image = None
                st.rerun()

        st.divider()
        st.caption("Step 4 - OCR 화면")
        st.caption("이미지 업로드 → OCR → 결과 표시")

    # 업로드된 이미지가 있으면 메인 영역에 표시
    if st.session_state.uploaded_image:
        with st.expander("🖼️ 업로드된 이미지", expanded=False):
            st.image(st.session_state.uploaded_image, use_container_width=True)

    # OCR 구조화 결과 표시 (Step 13: 최종 JSON 형식)
    if st.session_state.ocr_debug_output or st.session_state.ocr_structured:
        with st.expander("🧾 검사 결과 분석 (Step 13)", expanded=True):
            display_structured_result(
                st.session_state.ocr_structured,
                st.session_state.ocr_debug_output
            )

    # OCR 원문 텍스트 (접힌 상태로)
    if st.session_state.ocr_text:
        with st.expander("📝 OCR 원문 보기", expanded=False):
            st.text_area(
                "추출된 텍스트",
                st.session_state.ocr_text,
                height=200,
                disabled=True
            )

    # 대화 히스토리 표시
    display_chat_history()

    # 채팅 입력
    if user_input := st.chat_input("메시지를 입력하세요..."):
        handle_user_input(user_input)


if __name__ == "__main__":
    main()
