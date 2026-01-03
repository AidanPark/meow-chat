"""냥닥터 (Meow Chat) - 고양이 건강검진 OCR 챗봇

메인 Streamlit 애플리케이션 - Step 4.5(A): form 기반 단일 Send 플로우
- 파일 업로드 + 질문 입력 → Send 한 번으로 OCR → 답변 생성
- 채팅 히스토리 누적, 세션 상태 관리
- 에러/가이드 UX 포함
"""

import hashlib
import sys
from pathlib import Path

import streamlit as st

# src 모듈 임포트를 위한 경로 추가
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.services.llm.base import Message
from src.services.llm.factory import get_llm_service
from src.services.ocr.factory import get_ocr_service
from src.services.lab_extraction import LabTableExtractor
from src.services.lab_extraction.line_preprocessor import LinePreprocessor
from src.services.orchestration import Router, OrchestrationContext
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

    # 오케스트레이션 Router 초기화
    if "router" not in st.session_state:
        if st.session_state.llm_service:
            st.session_state.router = Router(st.session_state.llm_service)
        else:
            st.session_state.router = None

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

    if "uploaded_images" not in st.session_state:
        st.session_state.uploaded_images = []

    if "page_metadata" not in st.session_state:
        st.session_state.page_metadata = []

    # Step 4.5: 파일 캐싱용 키 및 정보 (캐시 키 = file_hash:provider)
    if "last_ocr_cache_key" not in st.session_state:
        st.session_state.last_ocr_cache_key = None

    if "last_file_name" not in st.session_state:
        st.session_state.last_file_name = None


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
    print(f"[DEBUG] process_ocr_result: ocr_result={ocr_result}")
    if not ocr_result or not ocr_result.data or not ocr_result.data.items:
        print("[DEBUG] OCR 결과가 비어있음")
        return None, None, ""

    # 원본 텍스트 추출
    all_texts = []
    for item in ocr_result.data.items:
        all_texts.extend(item.rec_texts)
    raw_text = "\n".join(all_texts)
    print(f"[DEBUG] 추출된 텍스트 라인 수: {len(all_texts)}")

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
    """구조화된 검사 결과를 표시 (노트북 스타일: 헤더 + 테이블)

    Args:
        structured_data: LabTableExtractor에서 반환된 구조화 데이터
        debug_output: debug_step13 출력 (노트북 Step 13 형식)
    """
    if not structured_data and not debug_output:
        st.info("추출된 검사 항목이 없습니다.")
        return

    # 노트북 스타일: 헤더 정보 + 테이블 출력
    if structured_data:
        tests = structured_data.get('tests', [])

        # 헤더 정보 출력
        lines = []
        lines.append(f"🏥 hospital_name    : {structured_data.get('hospital_name') or '(None)'}")
        lines.append(f"👤 client_name      : {structured_data.get('client_name') or '(None)'}")
        lines.append(f"🐾 patient_name     : {structured_data.get('patient_name') or '(None)'}")
        lines.append(f"🗓  inspection_date : {structured_data.get('inspection_date') or '(None)'}")
        lines.append(f"📊 tests count      : {len(tests)}")
        lines.append("")

        # 테이블 출력
        if tests:
            lines.append("code         value  unit     reference_min  reference_max")
            lines.append("------------+-------+---------+---------------+--------------")
            for t in tests:
                code = (t.get('code') or 'UNKNOWN')[:12].ljust(12)
                value = str(t.get('value') or '')[:5].rjust(5)
                unit = (t.get('unit') or 'UNKNOWN')[:7].ljust(7)
                ref_min = str(t.get('reference_min') or 'UNKNOWN')[:13].rjust(13)
                ref_max = str(t.get('reference_max') or 'UNKNOWN')[:13].rjust(13)
                lines.append(f"{code} {value}  {unit}  {ref_min}  {ref_max}")

        st.text("\n".join(lines))

    # 디버그 출력 (있으면 추가 표시)
    if debug_output:
        with st.expander("🔍 상세 디버그 정보", expanded=False):
            st.text(debug_output)


def compute_file_hash(file_bytes: bytes) -> str:
    """파일 bytes의 SHA256 해시 계산

    Args:
        file_bytes: 파일 바이트 데이터

    Returns:
        SHA256 해시 문자열
    """
    return hashlib.sha256(file_bytes).hexdigest()


def compute_ocr_cache_key(file_bytes: bytes) -> str:
    """OCR 캐시 키 생성 (파일해시 + provider)

    Args:
        file_bytes: 파일 바이트 데이터

    Returns:
        캐시 키 문자열 (file_hash:provider 형태)
    """
    file_hash = compute_file_hash(file_bytes)
    provider = settings.ocr_provider
    return f"{file_hash}:{provider}"


def handle_image_upload(uploaded_file, force_rerun: bool = False, source: str = "file") -> tuple[bool, str, bool]:
    """이미지 업로드 처리 및 OCR 실행 (캐싱 지원)

    Args:
        uploaded_file: Streamlit UploadedFile 객체 또는 카메라 입력
        force_rerun: 캐시를 무시하고 재실행할지 여부
        source: 입력 소스 ("file" 또는 "camera")

    Returns:
        (success: bool, message: str, cache_hit: bool)
    """
    if st.session_state.ocr_service is None:
        return False, "⚠️ OCR 서비스를 사용할 수 없습니다.", False

    try:
        # 카메라 입력과 파일 업로드 모두 .read() 또는 .getvalue() 지원
        if hasattr(uploaded_file, "read"):
            file_bytes = uploaded_file.read()
        elif hasattr(uploaded_file, "getvalue"):
            file_bytes = uploaded_file.getvalue()
        else:
            return False, "⚠️ 지원하지 않는 입력 형식입니다.", False

        cache_key = compute_ocr_cache_key(file_bytes)

        # 캐싱: 동일 파일+provider이면 OCR 건너뛰기 (force_rerun이 아닐 때)
        if not force_rerun and cache_key == st.session_state.last_ocr_cache_key:
            return True, "✅ 캐시 사용: 이전 OCR 결과를 재사용합니다.", True

        # 파일명 추출 (카메라 입력은 name이 없을 수 있음)
        file_name = getattr(uploaded_file, "name", None)
        if file_name is None:
            file_name = f"camera_{source}.jpg"  # 카메라 촬영 기본 이름

        # PDF 또는 이미지 처리
        if is_pdf(file_name):
            images = pdf_bytes_to_images(file_bytes, dpi=300)
            st.session_state.uploaded_image = images[0]  # 첫 페이지 표시용
            print(f"[DEBUG] PDF 변환: 첫 페이지 크기={images[0].size}, 모드={images[0].mode}")

            # 첫 페이지만 OCR (Step 4 MVP)
            ocr_result = st.session_state.ocr_service.extract_text(images[0])
        else:
            image = load_image_from_bytes(file_bytes)
            image = resize_image(image, max_width=2048, max_height=2048)
            st.session_state.uploaded_image = image
            print(f"[DEBUG] 이미지 로드: 크기={image.size}, 모드={image.mode}")

            # OCR 실행
            ocr_result = st.session_state.ocr_service.extract_text(image)

        # OCR 결과 처리 (노트북 파이프라인)
        structured, debug_output, raw_text = process_ocr_result(ocr_result)
        st.session_state.ocr_structured = structured
        st.session_state.ocr_debug_output = debug_output
        st.session_state.ocr_text = raw_text

        # 캐싱용 정보 저장 (cache_key = file_hash:provider)
        st.session_state.last_ocr_cache_key = cache_key
        st.session_state.last_file_name = file_name

        # OCR 품질 체크
        if not raw_text or len(raw_text.strip()) < 20:
            return True, "⚠️ OCR 결과가 부족합니다. 이미지가 흐리거나 잘렸을 수 있어요.", False

        return True, "✅ OCR 완료!", False
    except Exception as e:
        return False, f"⚠️ 이미지 처리 중 오류: {str(e)}", False


def handle_multi_file_upload(
    input_files: list,
    max_pdf_pages: int = 10,
    status_callback=None
) -> tuple[bool, str, int]:
    """멀티파일 업로드 처리 및 OCR 실행 + 결과 병합

    Args:
        input_files: [{"file": UploadedFile, "source": str, "name": str}, ...]
        max_pdf_pages: PDF 최대 페이지 수 (임시 상한)
        status_callback: 진행 상황 콜백 (msg: str) -> None

    Returns:
        (success: bool, message: str, processed_page_count: int)
    """
    if st.session_state.ocr_service is None:
        return False, "⚠️ OCR 서비스를 사용할 수 없습니다.", 0

    def log(msg):
        if status_callback:
            status_callback(msg)

    try:
        from src.services.lab_extraction import LabReportExtractor

        # 페이지별 이미지 리스트 생성 (파일/페이지 순서 유지)
        page_images = []  # [(file_name, page_idx, total_pages, PIL.Image), ...]
        all_file_bytes = []  # 캐시 키 계산용

        for item in input_files:
            file_obj = item["file"]
            file_name = item["name"]

            # bytes 추출
            if hasattr(file_obj, "read"):
                file_bytes = file_obj.read()
            elif hasattr(file_obj, "getvalue"):
                file_bytes = file_obj.getvalue()
            else:
                continue

            all_file_bytes.append(file_bytes)

            # PDF vs 이미지 분기
            if is_pdf(file_name):
                images = pdf_bytes_to_images(file_bytes, dpi=300)
                total_pages = len(images)

                # 페이지 상한 적용
                if total_pages > max_pdf_pages:
                    log(f"⚠️ {file_name}: {total_pages}페이지 중 처음 {max_pdf_pages}페이지만 처리")
                    images = images[:max_pdf_pages]

                for idx, img in enumerate(images):
                    page_images.append((file_name, idx + 1, min(total_pages, max_pdf_pages), img))
            else:
                # 단일 이미지
                image = load_image_from_bytes(file_bytes)
                image = resize_image(image, max_width=2048, max_height=2048)
                page_images.append((file_name, 1, 1, image))

        if not page_images:
            return False, "⚠️ 처리할 이미지가 없습니다.", 0

        # 캐시 키 계산 (문서 묶음 단위, 순서 포함)
        combined_hash = hashlib.sha256()
        for fb in all_file_bytes:
            combined_hash.update(fb)
        cache_key = f"{combined_hash.hexdigest()}:{settings.ocr_provider}"

        # 캐싱 체크
        if cache_key == st.session_state.last_ocr_cache_key:
            return True, f"⚡ 캐시 사용: 이전 결과 재사용 ({len(page_images)}페이지)", len(page_images)

        # 페이지별 OCR 실행 및 extraction 수집
        extractions = []
        raw_texts = []
        all_images = []  # 모든 페이지 이미지 저장 (프리뷰용)
        page_metadata = []  # 각 페이지 메타데이터

        for i, (fname, page_idx, total_pages, img) in enumerate(page_images):
            all_images.append(img)
            page_metadata.append({
                "file_name": fname,
                "page_idx": page_idx,
                "total_pages": total_pages,
            })

            log(f"   📄 [{i+1}/{len(page_images)}] {fname} (p{page_idx}/{total_pages}) OCR 중...")

            # OCR 실행
            ocr_result = st.session_state.ocr_service.extract_text(img)

            # 구조화 추출
            structured, debug_output, raw_text = process_ocr_result(ocr_result)

            # 파일/페이지 경계 구분자 추가
            separator = f"\n--- file:{fname} page:{page_idx}/{total_pages} ---\n"
            raw_texts.append(separator + (raw_text or ""))

            if structured:
                # extraction에 페이지 메타 추가
                structured["_page_meta"] = {
                    "file_name": fname,
                    "page_idx": page_idx,
                    "total_pages": total_pages,
                }
                extractions.append(structured)

        # 병합 (LabReportExtractor 사용)
        merged_structured = None
        merged_debug = None

        if extractions:
            try:
                extractor = LabReportExtractor.create_with_deps()
                merge_result = extractor.merge_extractions(extractions)

                # 병합 결과에서 첫 문서 추출 (merged는 리스트)
                merged_list = merge_result.data.merged if hasattr(merge_result.data, 'merged') else []
                if merged_list:
                    merged_structured = merged_list[0]  # 첫 번째 병합 문서

                    # 디버그 출력 생성
                    if st.session_state.lab_extractor:
                        merged_debug = st.session_state.lab_extractor.debug_step13(merged_structured)
            except Exception as e:
                log(f"⚠️ 병합 중 오류 (개별 결과 사용): {e}")
                # 병합 실패 시 첫 번째 extraction 사용
                if extractions:
                    merged_structured = extractions[0]

        # 세션에 저장
        st.session_state.uploaded_image = all_images[0] if all_images else None  # 첫 이미지 (하위 호환)
        st.session_state.uploaded_images = all_images  # 모든 이미지
        st.session_state.page_metadata = page_metadata  # 페이지 메타데이터
        st.session_state.ocr_text = "\n".join(raw_texts)
        st.session_state.ocr_structured = merged_structured
        st.session_state.ocr_debug_output = merged_debug
        st.session_state.last_ocr_cache_key = cache_key
        st.session_state.last_file_name = f"{len(input_files)}개 파일 ({len(page_images)}페이지)"

        return True, f"✅ OCR 완료! ({len(page_images)}페이지 처리, 병합됨)", len(page_images)

    except Exception as e:
        return False, f"⚠️ 멀티파일 처리 중 오류: {str(e)}", 0


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
    """사용자 입력 처리 및 스트리밍 응답 생성 (오케스트레이션 기반)

    오케스트레이션 파이프라인:
    1. IntentClassifier로 의도 분류 (gpt-5-nano 등 경량 모델)
    2. Router가 의도/문서유무/세션상태 기반으로 라우팅 결정
    3. 적절한 Responder가 응답 생성 (스몰톡=gpt-5-mini, 분석=gpt-4.1)
    """
    # 사용자 메시지 표시 및 저장
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Router 확인
    if st.session_state.router is None:
        with st.chat_message("assistant"):
            error_msg = "⚠️ LLM 서비스에 연결할 수 없습니다. API 키를 확인해주세요."
            if st.session_state.llm_error:
                error_msg += f"\n\n오류: {st.session_state.llm_error}"
            st.error(error_msg)
        st.session_state.messages.append({"role": "assistant", "content": error_msg})
        return

    # 오케스트레이션 컨텍스트 구성
    has_document = (
        (st.session_state.ocr_structured and st.session_state.ocr_structured.get("tests"))
        or st.session_state.ocr_text
    )

    context = OrchestrationContext(
        user_input=user_input,
        has_document=has_document,
        document_context=format_document_context() if has_document else None,
        chat_history=st.session_state.messages[-MAX_HISTORY_TURNS:],
    )

    # 1단계: 의도 분류 (경량 모델로 빠르게)
    with st.status("🤔 3/4 의도 분석 중...", expanded=False) as intent_status:
        intent = st.session_state.router.classify_intent(user_input)
        context.intent = intent
        intent_status.update(label=f"✅ 의도분류: {intent.intent_type.value}", state="complete")

    # 디버그: 의도 분류 결과 (사이드바에 표시)
    if settings.app_debug:
        route_info = st.session_state.router.get_route_info(context)
        st.sidebar.json(route_info)

    # 2단계: 라우팅 및 응답 생성
    route_type, stream_factory = st.session_state.router.route(context)

    # 3단계: 라우트 타입에 따른 처리
    if route_type == "analysis":
        # 검사지 분석 모드: 추가 UI 표시
        handle_analysis_response_with_context(context, stream_factory)
    elif route_type == "upload_guide":
        # 업로드 안내 (스트리밍 아님)
        with st.chat_message("assistant"):
            guide_message = next(iter(stream_factory()))
            st.info(guide_message)
        st.session_state.messages.append({"role": "assistant", "content": guide_message})
        st.session_state.analysis_mode_pending = True
    else:
        # 일반 대화/응급 상황
        with st.chat_message("assistant"):
            try:
                full_response = st.write_stream(stream_factory())
            except Exception as e:
                error_msg = f"⚠️ 응답 생성 중 오류가 발생했습니다: {str(e)}"
                st.error(error_msg)
                full_response = error_msg

        st.session_state.messages.append({"role": "assistant", "content": full_response})

    # 히스토리 관리 (토큰 절약)
    if len(st.session_state.messages) > MAX_HISTORY_TURNS * 2:
        st.session_state.messages = st.session_state.messages[-MAX_HISTORY_TURNS:]


def handle_analysis_response_with_context(context: OrchestrationContext, stream_factory):
    """검사 결과 분석 응답 생성 (오케스트레이션 버전)

    Args:
        context: 오케스트레이션 컨텍스트
        stream_factory: 스트리밍 응답 생성기 팩토리
    """
    with st.chat_message("assistant"):
        # 1. 업로드된 이미지 표시 (모든 이미지)
        if st.session_state.uploaded_images:
            st.subheader(f"📷 분석 이미지 ({len(st.session_state.uploaded_images)}장)")
            for i, img in enumerate(st.session_state.uploaded_images):
                if i < len(st.session_state.page_metadata):
                    meta = st.session_state.page_metadata[i]
                    st.caption(f"📄 {meta['file_name']} (페이지 {meta['page_idx']}/{meta['total_pages']})")
                st.image(img, use_container_width=True)
                if i < len(st.session_state.uploaded_images) - 1:
                    st.divider()
        elif st.session_state.uploaded_image is not None:
            # 하위 호환: 단일 이미지
            st.subheader("📷 분석 이미지")
            st.image(st.session_state.uploaded_image, use_container_width=True)

        if st.session_state.uploaded_images or st.session_state.uploaded_image:
            st.divider()

        # 2. 구조화된 검사 결과 표시 (노트북 스타일)
        if st.session_state.ocr_structured or st.session_state.ocr_debug_output:
            st.subheader("🧾 검사 결과 데이터")
            display_structured_result(
                st.session_state.ocr_structured,
                st.session_state.ocr_debug_output
            )
            st.divider()

        # 3. OCR 원문 (접힌 상태)
        if st.session_state.ocr_text:
            with st.expander("📝 OCR 인식 결과", expanded=False):
                st.text(st.session_state.ocr_text)

        st.divider()
        st.subheader("🩺 AI 분석 해석")

        try:
            # 스트리밍 응답 생성
            full_response = st.write_stream(stream_factory())
        except Exception as e:
            error_msg = f"⚠️ 분석 중 오류가 발생했습니다: {str(e)}"
            st.error(error_msg)
            full_response = error_msg

    # 히스토리에 저장
    st.session_state.messages.append({"role": "assistant", "content": full_response})


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
        # 1. 업로드된 이미지 표시
        if st.session_state.uploaded_image is not None:
            st.subheader("📷 분석 이미지")
            st.image(st.session_state.uploaded_image, use_container_width=True)
            st.divider()

        # 2. OCR 인식 결과 표시
        if st.session_state.ocr_text:
            with st.expander("📝 OCR 인식 결과", expanded=False):
                st.text(st.session_state.ocr_text)

        # 3. 구조화된 데이터 표시 (debug output)
        if st.session_state.ocr_debug_output:
            with st.expander("🔬 구조화된 분석 데이터", expanded=False):
                st.text(st.session_state.ocr_debug_output)

        st.divider()
        st.subheader("🩺 분석 결과")

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
    """메인 애플리케이션 - Step 4.5(A) form 기반 단일 Send 플로우"""
    init_session_state()

    # 헤더
    st.title("🐱 냥닥터")
    st.caption("고양이 건강검진 결과지를 업로드하고 질문해보세요!")

    # 사이드바 - 설정 및 상태 정보
    with st.sidebar:
        st.subheader("⚙️ 설정")
        st.info(f"**LLM Provider:** {settings.llm_provider}")
        st.info(f"**OCR:** {settings.ocr_provider}")

        # 오케스트레이션 모델 정보
        with st.expander("🤖 모델 설정", expanded=False):
            st.caption(f"**의도분류:** {settings.openai_model_intent}")
            st.caption(f"**스몰톡:** {settings.openai_model_chat}")
            st.caption(f"**검사분석:** {settings.openai_model_analysis}")

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
            st.session_state.uploaded_images = []
            st.session_state.page_metadata = []
            st.session_state.last_ocr_cache_key = None
            st.session_state.last_file_name = None
            st.rerun()

        # 현재 업로드된 파일 정보
        if st.session_state.last_file_name:
            st.divider()
            st.subheader("📄 현재 문서")
            st.caption(f"파일: {st.session_state.last_file_name}")
            if st.button("🗑️ 문서 삭제", use_container_width=True):
                st.session_state.ocr_text = None
                st.session_state.ocr_structured = None
                st.session_state.ocr_debug_output = None
                st.session_state.uploaded_image = None
                st.session_state.uploaded_images = []
                st.session_state.page_metadata = []
                st.session_state.last_ocr_cache_key = None
                st.session_state.last_file_name = None
                st.rerun()

        st.divider()
        st.caption("Step 4.5(A) - form 기반 단일 Send 플로우")

    # 업로드된 이미지 표시 (접힌 상태)
    if st.session_state.uploaded_images:
        with st.expander(f"🖼️ 업로드된 이미지 ({len(st.session_state.uploaded_images)}장)", expanded=False):
            for i, img in enumerate(st.session_state.uploaded_images):
                # 페이지 메타데이터가 있으면 표시
                if i < len(st.session_state.page_metadata):
                    meta = st.session_state.page_metadata[i]
                    st.caption(f"📄 {meta['file_name']} (페이지 {meta['page_idx']}/{meta['total_pages']})")
                st.image(img, use_container_width=True)
                if i < len(st.session_state.uploaded_images) - 1:
                    st.divider()
    elif st.session_state.uploaded_image:
        # 하위 호환: 단일 이미지
        with st.expander("🖼️ 업로드된 이미지", expanded=False):
            st.image(st.session_state.uploaded_image, use_container_width=True)

    # OCR 구조화 결과 표시
    if st.session_state.ocr_debug_output or st.session_state.ocr_structured:
        with st.expander("🧾 검사 결과 분석", expanded=True):
            display_structured_result(
                st.session_state.ocr_structured,
                st.session_state.ocr_debug_output
            )

    # OCR 원문 텍스트 (접힌 상태)
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

    # ========================================
    # Step 4.x: form 기반 멀티파일 Send 플로우
    # ========================================
    st.divider()

    # 파일 상한 설정 (Phase 2 전 임시)
    MAX_FILES = 5
    MAX_PDF_PAGES = 10

    with st.form(key="chat_form", clear_on_submit=True):
        # 파일 업로드 (멀티파일 지원)
        uploaded_files = st.file_uploader(
            f"📎 검진 결과지 첨부 (최대 {MAX_FILES}개)",
            type=["jpg", "jpeg", "png", "pdf", "webp"],
            accept_multiple_files=True,
            help=f"고양이 건강검진 결과지 이미지 또는 PDF를 첨부하세요. 최대 {MAX_FILES}개, PDF는 페이지당 처리됩니다.",
        )

        # 카메라 촬영 (모바일 지원)
        camera_image = st.camera_input(
            "📷 카메라로 촬영 (선택사항)",
            help="모바일에서 검진 결과지를 카메라로 촬영할 수 있습니다.",
        )

        # 질문 입력
        user_input = st.text_area(
            "💬 질문 입력",
            placeholder="예: 이 검사 결과가 정상인가요? / 크레아티닌 수치가 높은데 걱정되요",
            height=100,
            help="검진 결과에 대한 질문을 입력하세요. 파일 없이 일반 건강 상담도 가능합니다.",
        )

        # 컬럼으로 버튼 배치
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            submitted = st.form_submit_button("🚀 Send", use_container_width=True)
        with col2:
            # form 안에서는 일반 버튼 사용 불가, 힌트만 표시
            pass

    # ========================================
    # Send 버튼 클릭 시 처리 (Step 4.x: 멀티파일)
    # ========================================
    if submitted:
        # 입력 통합: 파일 업로드 리스트 + 카메라 촬영
        # (Step 4.x: 멀티파일 처리, 업로드 순서 유지)
        input_files = []

        # 파일 업로더에서 온 파일들 추가
        if uploaded_files:
            for f in uploaded_files:
                input_files.append({"file": f, "source": "file_uploader", "name": f.name})

        # 카메라 촬영 이미지 추가 (있으면 마지막에)
        if camera_image is not None:
            input_files.append({"file": camera_image, "source": "camera", "name": "camera_capture.jpg"})

        # 파일 상한 체크
        if len(input_files) > MAX_FILES:
            st.warning(f"⚠️ 최대 {MAX_FILES}개 파일까지 처리 가능합니다. 처음 {MAX_FILES}개만 처리합니다.")
            input_files = input_files[:MAX_FILES]

        # 입력 검증
        if not user_input and not input_files:
            st.warning("💡 질문을 입력하거나 파일을 첨부/촬영해주세요!")
            st.stop()

        # 파일 처리 (멀티파일)
        if input_files:
            with st.status("🔄 처리 중...", expanded=True) as status:
                total_files = len(input_files)
                st.write(f"📤 1/4 파일 {total_files}개 업로드 완료")

                # 멀티파일 OCR 처리
                st.write(f"🔍 2/4 OCR 분석 중... (총 {total_files}개 파일)")
                success, message, processed_count = handle_multi_file_upload(
                    input_files,
                    max_pdf_pages=MAX_PDF_PAGES,
                    status_callback=lambda msg: st.write(msg)
                )

                if success:
                    st.write(f"✅ 2/4 {message}")
                else:
                    st.error(message)
                    status.update(label="❌ 처리 실패", state="error")
                    st.stop()

                status.update(label=f"✅ 문서 준비 완료 ({processed_count}페이지)", state="complete")

        # 질문이 있으면 LLM 응답 생성
        if user_input:
            handle_user_input(user_input)
        elif input_files and not user_input:
            # 파일만 업로드하고 질문이 없는 경우: 자동 분석 제안
            auto_message = "검진 결과지가 업로드되었어요! 어떤 점이 궁금하신가요? 🐱"
            with st.chat_message("assistant"):
                st.markdown(auto_message)
            st.session_state.messages.append({"role": "assistant", "content": auto_message})

    # ========================================
    # 안전 문구 (하단 고정)
    # ========================================
    st.divider()
    st.caption(
        "⚠️ **주의**: 이 서비스는 참고용 정보만 제공합니다. "
        "정확한 진단과 처방은 반드시 수의사와 상담하세요. "
        "응급 상황이 의심되면 즉시 동물병원을 방문해주세요."
    )


if __name__ == "__main__":
    main()
