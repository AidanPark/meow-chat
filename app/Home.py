"""냥닥터 (Meow Chat) - 고양이 건강검진 OCR 챗봇

메인 Streamlit 애플리케이션
"""

import sys
from pathlib import Path

import streamlit as st
from PIL import Image

# src 모듈 임포트를 위한 경로 추가
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.services.chat.chat_service import ChatService
from src.services.llm.factory import get_llm_service
from src.services.ocr.factory import get_ocr_service
from src.settings import settings, validate_settings
from src.utils.images import load_image_from_bytes, resize_image
from src.utils.pdf import is_pdf, pdf_bytes_to_images

# 페이지 설정
st.set_page_config(
    page_title="냥닥터 🐱 - 고양이 건강검진 챗봇",
    page_icon="🐱",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_session_state():
    """세션 상태 초기화"""
    if "chat_service" not in st.session_state:
        ocr_service = get_ocr_service()
        llm_service = get_llm_service()
        st.session_state.chat_service = ChatService(ocr_service, llm_service)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "uploaded_image" not in st.session_state:
        st.session_state.uploaded_image = None


def main():
    """메인 애플리케이션"""
    init_session_state()

    # 사이드바
    with st.sidebar:
        st.title("🐱 냥닥터")
        st.markdown("고양이 건강검진 OCR 챗봇")
        st.divider()

        # 설정 정보
        st.subheader("⚙️ 설정")
        st.info(f"**OCR:** {settings.ocr_provider}")
        st.info(f"**LLM:** {settings.llm_provider}")

        # 설정 경고
        warnings = validate_settings()
        if warnings:
            st.warning("⚠️ 설정 확인 필요")
            for key, msg in warnings.items():
                st.caption(msg)

        st.divider()

        # 파일 업로드
        st.subheader("📄 검진 결과지 업로드")
        uploaded_file = st.file_uploader(
            "이미지 또는 PDF 파일을 선택하세요",
            type=["jpg", "jpeg", "png", "pdf", "webp"],
            help="고양이 건강검진 결과지를 업로드하세요",
        )

        if uploaded_file:
            if st.button("🔍 분석 시작", type="primary", use_container_width=True):
                with st.spinner("검진 결과를 분석하는 중입니다..."):
                    try:
                        # 파일 읽기
                        file_bytes = uploaded_file.read()

                        # PDF 또는 이미지 처리
                        if is_pdf(uploaded_file.name):
                            images = pdf_bytes_to_images(file_bytes, dpi=300)
                            st.session_state.uploaded_image = images[0]  # 첫 페이지 표시
                            analysis_result = st.session_state.chat_service.analyze_images(
                                images
                            )
                        else:
                            image = load_image_from_bytes(file_bytes)
                            image = resize_image(image, max_width=2048, max_height=2048)
                            st.session_state.uploaded_image = image
                            analysis_result = st.session_state.chat_service.analyze_image(
                                image
                            )

                        # 메시지 추가
                        st.session_state.messages.append(
                            {"role": "user", "content": "[검진 결과지 업로드]"}
                        )
                        st.session_state.messages.append(
                            {"role": "assistant", "content": analysis_result}
                        )

                        st.success("✅ 분석 완료!")
                        st.rerun()

                    except Exception as e:
                        st.error(f"❌ 오류 발생: {str(e)}")

        st.divider()

        # 대화 초기화
        if st.button("🔄 대화 초기화", use_container_width=True):
            st.session_state.chat_service.clear_history()
            st.session_state.messages = []
            st.session_state.uploaded_image = None
            st.rerun()

        st.divider()

        # 정보
        st.caption("💡 **주의사항**")
        st.caption("이 서비스는 참고용입니다.")
        st.caption("정확한 진단은 수의사와 상담하세요.")

    # 메인 영역
    st.title("🐱 냥닥터 - 고양이 건강검진 챗봇")
    st.markdown(
        "안녕하세요! 고양이 건강검진 결과지를 업로드하고 궁금한 점을 물어보세요."
    )

    # 업로드된 이미지 표시
    if st.session_state.uploaded_image:
        with st.expander("📷 업로드된 검진 결과지", expanded=False):
            st.image(st.session_state.uploaded_image, use_container_width=True)

    st.divider()

    # 채팅 메시지 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 사용자 입력
    if prompt := st.chat_input("궁금한 점을 물어보세요..."):
        # 사용자 메시지 추가
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # AI 응답 생성
        with st.chat_message("assistant"):
            with st.spinner("답변 생성 중..."):
                try:
                    response = st.session_state.chat_service.chat(prompt)
                    st.markdown(response)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response}
                    )
                except Exception as e:
                    error_msg = f"❌ 오류가 발생했습니다: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": error_msg}
                    )


if __name__ == "__main__":
    main()

