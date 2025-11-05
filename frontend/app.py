"""
Meow Chat 프론트엔드
1) LangGraph 기반 에이전트로 MCP 서버의 도구를 호출하고, 스트리밍 응답을 UI에 전달한다.
2) 사용자 대화를 세션 상태에 저장하고, 일정 턴이 넘으면 LLM 요약으로 압축한다.
3) 장기 메모리(MCP + Chroma), 이미지 업로드, 프로필 네임스페이스 등 부가 기능을 제공한다.
"""

import os
import sys
import asyncio
import time
from datetime import datetime
import io
import json
import streamlit as st

# MCP 서버와 연결하는 LangChain 어댑터
from langchain_mcp_adapters.client import MultiServerMCPClient


from dotenv import load_dotenv, find_dotenv

# 동일 경로의 모듈을 우선 임포트할 수 있도록 sys.path 정비
CURRENT_DIR = os.path.dirname(__file__)
if CURRENT_DIR and CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

UPLOAD_ROOT = os.path.join(CURRENT_DIR, "uploads")

# 프론트엔드 서비스/설정 모듈
from config.loader import load_mcp_server_config
from config.defaults import RECENT_TURN_WINDOW, SUMMARIZE_TRIGGER_TURNS, RETRIEVAL_TOP_K
from services.streaming import stream_react_rag_generator
from ui.styles import inject_core_css
# Legacy memory helpers no longer needed in app-level pipeline (kept server-side)
from services.memory.core_facts import build_pinned_core_facts_block
from services.memory.memory_search import search_memories, MEMORY_TYPES
# from services.orchestrator import run_react_rag  # no longer imported here

# ---------------------------------------------------------------------------
# 전체 UI 흐름 안내
# 1) 전역 설정: .env와 MCP 서버 설정을 불러오고, Streamlit 페이지 옵션과 CSS를 적용한다.
# 2) 세션 상태 초기화: 메시지, 요약, 메모리, 업로드된 이미지 등 대화 유지에 필요한 상태 값을 준비한다.
# 3) Sidebar:
#    - 프로필 전환 및 새 네임스페이스 생성
#    - 이미지 업로드 관리
#    - 장기 메모리/핵심 사실 관련 슬라이더와 스위치
#    - 환경 진단(필수 패키지 설치 여부), 메모리 검색 도구
# 4) 메인 영역:
#    - 과거 메시지를 순서대로 렌더링
#    - 사용자 입력을 받으면 메시지 목록에 추가하고, LangGraph 에이전트를 비동기로 실행
#    - 실행 도중 stream_agent_generator 가 토큰을 streaming 하며, 완료 후 요약 및 메모리 저장 로직 수행
# 5) 대화 종료 후 UI는 마지막 응답, 사용된 도구, 요약 결과, 메모리 기록 등을 세션 상태로 관리한다.
# ---------------------------------------------------------------------------

# 실행 환경 변수 로드
load_dotenv(find_dotenv())

# 스트림릿 페이지 속성 구성
st.set_page_config(page_title="Meow Chat", page_icon="🐱", layout="wide")

# 핵심 CSS 삽입
inject_core_css()

# MCP 서버 설정 불러오기
SERVERS = load_mcp_server_config()

# 공통: 사이드바 업로드 위젯의 X 버튼 동작을 모사하는 초기화 함수
def _uploader_key() -> str:
    return f"sidebar_image_uploader_{st.session_state.get('_uploader_nonce', 0)}"

def _clear_sidebar_uploader_state():
    # 위젯 상태 자체를 제거하여 다음 렌더에서 완전히 초기화되도록 함
    try:
        curr_key = _uploader_key()
        st.session_state.pop(curr_key, None)
    except Exception:
        pass
    # 내부 보관 리스트도 함께 초기화
    st.session_state.uploaded_images = []
    st.session_state.previous_uploaded_count = 0
    # 새 키로 리마운트되도록 nonce 증가
    st.session_state["_uploader_nonce"] = int(st.session_state.get("_uploader_nonce", 0)) + 1
    # 디버그 로그
    try:
        print(f"[DEBUG] _clear_sidebar_uploader_state(): cleared, new _uploader_nonce={st.session_state.get('_uploader_nonce')}")
    except Exception:
        pass

# 세션 상태 기본값 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploaded_images" not in st.session_state:
    st.session_state.uploaded_images = []
if "tool_history" not in st.session_state:
    st.session_state.tool_history = []
if "previous_uploaded_count" not in st.session_state:
    st.session_state.previous_uploaded_count = 0
if "user_id" not in st.session_state:
    st.session_state.user_id = os.getenv("USER", "default")
if "use_memory" not in st.session_state:
    st.session_state.use_memory = True
if "retrieval_top_k" not in st.session_state:
    st.session_state.retrieval_top_k = RETRIEVAL_TOP_K
if "recent_turn_window" not in st.session_state:
    st.session_state.recent_turn_window = RECENT_TURN_WINDOW
if "summarize_trigger_turns" not in st.session_state:
    st.session_state.summarize_trigger_turns = SUMMARIZE_TRIGGER_TURNS
if "last_retrieved_memories" not in st.session_state:
    st.session_state.last_retrieved_memories = []
if "last_saved_memory_ids" not in st.session_state:
    st.session_state.last_saved_memory_ids = []
if "last_saved_memories" not in st.session_state:
    st.session_state.last_saved_memories = []
if "memory_token_budget" not in st.session_state:
    st.session_state.memory_token_budget = 1200
if "memory_item_token_cap" not in st.session_state:
    st.session_state.memory_item_token_cap = 150
if "pinned_core_enabled" not in st.session_state:
    st.session_state.pinned_core_enabled = True
if "pinned_token_budget" not in st.session_state:
    st.session_state.pinned_token_budget = 400
if "manual_injected_memories" not in st.session_state:
    st.session_state.manual_injected_memories = []
if "profiles" not in st.session_state:
    st.session_state.profiles = [st.session_state.user_id or "default"]
if "active_profile" not in st.session_state:
    st.session_state.active_profile = st.session_state.user_id
if "_prev_active_profile" not in st.session_state:
    st.session_state._prev_active_profile = st.session_state.active_profile
if "auto_allowed_tools" not in st.session_state:
    st.session_state.auto_allowed_tools = []
if "react_max_iters" not in st.session_state:
    st.session_state.react_max_iters = 4
if "owner_id" not in st.session_state:
    st.session_state.owner_id = ""
if "cat_id" not in st.session_state:
    st.session_state.cat_id = ""
if "pinned_preview" not in st.session_state:
    st.session_state.pinned_preview = None
if "_uploader_nonce" not in st.session_state:
    st.session_state._uploader_nonce = 0
if "summary_text" not in st.session_state:
    st.session_state.summary_text = None

# 사이드바 진행 로그용 플레이스홀더 (동일 런에서 실시간 업데이트)
from typing import Any as _Any
progress_logs_area: _Any = None


@st.cache_resource
def get_model_and_client():
    if not os.getenv("OPENAI_API_KEY"):
        st.error("OPENAI_API_KEY가 설정되지 않았습니다. .env 또는 환경변수를 확인해주세요.")
        st.stop()
    # LangChain 모듈 임포트 시 버전 불일치가 잦으므로, 실패하면 버전 정보를 함께 안내한다.
    try:
        from langchain_openai import ChatOpenAI  # type: ignore
    except Exception as e:
        import importlib.metadata as _md
        def _ver(pkg: str) -> str:
            try:
                return _md.version(pkg)
            except Exception:
                return "not-installed"

        lc = _ver("langchain")
        lcc = _ver("langchain-core")
        lco = _ver("langchain-openai")
        lg = _ver("langgraph")
        st.error(
            "LangChain/OpenAI 모듈 임포트 오류로 앱을 시작할 수 없습니다.\n\n"
            "원인: 설치된 패키지 버전 불일치 가능성이 큽니다.\n\n"
            f"설치된 버전:\n- langchain={lc}\n- langchain-core={lcc}\n- langchain-openai={lco}\n- langgraph={lg}\n\n"
            "권장 해결책:\n"
            "- 프로젝트의 고정 버전을 맞추세요 (backend/requirements.txt 참고).\n"
            "- 최소 조합 예시: langchain==1.0.3, langchain-openai==1.0.1, langgraph==1.0.2\n"
            "- 또는 모든 관련 패키지 최신 버전으로 동기 업그레이드\n"
            "\n자세한 오류: " + str(e)
        )
        st.stop()

    model = ChatOpenAI(model="gpt-4.1-mini", streaming=True)
    client = MultiServerMCPClient(SERVERS)  # type: ignore[arg-type]
    return model, client


def run_ocr_on_images(paths: list[str], client) -> list[tuple[str, str]]:
    """[Deprecated] 더 이상 사용되지 않습니다. OCR은 extract_lab_report 내부에서 수행됩니다.

    이 함수는 호환성을 위해 남겨졌으며 빈 결과를 반환합니다.
    """
    if not paths:
        return []
    return [(p, "") for p in paths]


with st.sidebar:
    st.title("🐱 Meow Chat")
    st.subheader("👤 프로필 / 네임스페이스")
    active = st.selectbox(
        "활성 프로필",
        options=st.session_state.profiles,
        index=st.session_state.profiles.index(st.session_state.active_profile) if st.session_state.active_profile in st.session_state.profiles else 0,
        key="profile_select",
    )
    with st.container():
        new_prof = st.text_input("새 프로필 이름", key="new_profile_name")
        if st.button("프로필 추가", use_container_width=True, key="btn_add_profile"):
            name = (new_prof or "").strip()
            if name and name not in st.session_state.profiles:
                st.session_state.profiles.append(name)
                st.session_state.active_profile = name
                st.success(f"프로필 '{name}' 추가 및 활성화")
            elif name in st.session_state.profiles:
                st.info("이미 존재하는 프로필입니다.")
            else:
                st.warning("프로필 이름을 입력하세요.")
    if active != st.session_state.active_profile:
        st.session_state.active_profile = active

    if st.session_state.active_profile != st.session_state._prev_active_profile:
        st.session_state.user_id = st.session_state.active_profile
        st.session_state.messages = []
        st.session_state.summary_text = None
        st.session_state.tool_history = []
        st.session_state.last_retrieved_memories = []
        st.session_state.last_saved_memory_ids = []
        st.session_state.manual_injected_memories = []
        st.session_state.mem_search_results = []
        st.session_state.uploaded_images = []
        st.session_state.previous_uploaded_count = 0
        st.session_state._prev_active_profile = st.session_state.active_profile
        st.info(f"프로필 전환: '{st.session_state.active_profile}' (대화 상태 초기화)")

    st.divider()

    st.subheader("📎 이미지 업로드")
    uploaded_files = st.file_uploader(
        "대화에 첨부할 이미지",
        type=["png", "jpg", "jpeg", "gif", "webp"],
        accept_multiple_files=True,
        key=_uploader_key(),
    )
    if uploaded_files:
        stored: list[io.BytesIO] = []
        for file in uploaded_files:
            data = file.getvalue()
            buf = io.BytesIO(data)
            buf.name = file.name  # type: ignore[attr-defined]
            stored.append(buf)
        st.session_state.uploaded_images = stored
        st.session_state.previous_uploaded_count = len(stored)
        # 별도 안내 메시지는 띄우지 않고 입력창 프롬프트에서 첨부 현황을 확인하도록 한다.
    else:
        if st.session_state.uploaded_images:
            _clear_sidebar_uploader_state()

    # 진행 로그(최근) - 고정 영역 스크롤 표시 (이미지 업로드 바로 아래)
    st.subheader("🔎 진행 로그")
    logs = st.session_state.get("last_progress_logs", [])
    progress_logs_area = st.empty()
    def _render_progress(_logs: list[str]):
        text = "\n".join([str(x) for x in _logs[-200:]]) if _logs else ""
        try:
            progress_logs_area.text_area(
                label="진행 로그",
                value=text,
                height=200,
                key="ta_progress_logs",
                label_visibility="collapsed",
            )
        except Exception:
            progress_logs_area.text_area(
                label="진행 로그",
                value=text,
                height=200,
                key="ta_progress_logs_fallback",
            )
    _render_progress(logs)

    # 수동 첨부 초기화 버튼 제거 (자동 초기화 및 분석 성공 시 초기화만 유지)

    # 🤖 오케스트레이션: 진행 로그 바로 아래로 이동
    st.divider()
    st.subheader("🤖 오케스트레이션 (ReAct)")
    TOOL_OPTIONS = [
        # Memory
        "memory_search", "memory_read", "memory_upsert",
        # Weather
        "get_weather", "get_forecast", "get_air_quality", "get_time_zone", "search_location",
        # Math
        "add", "subtract", "multiply", "divide", "convert_units", "calculate_percentage",
        # Lab / Health (존재 시)
        "extract_lab_report", "extract_lab_table", "analyze_cat_health",
    ]
    st.session_state.auto_allowed_tools = st.multiselect(
        "허용 도구(화이트리스트)",
        options=TOOL_OPTIONS,
        default=[],
        help="플래너/루프가 사용할 수 있는 도구만 허용합니다. 안전/비용 제어용",
    )
    st.session_state.react_max_iters = st.slider("ReAct 최대 반복", min_value=1, max_value=12, value=int(st.session_state.react_max_iters))

    st.divider()

    st.subheader("🧠 메모리 설정")
    st.session_state.use_memory = st.checkbox("장기 메모리 사용", value=st.session_state.use_memory)
    st.session_state.pinned_core_enabled = st.checkbox("핵심 사실 고정 슬롯 사용", value=st.session_state.pinned_core_enabled)
    st.session_state.retrieval_top_k = st.slider("검색 Top-K", min_value=1, max_value=20, value=int(st.session_state.retrieval_top_k))
    st.session_state.recent_turn_window = st.slider("최근 턴 창 크기", min_value=3, max_value=20, value=int(st.session_state.recent_turn_window))
    st.session_state.summarize_trigger_turns = st.slider("요약 트리거 턴 수", min_value=5, max_value=40, value=int(st.session_state.summarize_trigger_turns))
    st.session_state.memory_token_budget = st.slider("메모리 블록 최대 토큰", min_value=200, max_value=4000, value=int(st.session_state.memory_token_budget), step=50)
    st.session_state.memory_item_token_cap = st.slider("항목당 토큰 상한", min_value=50, max_value=300, value=int(st.session_state.memory_item_token_cap), step=10)
    st.session_state.pinned_token_budget = st.slider("핵심 사실 슬롯 토큰", min_value=100, max_value=1000, value=int(st.session_state.pinned_token_budget), step=50)
    st.session_state.setdefault("pinned_compact_with_model", False)
    st.session_state.setdefault("pinned_max_queries", 6)
    st.session_state.pinned_compact_with_model = st.checkbox("핵심 사실 요약 압축(느릴 수 있음)", value=bool(st.session_state.pinned_compact_with_model))
    st.session_state.pinned_max_queries = st.slider("핵심 사실 검색 강도(질의 수)", min_value=3, max_value=12, value=int(st.session_state.pinned_max_queries))

    with st.expander("📌 핵심 사실 미리보기", expanded=False):
        st.caption("owner_id / cat_id 범위를 기준으로 중요도 높은 프로필 항목을 요약해 보여줍니다.")
        col_a, col_b = st.columns([0.5, 0.5])
        with col_a:
            if st.button("미리보기 갱신", use_container_width=True, key="btn_refresh_pinned_preview"):
                try:
                    model, _client = get_model_and_client()
                    preview = build_pinned_core_facts_block(
                        user_id=st.session_state.user_id,
                        user_message="",
                        summary_text=st.session_state.get("summary_text"),
                        model=model,
                        max_tokens=int(st.session_state.get("pinned_token_budget", 400)),
                        per_item_cap=int(st.session_state.get("memory_item_token_cap", 150)),
                        compact_with_model=bool(st.session_state.get("pinned_compact_with_model", False)),
                        max_queries=int(st.session_state.get("pinned_max_queries", 6)),
                        owner_id=(st.session_state.owner_id or None),
                        cat_id=(st.session_state.cat_id or None),
                        importance_min=0.8,
                    )
                    st.session_state.pinned_preview = preview or "(비어 있음)"
                    st.success("핵심 사실 미리보기를 갱신했습니다.")
                except Exception as e:
                    st.warning(f"미리보기 실패: {e}")
        with col_b:
            if st.button("미리보기 초기화", use_container_width=True, key="btn_clear_pinned_preview"):
                st.session_state.pinned_preview = None
        if st.session_state.pinned_preview:
            st.text_area("핵심 사실", value=st.session_state.pinned_preview, height=220, key="ta_pinned_preview")
        else:
            st.caption("미리보기가 없습니다. '미리보기 갱신'을 눌러 생성하세요.")

    st.divider()
    st.subheader("👥 개체 선택 (보호자/고양이)")
    st.session_state.owner_id = st.text_input("보호자 ID (owner_id)", value=st.session_state.owner_id, placeholder="예: owner:aidan")
    st.session_state.cat_id = st.text_input("고양이 ID (cat_id)", value=st.session_state.cat_id, placeholder="예: cat:momo")

    # 진행 로그(최근) - 고정 영역 스크롤 표시


    st.divider()
    with st.expander("📜 타임라인 · 메모리 검색", expanded=False):
        q = st.text_input("키워드", key="mem_search_query", placeholder="예: 예방접종, 알레르기, 사료")
        col1, col2 = st.columns(2)
        with col1:
            yf = st.number_input("연도(시작)", value=0, min_value=0, max_value=9999, step=1)
        with col2:
            yt = st.number_input("연도(종료)", value=0, min_value=0, max_value=9999, step=1)
        year_from = int(yf) if yf else None
        year_to = int(yt) if yt else None
        types = st.multiselect("유형 필터", options=MEMORY_TYPES, default=[])
        limit = st.slider("최대 표시 수", min_value=10, max_value=200, value=50, step=10)
        if st.button("검색", use_container_width=True):
            try:
                res = search_memories(
                    user_id=st.session_state.user_id,
                    query=q,
                    types=types or None,
                    year_from=year_from,
                    year_to=year_to,
                    limit=int(limit),
                )
                st.session_state.mem_search_results = res
            except Exception as e:
                st.warning(f"검색 오류: {e}")

        results = st.session_state.get("mem_search_results", [])
        if results:
            st.caption(f"검색 결과: {len(results)}개")
            sel_indices = []
            for idx, r in enumerate(results[:200]):
                ts = r.get("timestamp") or ""
                rtype = r.get("type") or ""
                content = r.get("content") or ""
                with st.container(border=True):
                    c1, c2 = st.columns([0.8, 0.2])
                    with c1:
                        st.markdown(f"**[{rtype}]** {content}")
                        if ts:
                            st.caption(ts)
                    with c2:
                        if st.checkbox("선택", key=f"mem_pick_{idx}"):
                            sel_indices.append(idx)
            if st.button("선택 항목 컨텍스트에 넣기", type="primary", use_container_width=True):
                picked = []
                for i in sel_indices:
                    if 0 <= i < len(results):
                        txt = (results[i].get("content") or "").strip()
                        if txt:
                            picked.append(txt)
                base = st.session_state.get("manual_injected_memories", [])
                st.session_state.manual_injected_memories = picked + base
                st.success(f"컨텍스트에 {len(picked)}개 항목을 추가했습니다.")
            if st.button("선택 초기화", use_container_width=True):
                st.session_state.manual_injected_memories = []
                st.session_state.mem_search_results = []
                st.info("선택과 결과를 초기화했습니다.")

    # 맨 아래: 환경 상태 + 메모리 상태
    st.divider()
    # 환경/백엔드 배지
    import importlib.util as _import_util
    tiktoken_ok = _import_util.find_spec("tiktoken") is not None
    chroma_ok = _import_util.find_spec("chromadb") is not None
    st.subheader("🧩 환경 상태")
    col_a, col_b = st.columns(2)
    with col_a:
        st.caption("Vector Store")
        st.markdown(f"- {'🟢' if chroma_ok else '🔴'} Chroma")
        st.caption("Persist dir: data/vectors/")
    with col_b:
        st.caption("Tokenizer")
        st.markdown(f"- {'🟢' if tiktoken_ok else '🔴'} tiktoken")

    with st.expander("🧠 메모리 상태", expanded=False):
        last_ret = st.session_state.get("last_retrieved_memories", [])
        last_saved = st.session_state.get("last_saved_memory_ids", [])
        st.caption(f"최근 검색된 메모리: {len(last_ret)}개")
        for m in last_ret[:5]:
            st.write(f"- {m}")
        st.caption(f"최근 저장된 메모리: {len(last_saved)}개")
        # 최근 저장된 메모리 상세 표시 (검사결과는 날짜만 간단히 표시)
        saved_items = st.session_state.get("last_saved_memories", [])
        if saved_items:
            st.caption("최근 저장 항목 미리보기:")
            for it in saved_items[-5:]:  # 최근 5개
                try:
                    if isinstance(it, dict):
                        t = it.get("type") or ""
                        if t == "lab_report":
                            dates = it.get("dates") or []
                            dates_txt = ", ".join([str(d) for d in dates]) if dates else "(날짜 없음)"
                            st.write(f"- [LabReport] {dates_txt}")
                        else:
                            content = (it.get("content") or it.get("text") or "").strip()
                            if content and len(content) > 120:
                                content = content[:120] + "…"
                            if content:
                                st.write(f"- [{t or 'memo'}] {content}")
                            else:
                                st.write(f"- [{t or 'memo'}]")
                    else:
                        st.write(f"- {str(it)[:120]}")
                except Exception:
                    pass


# 대화 메시지 영역 렌더링
st.markdown('<div class="chat-messages">', unsafe_allow_html=True)
for role, content in st.session_state.messages:
    with st.chat_message(role):
        st.markdown(content)

st.markdown('</div>', unsafe_allow_html=True)

# 사용자 입력 영역
st.markdown('<div class="input-section">', unsafe_allow_html=True)

prompt_text = "질문을 입력하세요"
if st.session_state.uploaded_images and len(st.session_state.uploaded_images) > 0:
    prompt_text += f" (📎 {len(st.session_state.uploaded_images)}개 이미지 첨부됨)"

st.markdown('</div>', unsafe_allow_html=True)

chat_input_key = f"chat_input_{len(st.session_state.uploaded_images)}"
if prompt := st.chat_input(prompt_text, key=chat_input_key):
    user_message = prompt
    if st.session_state.uploaded_images:
        image_info = f" [📎 {len(st.session_state.uploaded_images)}개 이미지 첨부]"
        user_message += image_info

    saved_image_paths: list[str] = []
    display_images = list(st.session_state.uploaded_images)
    if st.session_state.uploaded_images:
        profile_dir = os.path.abspath(os.path.join(UPLOAD_ROOT, st.session_state.user_id))
        os.makedirs(profile_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for idx, img in enumerate(st.session_state.uploaded_images):
            try:
                data = img.getvalue()
                original_name = getattr(img, "name", f"upload_{idx}.png")
                safe_name = f"{timestamp}_{idx}_{original_name}"
                path = os.path.abspath(os.path.join(profile_dir, safe_name))
                with open(path, "wb") as f:
                    f.write(data)
                saved_image_paths.append(path)
            except Exception:
                continue
        if saved_image_paths:
            path_lines = "\n".join(f"- {p}" for p in saved_image_paths)
            user_message += "\n\n[첨부 이미지 경로]\n" + path_lines
        st.session_state.uploaded_images = []
        st.session_state.previous_uploaded_count = 0

    st.session_state.messages.append(("user", user_message))

    with st.chat_message("user"):
        st.markdown(user_message)
        if display_images:
            img_cols = st.columns(min(len(display_images), 3))
            for i, img_file in enumerate(display_images):
                try:
                    img_file.seek(0)
                except Exception:
                    pass
                with img_cols[i % 3]:
                    st.image(img_file, caption=img_file.name, width=120)

    with st.chat_message("assistant"):
        try:
            model, client = get_model_and_client()

            # 핵심 사실 슬롯 자동 집계(옵션)
            pinned_block: str | None = None
            try:
                if bool(st.session_state.get("pinned_core_enabled", True)):
                    pinned_block = build_pinned_core_facts_block(
                        user_id=st.session_state.user_id,
                        user_message=user_message,
                        summary_text=None,
                        model=model,
                        max_tokens=int(st.session_state.get("pinned_token_budget", 400)),
                        per_item_cap=int(st.session_state.get("memory_item_token_cap", 150)),
                        compact_with_model=bool(st.session_state.get("pinned_compact_with_model", False)),
                        max_queries=int(st.session_state.get("pinned_max_queries", 6)),
                        owner_id=(st.session_state.owner_id or None),
                        cat_id=(st.session_state.cat_id or None),
                        importance_min=0.8,
                    )
            except Exception:
                pinned_block = None

            # 항상 ReAct 스트리밍 오케스트레이션
            # 스트리밍 방식으로 ReAct 실행
            allowed_tools = st.session_state.auto_allowed_tools or None
            extra_vars = {
                "owner_id": st.session_state.owner_id or "",
                "cat_id": st.session_state.cat_id or "",
                "user_id": st.session_state.user_id or os.getenv("USER", "default"),
            }
            # 첨부 이미지가 저장되어 있으면 경로 배열을 vars로 명시 전달
            try:
                if saved_image_paths:
                    extra_vars["image_paths"] = list(saved_image_paths)
            except Exception:
                pass
            if pinned_block:
                extra_vars["pinned_core_facts"] = pinned_block

            rec = {"tokens": [], "used_tools": set(), "tool_details": [], "final_text": None}
            text_stream = stream_react_rag_generator(
                user_request=user_message,
                rec=rec,
                model=model,
                client=client,
                allowed_tools=allowed_tools,
                max_iters=int(st.session_state.react_max_iters),
                extra_vars=extra_vars,
            )
            # 첫 토큰이 나타날 때까지는 동그라미 스피너만 보여주고,
            # 첫 토큰 이후에는 기존처럼 채팅 영역에 바로 스트리밍되도록 처리
            first_chunk = None
            with st.spinner("생각 중…"):
                try:
                    first_chunk = next(text_stream)
                except StopIteration:
                    first_chunk = None

            def _chain_first(gen, first):
                if first is not None:
                    yield first
                for chunk in gen:
                    yield chunk

            # 스트림을 소비하면서 사이드바 진행 로그를 실시간 갱신
            def _wrap_with_progress(gen):
                for chunk in gen:
                    # 진행 로그가 쌓였으면 사이드바 갱신
                    try:
                        if rec.get("progress_logs"):
                            st.session_state["last_progress_logs"] = list(rec.get("progress_logs") or [])[-200:]
                            # 렌더 함수가 존재하면 갱신
                            if 'progress_logs_area' in globals() and progress_logs_area is not None:
                                logs_now = st.session_state.get("last_progress_logs", [])
                                # 텍스트 영역 재렌더
                                try:
                                    progress_logs_area.text_area(
                                        label="진행 로그",
                                        value="\n".join([str(x) for x in logs_now[-200:]]),
                                        height=200,
                                        key="ta_progress_logs",
                                        label_visibility="collapsed",
                                    )
                                except Exception:
                                    pass
                    except Exception:
                        pass
                    yield chunk

            final_text = st.write_stream(_wrap_with_progress(_chain_first(text_stream, first_chunk)))

            now = datetime.now().strftime("%H:%M:%S")
            for d in rec.get("tool_details", []):
                st.session_state.tool_history.append({"time": now, **d})
            used_tools = list(rec.get("used_tools") or [])
            if used_tools:
                st.info(f"🛠️ 사용된 도구: {', '.join(str(x) for x in used_tools)}")
            # 진행 로그를 사이드바 표시용 세션 상태에 저장
            try:
                if rec.get("progress_logs"):
                    st.session_state["last_progress_logs"] = list(rec.get("progress_logs") or [])[-200:]
            except Exception:
                pass

            final_str = final_text if isinstance(final_text, str) else (rec.get("final_text") or "")
            # 최근 저장된 메모리 목록에 반영 (먼저 처리)
            try:
                if rec.get("saved_memories"):
                    cur = list(st.session_state.get("last_saved_memories", []))
                    cur.extend(rec.get("saved_memories") or [])
                    st.session_state.last_saved_memories = cur[-50:]
            except Exception:
                pass
            # 답변을 세션 메시지에 먼저 반영
            st.session_state.messages.append(("assistant", final_str))
            # 디버그: 저장 플래그 상태 출력
            try:
                print("[DEBUG] rec.lab_report_saved=", rec.get("lab_report_saved"), "| saved_memories_len=", len(rec.get("saved_memories") or []))
            except Exception:
                pass
            # 검사결과 저장 성공 시: 업로더 완전 초기화 + 즉시 리렌더
            if rec.get("lab_report_saved"):
                try:
                    print("[DEBUG] Entering lab_report_saved clear path. _uploader_nonce(before)=", st.session_state.get("_uploader_nonce"))
                except Exception:
                    pass
                _clear_sidebar_uploader_state()
                st.info("검사결과 저장 완료. 첨부 이미지 목록을 초기화했습니다.")
                st.rerun()
            st.stop()

            # 이하 레거시 파이프라인 코드는 st.stop() 이후로 도달하지 않으므로 제거되었습니다.

        except Exception as e:
            err = f"오류가 발생했습니다: {e}"
            st.markdown(err)
            st.session_state.messages.append(("assistant", err))

# 앱 로직 종료
