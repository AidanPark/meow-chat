"""
Meow Chat 프론트엔드
1) LangGraph 기반 에이전트로 MCP 서버의 도구를 호출하고, 스트리밍 응답을 UI에 전달한다.
2) 사용자 대화를 세션 상태에 저장하고, 일정 턴이 넘으면 LLM 요약으로 압축한다.
3) 장기 메모리(MCP + Chroma), 이미지 업로드, 프로필 네임스페이스 등 부가 기능을 제공한다.
"""

import os
import sys
from datetime import datetime
import time
import io
import re
import streamlit as st
import streamlit.components.v1 as components
import threading
import uuid
# 전역 메모리 쓰기 락(스트림릿 세션과 무관하게 백그라운드 스레드에서 사용 가능)
MEM_WRITE_LOCK = threading.Lock()

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
from config.defaults import (
    RECENT_TURN_WINDOW,
    SUMMARIZE_TRIGGER_TURNS,
    RETRIEVAL_TOP_K,
)
from services.streaming import stream_react_rag_generator
from ui.styles import inject_core_css
from services.memory.core_facts import build_pinned_core_facts_block
from services.memory.memory_search import search_memories, MEMORY_TYPES
from services.memory.memory_writer import extract_candidates
from services.memory.memory_retriever import write_memories

# 실행 환경 변수 로드
load_dotenv(find_dotenv())

# =====================
# 상수 및 유틸리티
# =====================

LOG_PANEL_HEIGHT = 400
LOG_MAX_LINES = 1000
LOG_PREFIX_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3}\s+\[[A-Z]+\]\s+[^:]+:\s*"
)

def init_state() -> None:
    ss = st.session_state
    if "messages" not in ss:
        ss.messages = []
    if "uploaded_images" not in ss:
        ss.uploaded_images = []
    if "tool_history" not in ss:
        ss.tool_history = []
    if "previous_uploaded_count" not in ss:
        ss.previous_uploaded_count = 0
    if "user_id" not in ss:
        ss.user_id = os.getenv("USER", "default")
    if "retrieval_top_k" not in ss:
        ss.retrieval_top_k = RETRIEVAL_TOP_K
    if "recent_turn_window" not in ss:
        ss.recent_turn_window = RECENT_TURN_WINDOW
    if "summarize_trigger_turns" not in ss:
        ss.summarize_trigger_turns = SUMMARIZE_TRIGGER_TURNS
    if "last_retrieved_memories" not in ss:
        ss.last_retrieved_memories = []
    if "last_saved_memory_ids" not in ss:
        ss.last_saved_memory_ids = []
    if "last_saved_memories" not in ss:
        ss.last_saved_memories = []
    if "memory_token_budget" not in ss:
        ss.memory_token_budget = 1200
    if "memory_item_token_cap" not in ss:
        ss.memory_item_token_cap = 150
    if "pinned_token_budget" not in ss:
        ss.pinned_token_budget = 400
    if "manual_injected_memories" not in ss:
        ss.manual_injected_memories = []
    # 단일 프로필 사용: profiles/active_profile 상태는 유지하지 않습니다.
    if "react_max_iters" not in ss:
        ss.react_max_iters = 4
    # 개체 선택(보호자/고양이) 기능 제거: owner_id/cat_id 상태는 사용하지 않습니다.
    # 미리보기 상태는 사용하지 않습니다(미리보기는 즉시 생성 방식으로 표시).
    if "_uploader_nonce" not in ss:
        ss._uploader_nonce = 0
    if "summary_text" not in ss:
        ss.summary_text = None
    ss.setdefault("orch_logs_accum", [])
    ss.setdefault("_orch_last_line", None)
    # --- 계측/디버그 상태 ---
    ss.setdefault("_metrics", {
        "frame_seq": 0,                 # 앱 스크립트 재실행(프레임) 카운터
        "turn_seq": 0,                  # 사용자 발화(턴) 시퀀스
        "current_turn": 0,              # 현재 처리 중인 턴 번호
        "rerun_total": 0,               # 전체 rerun 호출 누계(명시적 호출만 집계)
        "rerun_this_turn": 0,           # 현재 턴 내 rerun 호출 수
        "last_stream_end": None,        # 마지막 스트리밍 종료 시각(ISO)
        "last_assistant_append": None,  # 마지막 assistant 메시지 append 완료 시각(ISO)
        "last_rerun_reason": None,      # 마지막 rerun 사유
    })
    ss.setdefault("debug_events", [])   # 최근 디버그 이벤트 텍스트 로그
    ss.setdefault("_pending_rerun", []) # 디바운스된 rerun 요청 사유 목록
    # --- 개인화 컨텍스트 미리보기 캐시/플래그 ---
    ss.setdefault("pinned_preview_cache", {"text": None, "ts": 0.0})
    ss.setdefault("pinned_preview_ttl", 20)  # seconds
    ss.setdefault("pinned_preview_needs_refresh", False)
    ss.setdefault("pinned_preview_defer_frame", 0)  # 특정 프레임 이후에만 재계산 허용
    ss.setdefault("feature_finish_verbatim", True)   # 계획 Finish(message)를 그대로 사용
    # --- 기능 플래그 ---
    ss.setdefault("feature_mem_bg", True)           # 메모리 추출/저장 백그라운드 실행
    ss.setdefault("feature_preview_mode", "ttl")   # immediate | ttl | button
    ss.setdefault("feature_extract_timing", "pre")  # pre | post (개인화 추출 시점)
    # --- 백그라운드 작업 상태 ---
    ss.setdefault("_bg_jobs", {})      # job_id -> {status, started_at, finished_at, turn}
    ss.setdefault("_bg_events", [])    # 워커가 남긴 이벤트(메인 스레드에서 처리)
    if "_mem_write_lock" not in ss:
        ss._mem_write_lock = threading.Lock()

def _log_event(msg: str) -> None:
    try:
        now = datetime.now().isoformat(timespec="milliseconds")
        m = st.session_state.get("_metrics", {})
        prefix = f"[{now}] f#{m.get('frame_seq',0)} t#{m.get('current_turn',0)}"
        line = f"{prefix} | {msg}"
        arr = st.session_state.get("debug_events", [])
        arr.append(line)
        # 최근 200줄만 유지
        if len(arr) > 200:
            arr[:] = arr[-200:]
        st.session_state["debug_events"] = arr
        try:
            print("[MEOW-METRICS]", line)
        except Exception:
            pass
    except Exception:
        pass

def _note_frame_advance() -> None:
    try:
        m = st.session_state["_metrics"]
        m["frame_seq"] = int(m.get("frame_seq", 0)) + 1
        st.session_state["_metrics"] = m
        _log_event("frame advanced")
    except Exception:
        pass

def _request_rerun(reason: str) -> None:
    """rerun을 즉시 실행하지 않고 요청 사유를 수집합니다."""
    try:
        pending = list(st.session_state.get("_pending_rerun", []))
        if reason not in pending:
            pending.append(reason)
        st.session_state["_pending_rerun"] = pending
        _log_event(f"enqueue rerun request: {reason}")
    except Exception:
        pass

def _perform_debounced_rerun() -> None:
    """수집된 rerun 요청을 한 번에 처리(단일 rerun)합니다."""
    try:
        reasons = list(st.session_state.get("_pending_rerun", []))
        if not reasons:
            return
        reason_text = ",".join(reasons)
        # 계측 카운터는 실제 실행 시에만 증가
        m = st.session_state.get("_metrics", {})
        m["rerun_total"] = int(m.get("rerun_total", 0)) + 1
        m["rerun_this_turn"] = int(m.get("rerun_this_turn", 0)) + 1
        m["last_rerun_reason"] = reason_text
        st.session_state["_metrics"] = m
        st.session_state["_pending_rerun"] = []
        _log_event(f"perform rerun: {reason_text}")
        st.rerun()
    except Exception:
        pass

def render_progress_html(placeholder, text: str) -> None:
    try:
        import html as _html
        _raw = text or ""
        _stripped = "\n".join(LOG_PREFIX_RE.sub("", ln) for ln in _raw.splitlines())
        safe = _html.escape(_stripped)
    except Exception:
        safe = (text or "")
    html_block = f"""
<div id=\"orch-logbox\" style=\"height: {LOG_PANEL_HEIGHT}px; overflow: auto; white-space: pre; 
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace; 
        background-color: #0e1117; color: #e6e6e6; padding: 8px; border-radius: 6px; 
        border: 1px solid rgba(255,255,255,0.1);\">{safe}</div>
    <script>
    (function() {{
        var el = document.getElementById('orch-logbox');
        if (!el) return;
        el.scrollTop = el.scrollHeight;
    }})();
    </script>
    """
    try:
        with placeholder.container():
            components.html(html_block, height=LOG_PANEL_HEIGHT)
    except Exception:
        try:
            placeholder.markdown(html_block, unsafe_allow_html=True)
        except Exception:
            try:
                placeholder.write(text or "")
            except Exception:
                pass

def merge_ring_into_session(rec: dict) -> None:
    try:
        ring = rec.get("orchestrator_logs")
        if ring is None:
            return
        ring_list = list(ring)
        if not ring_list:
            return
        acc = st.session_state.setdefault("orch_logs_accum", [])
        last_seen = st.session_state.get("_orch_last_line")
        start_idx = -1
        if last_seen is not None:
            try:
                start_idx = ring_list.index(last_seen)
            except ValueError:
                start_idx = -1
        new_lines = ring_list[start_idx + 1 :] if start_idx >= 0 else ring_list
        if new_lines:
            acc.extend(new_lines)
            if len(acc) > LOG_MAX_LINES:
                acc[:] = acc[-LOG_MAX_LINES:]
            st.session_state["orch_logs_accum"] = acc
            st.session_state["_orch_last_line"] = ring_list[-1]
    except Exception:
        pass

def append_turn_divider(progress_placeholder) -> None:
    try:
        acc = st.session_state.setdefault("orch_logs_accum", [])
        sep_line = (
            f"──── {datetime.now().strftime('%H:%M:%S')} ─────────────────────────────────"
        )
        acc.append(sep_line)
        if len(acc) > LOG_MAX_LINES:
            acc[:] = acc[-LOG_MAX_LINES:]
        st.session_state["orch_logs_accum"] = acc
        render_progress_html(progress_placeholder, "\n".join(acc[-LOG_MAX_LINES:]))
    except Exception:
        pass

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
    try:
        curr_key = _uploader_key()
        st.session_state.pop(curr_key, None)
    except Exception:
        pass
    st.session_state.uploaded_images = []
    st.session_state.previous_uploaded_count = 0
    st.session_state["_uploader_nonce"] = int(st.session_state.get("_uploader_nonce", 0)) + 1
    try:
        print(
            f"[DEBUG] _clear_sidebar_uploader_state(): cleared, new _uploader_nonce={st.session_state.get('_uploader_nonce')}"
        )
    except Exception:
        pass

# 세션 상태 기본값 초기화
init_state()

# 프레임(스크립트 재실행) 증가 계측
_note_frame_advance()

def _process_bg_events() -> None:
    """백그라운드 워커가 남긴 이벤트를 수거해 세션 상태에 반영합니다."""
    try:
        events = list(st.session_state.get("_bg_events", []))
        if not events:
            return
        st.session_state["_bg_events"] = []
        for ev in events:
            et = ev.get("type")
            if et == "memory_saved":
                ids = ev.get("ids") or []
                saved_preview = ev.get("saved_preview") or []
                if ids:
                    st.session_state.last_saved_memory_ids = (st.session_state.get("last_saved_memory_ids", []) + ids)[-50:]
                if saved_preview:
                    cur = list(st.session_state.get("last_saved_memories", []))
                    cur.extend(saved_preview)
                    st.session_state.last_saved_memories = cur[-50:]
                # 프리뷰는 다음 프레임부터 1회 재계산 (쓰기 직후 읽기 방지)
                st.session_state["pinned_preview_needs_refresh"] = True
                m = st.session_state.get("_metrics", {})
                next_frame = int(m.get("frame_seq", 0)) + 1
                st.session_state["pinned_preview_defer_frame"] = next_frame
                _log_event(f"bg event applied: memory_saved ({len(ids)} ids)")
    except Exception as e:
        _log_event(f"bg event processing failed: {e}")

_process_bg_events()


def render_sidebar() -> None:
    """사이드바 전체 UI를 렌더링하고 진행 로그 표시용 플레이스홀더를 초기화합니다."""
    global progress_logs_area
    with st.sidebar:
        st.title("🐱 Meow Chat")
        # 단일 프로필 사용: 제목에 프로필명을 직접 표시
        st.subheader(f"👤 {st.session_state.user_id}")

        st.divider()

        st.subheader("📎 이미지 업로드")
        uploaded_files = st.file_uploader(
            "대화에 첨부할 이미지",
            type=["png", "jpg", "jpeg", "gif", "webp"],
            accept_multiple_files=True,
            key=_uploader_key(),
        )
        # Streamlit은 초기에는 None, 위젯 초기화/클리어 시 빈 리스트([])를 반환할 수 있습니다.
        if uploaded_files is not None:
            if len(uploaded_files) > 0:
                stored: list[io.BytesIO] = []
                for file in uploaded_files:
                    data = file.getvalue()
                    buf = io.BytesIO(data)
                    buf.name = file.name  # type: ignore[attr-defined]
                    stored.append(buf)
                st.session_state.uploaded_images = stored
                st.session_state.previous_uploaded_count = len(stored)
            else:
                # 사용자가 X 버튼으로 비웠을 때: 키 교체 없이 상태만 리셋(위젯 재생성 최소화)
                if st.session_state.previous_uploaded_count > 0 or st.session_state.uploaded_images:
                    st.session_state.uploaded_images = []
                    st.session_state.previous_uploaded_count = 0
                    try:
                        _log_event("sidebar uploader cleared (state-only reset, no key change)")
                    except Exception:
                        pass

        st.divider()
        st.subheader("🤖 오케스트레이션 (ReAct)")
        st.session_state.react_max_iters = st.slider(
            "ReAct 최대 반복",
            min_value=1,
            max_value=12,
            value=int(st.session_state.react_max_iters),
            help=(
                "에이전트가 생각(Reason)·행동(Act) 사이클을 수행하는 최대 횟수입니다.\n"
                "- 높음: 복잡한 멀티스텝 문제 해결에 유리, 도구 호출/비용/지연↑\n"
                "- 낮음: 빠르고 저비용, 필요한 도구 호출을 다 못 할 수 있음\n"
                "권장: 3~6"
            ),
        )

        st.subheader("🔎 오케스트레이션 로그")
        progress_logs_area = st.empty()
        try:
            render_progress_html(
                progress_logs_area,
                "\n".join(st.session_state.get("orch_logs_accum", [])[-LOG_MAX_LINES:]),
            )
        except Exception:
            render_progress_html(progress_logs_area, "")


        st.divider()
        st.subheader("🧠 메모리 설정")

        st.session_state.retrieval_top_k = st.slider(
            "검색 Top-K",
            min_value=1,
            max_value=20,
            value=int(st.session_state.retrieval_top_k),
            help=(
                "메모리/지식 검색 시 한 번에 가져올 최대 항목 수입니다.\n"
                "- 높음: 회상률(Recall)↑, 잡음/비용↑\n"
                "- 낮음: 정확도(Precision)↑ 가능, 놓칠 위험↑\n"
                "권장: 5~10"
            ),
        )
        st.session_state.recent_turn_window = st.slider(
            "최근 턴 창 크기",
            min_value=3,
            max_value=20,
            value=int(st.session_state.recent_turn_window),
            help=(
                "자동 메모리 추출·요약에서 참조하는 최근 대화 턴 창 크기입니다.\n"
                "값 n은 사용자/어시스턴트 페어 기준으로 약 2n개의 메시지를 커버합니다.\n"
                "- 큼: 더 많은 맥락 반영, 비용/지연↑\n"
                "- 작음: 최신성↑, 맥락 누락 가능\n"
                "권장: 8~12"
            ),
        )
        st.session_state.summarize_trigger_turns = st.slider(
            "요약 트리거 턴 수",
            min_value=5,
            max_value=40,
            value=int(st.session_state.summarize_trigger_turns),
            help=(
                "대화가 길어졌을 때 이전 메시지를 요약(압축)하기 시작하는 임계 턴 수입니다.\n"
                "이 값을 넘으면 오래된 구간부터 요약 블록에 합쳐 저장합니다.\n"
                "- 낮음: 메모리 사용량↓, 상세 맥락 손실↑\n"
                "- 높음: 맥락 유지↑, 비용/지연↑\n"
                "권장: 10~20"
            ),
        )
        st.session_state.memory_token_budget = st.slider(
            "메모리 블록 최대 토큰",
            min_value=200,
            max_value=4000,
            value=int(st.session_state.memory_token_budget),
            step=50,
            help=(
                "대화 요약/검색으로 구성되는 일반 메모리 블록의 전체 길이(토큰) 상한입니다. "
                "이 한도를 넘으면 오래된 턴을 우선 압축하거나 생략합니다."
            ),
        )
        st.session_state.memory_item_token_cap = st.slider(
            "항목당 토큰 상한 (단일 항목 요약 길이)",
            min_value=50,
            max_value=300,
            value=int(st.session_state.memory_item_token_cap),
            step=10,
            help=(
                "개인화 컨텍스트를 구성할 때 각 항목(프로필/알레르기/약/식단 등)이 자신에게 배정받는 최대 길이(토큰)입니다.\n"
                "- 낮게 설정: 더 많은 항목을 담을 수 있으나, 문장이 중간에서 잘릴 수 있음\n"
                "- 높게 설정: 각 항목이 더 자세히 유지되지만, 전체 컨텍스트가 길어질 수 있음\n"
                "권장: 120~200\n"
                "예시) 150으로 설정하면 각 항목은 대략 2~3문장 길이 내에서 잘려 들어갑니다. 중요도/최근성이 낮은 항목은 우선순위에서 밀릴 수 있습니다."
            ),
        )
        st.session_state.pinned_token_budget = st.slider(
            "개인화 컨텍스트 토큰 (전체 한도)",
            min_value=100,
            max_value=1000,
            value=int(st.session_state.pinned_token_budget),
            step=50,
            help=(
                "프롬프트에 항상 주입되는 개인화 컨텍스트(고정 블록)의 전체 길이(토큰) 상한입니다.\n"
                "- 초과 시: 항목을 중요도/최근성 기준으로 선별해 일부만 포함합니다.\n"
                "- 영향: 모델 호출 당 비용/지연에 직접 영향합니다. 높을수록 개인화 품질이 오르지만 느려질 수 있습니다.\n"
                "권장: 300~600\n"
                "Tip) 개인화 컨텍스트 토큰을 키우면 회상 능력은 좋아지지만 응답 속도와 비용이 올라갑니다. 작업 성격에 맞춰 균형점을 찾으세요."
            ),
        )
        st.session_state.setdefault("pinned_max_queries", 6)
        st.session_state.pinned_max_queries = st.slider(
            "개인화 컨텍스트 검색 강도(질의 수)",
            min_value=3,
            max_value=12,
            value=int(st.session_state.pinned_max_queries),
            help=(
                "개인화 컨텍스트를 만들 때 사용하는 '키워드 기반 다중 검색'의 횟수입니다.\n"
                "- 동작: 프로필/알레르기/만성/금기/약/식단 등의 키워드에서 앞쪽 n개를 골라 n회 검색 → 결과 합치기 → 중복 제거 → 토큰 규칙으로 트리밍\n"
                "- 위치: 장기 메모리 벡터DB(Chroma)에서 유사도 검색을 수행합니다.\n"
                "- 높음(n↑): 더 다양한 카테고리에서 항목 회수(회상률↑), 대신 검색 횟수만큼 지연/비용↑\n"
                "- 낮음(n↓): 빠르고 저비용, 특정 카테고리 정보가 덜 들어올 수 있음\n"
                "- 팁: 미리보기에서 특정 범주(예: 알레르기)가 자주 빠지면 n을 1~2 올려보세요.\n"
                "권장: 4~8 (카테고리가 많을수록 ↑, 속도가 중요하면 ↓)"
            ),
        )

        st.subheader("📌 개인화 컨텍스트")
        st.caption("항상 프롬프트에 포함되는 개인화된 핵심 정보 요약입니다.")
        st.markdown(
            """
            - profile: 이름, 연령, 성별, 품종, 중성화, 몸무게, 성격 등 기본 프로필
            - allergy: 알레르기·과민·부작용 (예: “닭고기 알레르기”)
            - chronic: 만성질환·진단·병력
            - contraindication: 금기·주의
            - medication: 약/투약/용량
            - diet: 식단·사료·영양제
            - preference: 선호/비선호
            - constraint: 제약·제한
            - decision: 결정/합의
            - todo: 해야 할 일
            - timeline: 과거 기록/이력
            - fact, note: 일반 사실/노트
            """
        )
        # 미리보기: TTL 캐시 + 이벤트 기반 + 수동 새로고침
        col_p1, col_p2, col_p3 = st.columns([0.5, 0.3, 0.2])
        with col_p1:
            st.caption("미리보기는 캐시를 사용합니다(기본 20초). 저장 이벤트 시 1회 강제 갱신합니다.")
        with col_p2:
            # 선택: TTL 조정은 내부 상태로 유지(필요 시 주석 해제하여 UI 노출)
            # st.number_input("미리보기 TTL(초)", min_value=5, max_value=120, step=5,
            #                 value=int(st.session_state.get("pinned_preview_ttl", 20)), key="pinned_preview_ttl")
            pass
        with col_p3:
            force_refresh = st.button("새로고침", key="btn_refresh_preview")

        now_ts = time.time()
        cache = st.session_state.get("pinned_preview_cache", {"text": None, "ts": 0.0})
        ttl = int(st.session_state.get("pinned_preview_ttl", 20))
        needs_refresh = bool(st.session_state.get("pinned_preview_needs_refresh", False))
        expired = (now_ts - float(cache.get("ts") or 0.0)) > ttl
        defer_frame = int(st.session_state.get("pinned_preview_defer_frame", 0))
        cur_frame = int(st.session_state.get("_metrics", {}).get("frame_seq", 0))
        mode = st.session_state.get("feature_preview_mode", "ttl")

        # 쓰기 직후에는 최소 1프레임을 기다린 뒤 재계산
        can_recompute_now = (cur_frame >= defer_frame)
        if mode == "immediate":
            should_recompute = can_recompute_now
        elif mode == "button":
            should_recompute = (force_refresh or needs_refresh) and can_recompute_now
        else:  # ttl(default)
            should_recompute = (force_refresh or needs_refresh or (not cache.get("text")) or expired) and can_recompute_now
        _preview_text = None
        if should_recompute:
            try:
                model_prev = get_preview_model()
                text_new = build_pinned_core_facts_block(
                    user_id=st.session_state.user_id,
                    user_message="",
                    summary_text=st.session_state.get("summary_text"),
                    model=model_prev,
                    max_tokens=int(st.session_state.get("pinned_token_budget", 400)),
                    per_item_cap=int(st.session_state.get("memory_item_token_cap", 150)),
                    max_queries=int(st.session_state.get("pinned_max_queries", 6)),
                    importance_min=0.8,
                )
                if text_new:
                    st.session_state["pinned_preview_cache"] = {"text": text_new, "ts": now_ts}
                    st.session_state["pinned_preview_needs_refresh"] = False
                    _preview_text = text_new
                else:
                    _preview_text = cache.get("text")
            except Exception as e:
                # 실패 시 캐시 폴백
                _log_event(f"preview compute failed: {e}")
                _preview_text = cache.get("text")
                if not _preview_text:
                    st.info("미리보기를 생성할 수 없습니다. 잠시 후 다시 시도하거나 새로고침을 눌러주세요.")
        else:
            _preview_text = cache.get("text")

        if _preview_text:
            st.text_area("개인화 컨텍스트", value=_preview_text, height=220, key="ta_pinned_preview")
        else:
            st.caption("미리보기가 없습니다. 설정을 조정하거나 대화를 진행해 보세요.")

        st.divider()
    # 개체 선택(보호자/고양이) UI 제거
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

        # --- 실험적 기능 플래그 ---
        with st.expander("⚙️ 실험적 기능", expanded=False):
            st.caption("문제 발생 시, 여기서 기능을 끄고 롤백할 수 있습니다.")
            st.session_state.feature_mem_bg = st.toggle(
                "메모리 추출/저장 백그라운드", value=bool(st.session_state.get("feature_mem_bg", True))
            )
            preview_mode = st.session_state.get("feature_preview_mode", "ttl")
            mode = st.selectbox(
                "미리보기 모드",
                options=["ttl", "immediate", "button"],
                index=["ttl", "immediate", "button"].index(preview_mode if preview_mode in ["ttl","immediate","button"] else "ttl"),
                help="ttl: 캐시+이벤트 기반 / immediate: 항상 재계산(권장X) / button: 버튼/이벤트로만 재계산",
            )
            st.session_state.feature_preview_mode = mode
            extract_timing = st.session_state.get("feature_extract_timing", "pre")
            timing = st.selectbox(
                "개인화 추출 시점",
                options=["pre", "post"],
                index=["pre", "post"].index(extract_timing if extract_timing in ["pre","post"] else "pre"),
                help="pre: 턴 시작 직후 사용자 질의에서 추출(권장) / post: 응답 후 추출(구 전략)",
            )
            st.session_state.feature_extract_timing = timing

            st.session_state.feature_finish_verbatim = st.toggle(
                "계획 Finish(message) 그대로 사용", value=bool(st.session_state.get("feature_finish_verbatim", True)),
                help="계획 단계에서 finish.use=message가 생성되면, 추가 리라이팅 없이 그 메시지를 최종 응답으로 사용합니다."
            )

        st.divider()
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
            saved_items = st.session_state.get("last_saved_memories", [])
            if saved_items:
                st.caption("최근 저장 항목 미리보기:")
                for it in saved_items[-5:]:
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

        # --- 계측/진단 뷰 ---
        with st.expander("🧪 계측 로그", expanded=False):
            m = st.session_state.get("_metrics", {})
            col1, col2 = st.columns(2)
            with col1:
                st.caption("카운터")
                st.write(f"frame_seq: {m.get('frame_seq')}")
                st.write(f"turn_seq: {m.get('turn_seq')}")
                st.write(f"current_turn: {m.get('current_turn')}")
                st.write(f"rerun_total: {m.get('rerun_total')}")
                st.write(f"rerun_this_turn: {m.get('rerun_this_turn')}")
            with col2:
                st.caption("최근 시각")
                st.write(f"last_stream_end: {m.get('last_stream_end')}")
                st.write(f"last_assistant_append: {m.get('last_assistant_append')}")
                st.write(f"last_rerun_reason: {m.get('last_rerun_reason')}")
            logs = st.session_state.get("debug_events", [])
            if logs:
                st.caption(f"최근 이벤트 ({min(len(logs),50)}줄)")
                # 최근 50줄만 표시
                st.text("\n".join(logs[-50:]))


def render_chat_main() -> None:
    """채팅 기록과 입력 UI를 렌더링하고, 전송 시 run_chat_turn을 호출하여 한 턴을 수행합니다."""
    st.markdown('<div class="chat-messages">', unsafe_allow_html=True)
    for role, content in st.session_state.messages:
        with st.chat_message(role):
            st.markdown(content)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="input-section">', unsafe_allow_html=True)
    prompt_text = "질문을 입력하세요"
    if st.session_state.uploaded_images and len(st.session_state.uploaded_images) > 0:
        prompt_text += f" (📎 {len(st.session_state.uploaded_images)}개 이미지 첨부됨)"
    st.markdown("</div>", unsafe_allow_html=True)

    # 입력 키를 고정해 위젯 재생성으로 인한 불필요한 rerun을 방지
    if prompt := st.chat_input(prompt_text, key="chat_input_main"):
        # 새 사용자 발화 시작: 턴 시퀀스 증가 및 현재 턴 설정, rerun 카운터 리셋
        try:
            m = st.session_state.get("_metrics", {})
            m["turn_seq"] = int(m.get("turn_seq", 0)) + 1
            m["current_turn"] = int(m.get("turn_seq", 0))
            m["rerun_this_turn"] = 0
            st.session_state["_metrics"] = m
            _log_event("turn started: user submitted input")
        except Exception:
            pass
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
        _log_event("user message appended to session_state.messages")

        # 턴 시작 직후(동일 턴 비반영) 개인화 추출을 백그라운드로 실행
        try:
            if bool(st.session_state.get("feature_mem_bg", True)) and str(st.session_state.get("feature_extract_timing", "pre")) == "pre":
                recent_turns = list(st.session_state.messages)[-2 * int(st.session_state.get("recent_turn_window", 10)) :]
                user_id = st.session_state.user_id or os.getenv("USER", "default")
                job_id = f"memsave-{uuid.uuid4().hex}"
                jobs = st.session_state.get("_bg_jobs", {})
                jobs[job_id] = {
                    "status": "queued",
                    "started_at": datetime.now().isoformat(timespec="milliseconds"),
                    "turn": st.session_state.get("_metrics", {}).get("current_turn"),
                }
                st.session_state["_bg_jobs"] = jobs
                th = threading.Thread(
                    target=_bg_extract_and_save_memories,
                    args=(user_id, recent_turns, "", job_id),  # assistant_reply 비움
                    daemon=True,
                )
                th.start()
                _log_event(f"spawned bg memsave job (pre): {job_id}")
        except Exception as e:
            _log_event(f"spawn pre-reply bg job failed: {e}")

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

        # 사용자가 입력을 제출한 경우에만 턴 실행
        run_chat_turn(user_message=user_message, saved_image_paths=saved_image_paths)


def render_layout() -> dict:
    """사이드바를 먼저 렌더링하여 공용 플레이스홀더를 생성/반환합니다."""
    render_sidebar()
    return {"progress": progress_logs_area}


@st.cache_resource
def get_model_and_client():
    if not os.getenv("OPENAI_API_KEY"):
        st.error(
            "OPENAI_API_KEY가 설정되지 않았습니다. .env 또는 환경변수를 확인해주세요."
        )
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

    # 모델 선택: 개별 환경변수 → 기본값(OPENAI_DEFAULT_MODEL) → 하드코딩 폴백
    _default_model = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4.1-mini")
    _chat_model = os.getenv("FRONTEND_CHAT_STREAM_MODEL", _default_model) or _default_model
    model = ChatOpenAI(model=_chat_model, streaming=True)
    client = MultiServerMCPClient(SERVERS)  # type: ignore[arg-type]
    return model, client


@st.cache_resource
def get_preview_model():
    """미리보기 전용(비스트리밍) 모델 인스턴스.

    오케스트레이션과 분리해 세션 간섭을 줄이고, 프리뷰 계산 실패 시
    에러 메시지 대신 캐시에 폴백할 수 있도록 단순화한다.
    """
    if not os.getenv("OPENAI_API_KEY"):
        st.error(
            "OPENAI_API_KEY가 설정되지 않았습니다. .env 또는 환경변수를 확인해주세요."
        )
        st.stop()
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
        st.error(
            "프리뷰 모델 로드 실패 (LangChain/OpenAI 버전 불일치 가능).\n\n"
            f"설치된 버전:\n- langchain={lc}\n- langchain-core={lcc}\n- langchain-openai={lco}\n\n"
            "해결: 관련 패키지 버전을 동기화하세요."
            "\n자세한 오류: " + str(e)
        )
        st.stop()

    # 모델 선택: 개별 환경변수 → 기본값(OPENAI_DEFAULT_MODEL) → 하드코딩 폴백
    _default_model = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4.1-mini")
    _preview_model = os.getenv("FRONTEND_PREVIEW_MODEL", _default_model) or _default_model
    return ChatOpenAI(model=_preview_model, streaming=False)


def _bg_extract_and_save_memories(user_id: str, recent_turns: list[tuple[str, str]], assistant_reply: str, job_id: str) -> None:
    """백그라운드에서 메모리 추출(LLM) 후 Chroma에 저장하는 워커.

    - 모델: 비스트리밍(preview) 모델 사용
    - 쓰기: 세션 락으로 보호
    - 완료: 세션의 _bg_events에 결과를 남기고 종료
    """
    try:
        # 작업 시작 표시
        jobs = st.session_state.get("_bg_jobs", {})
        j = jobs.get(job_id, {})
        j["status"] = "running"
        jobs[job_id] = j
        st.session_state["_bg_jobs"] = jobs
        _log_event(f"bg job start: {job_id}")

        model_prev = get_preview_model()
        cands = []
        try:
            cands = extract_candidates(recent_turns=recent_turns, assistant_reply=assistant_reply, model=model_prev) or []
        except Exception as e:
            _log_event(f"bg extract_candidates failed: {e}")
            cands = []

        saved_ids = []
        saved_preview = []
        if cands:
            try:
                # 스트림릿 세션 상태 대신 전역 락 사용(백그라운드에서도 안전)
                with MEM_WRITE_LOCK:
                    ids = write_memories(user_id=user_id, memories=cands) or []
                saved_ids = ids
                # 미리보기용 저장 항목 프리뷰 구성
                for m in cands:
                    try:
                        saved_preview.append({"type": m.get("type"), "content": m.get("content")})
                    except Exception:
                        continue
            except Exception as e:
                _log_event(f"bg write_memories failed: {e}")

        # 메인 스레드 반영 이벤트 큐에 추가
        ev = {"type": "memory_saved", "ids": saved_ids, "saved_preview": saved_preview}
        arr = st.session_state.get("_bg_events", [])
        arr.append(ev)
        st.session_state["_bg_events"] = arr

        # 작업 완료 표시
        j["status"] = "done"
        j["finished_at"] = datetime.now().isoformat(timespec="milliseconds")
        jobs[job_id] = j
        st.session_state["_bg_jobs"] = jobs
        _log_event(f"bg job done: {job_id} (saved {len(saved_ids)})")
    except Exception as e:
        try:
            _log_event(f"bg job exception: {job_id} | {e}")
            jobs = st.session_state.get("_bg_jobs", {})
            j = jobs.get(job_id, {})
            j["status"] = "error"
            j["error"] = str(e)
            jobs[job_id] = j
            st.session_state["_bg_jobs"] = jobs
        except Exception:
            pass



def run_chat_turn(user_message: str, saved_image_paths: list[str]) -> None:
    """스트리밍과 실시간 진행 로그 갱신을 포함하여 어시스턴트의 한 턴을 실행합니다.

    기존 동작을 유지하면서 가독성을 위해 절차를 구조화했습니다.
    """
    global progress_logs_area
    with st.chat_message("assistant"):
        message_appended = False
        try:
            model, client = get_model_and_client()

            # 핵심 사실 블록 구성(선택 사항)
            pinned_block: str | None = None
            try:
                pinned_block = build_pinned_core_facts_block(
                    user_id=st.session_state.user_id,
                    user_message=user_message,
                    summary_text=None,
                    model=model,
                    max_tokens=int(
                        st.session_state.get("pinned_token_budget", 400)
                    ),
                    per_item_cap=int(
                        st.session_state.get("memory_item_token_cap", 150)
                    ),
                    max_queries=int(st.session_state.get("pinned_max_queries", 6)),
                    importance_min=0.8,
                )
            except Exception:
                pinned_block = None

            # ReAct 스트리밍 오케스트레이션 준비
            extra_vars = {
                "user_id": st.session_state.user_id or os.getenv("USER", "default"),
            }
            try:
                if saved_image_paths:
                    extra_vars["image_paths"] = list(saved_image_paths)
            except Exception:
                pass
            if pinned_block:
                extra_vars["pinned_core_facts"] = pinned_block
            # 구성 옵션 전달: finish 메시지를 그대로 사용할지 여부
            extra_vars["_compose_verbatim_on_finish"] = bool(st.session_state.get("feature_finish_verbatim", True))

            rec: dict = {
                "tokens": [],
                "used_tools": set(),
                "tool_details": [],
                "final_text": None,
            }
            text_stream = stream_react_rag_generator(
                user_request=user_message,
                rec=rec,
                model=model,
                client=client,
                max_iters=int(st.session_state.react_max_iters),
                extra_vars=extra_vars,
            )

            # 새 턴(사용자→어시스턴트) 구분선 추가
            append_turn_divider(progress_logs_area)

            # 스피너 하에서 첫 청크를 미리 수신
            first_chunk = None
            with st.spinner("생각 중…"):
                try:
                    first_chunk = next(text_stream)
                except StopIteration:
                    first_chunk = None

            # 첫 청크 직후 한 번 로그 병합/렌더링(이미 계획/실행 로그가 존재할 수 있음)
            try:
                merge_ring_into_session(rec)
                render_progress_html(
                    progress_logs_area,
                    "\n".join(
                        st.session_state.get("orch_logs_accum", [])[-LOG_MAX_LINES:]
                    ),
                )
            except Exception:
                pass

            def _chain_first(gen, first):
                if first is not None:
                    yield first
                for chunk in gen:
                    yield chunk

            def _wrap_with_orch_logs(gen):
                prev_len = -1
                while True:
                    try:
                        chunk = next(gen)
                    except StopIteration:
                        # 마지막 병합 및 렌더링
                        try:
                            merge_ring_into_session(rec)
                            render_progress_html(
                                progress_logs_area,
                                "\n".join(
                                    st.session_state.get("orch_logs_accum", [])[
                                        -LOG_MAX_LINES:
                                    ]
                                ),
                            )
                        except Exception:
                            pass
                        break
                    try:
                        ring = rec.get("orchestrator_logs")
                        if ring is not None:
                            curr_len = len(ring)
                            if curr_len != prev_len:
                                prev_len = curr_len
                                merge_ring_into_session(rec)
                                render_progress_html(
                                    progress_logs_area,
                                    "\n".join(
                                        st.session_state.get("orch_logs_accum", [])[
                                            -LOG_MAX_LINES:
                                        ]
                                    ),
                                )
                    except Exception:
                        pass
                    yield chunk

            # 사이드바 로그를 갱신하면서 채팅으로 텍스트 스트리밍
            final_text = st.write_stream(
                _wrap_with_orch_logs(_chain_first(text_stream, first_chunk))
            )
            try:
                # 스트리밍 종료 시각 기록
                m = st.session_state.get("_metrics", {})
                m["last_stream_end"] = datetime.now().isoformat(timespec="milliseconds")
                st.session_state["_metrics"] = m
                _log_event("streaming finished")
            except Exception:
                pass

            now = datetime.now().strftime("%H:%M:%S")
            for d in rec.get("tool_details", []):
                st.session_state.tool_history.append({"time": now, **d})
            used_tools = list(rec.get("used_tools") or [])
            if used_tools:
                st.info(f"🛠️ 사용된 도구: {', '.join(str(x) for x in used_tools)}")

            final_str = (
                final_text
                if isinstance(final_text, str)
                else (rec.get("final_text") or "")
            )
            # 대화 기반 핵심/사실 자동 저장 - 플래그에 따라 백그라운드 또는 동기 실행
            try:
                recent_turns = list(st.session_state.messages)[-2 * int(st.session_state.get("recent_turn_window", 10)) :]
                user_id = st.session_state.user_id or os.getenv("USER", "default")
                extract_timing = str(st.session_state.get("feature_extract_timing", "pre"))
                mem_bg = bool(st.session_state.get("feature_mem_bg", True))
                if mem_bg and extract_timing == "post":
                    job_id = f"memsave-{uuid.uuid4().hex}"
                    jobs = st.session_state.get("_bg_jobs", {})
                    jobs[job_id] = {
                        "status": "queued",
                        "started_at": datetime.now().isoformat(timespec="milliseconds"),
                        "turn": st.session_state.get("_metrics", {}).get("current_turn"),
                    }
                    st.session_state["_bg_jobs"] = jobs
                    th = threading.Thread(
                        target=_bg_extract_and_save_memories,
                        args=(user_id, recent_turns, final_str, job_id),
                        daemon=True,
                    )
                    th.start()
                    _log_event(f"spawned bg memsave job (post): {job_id}")
                elif not mem_bg:
                    # 동기 실행(롤백 모드): 비스트리밍 모델로 추출 후 락 보호 하에 저장
                    model_prev = get_preview_model()
                    cands = []
                    try:
                        cands = extract_candidates(recent_turns=recent_turns, assistant_reply=final_str, model=model_prev) or []
                    except Exception as e:
                        _log_event(f"sync extract_candidates failed: {e}")
                        cands = []
                    if cands:
                        try:
                            lock = st.session_state._mem_write_lock
                            with lock:
                                ids = write_memories(user_id=user_id, memories=cands) or []
                            if ids:
                                st.session_state.last_saved_memory_ids = (st.session_state.get("last_saved_memory_ids", []) + ids)[-50:]
                                saved_preview = []
                                for m in cands:
                                    try:
                                        saved_preview.append({"type": m.get("type"), "content": m.get("content")})
                                    except Exception:
                                        continue
                                cur = list(st.session_state.get("last_saved_memories", []))
                                cur.extend(saved_preview)
                                st.session_state.last_saved_memories = cur[-50:]
                                st.session_state["pinned_preview_needs_refresh"] = True
                                m = st.session_state.get("_metrics", {})
                                st.session_state["pinned_preview_defer_frame"] = int(m.get("frame_seq", 0)) + 1
                        except Exception as e:
                            _log_event(f"sync write_memories failed: {e}")
            except Exception as e:
                _log_event(f"mem save scheduling failed: {e}")
            try:
                if rec.get("saved_memories"):
                    cur = list(st.session_state.get("last_saved_memories", []))
                    cur.extend(rec.get("saved_memories") or [])
                    st.session_state.last_saved_memories = cur[-50:]
            except Exception:
                pass
            st.session_state.messages.append(("assistant", final_str))
            try:
                m = st.session_state.get("_metrics", {})
                m["last_assistant_append"] = datetime.now().isoformat(timespec="milliseconds")
                st.session_state["_metrics"] = m
                _log_event("assistant message appended to session_state.messages")
            except Exception:
                pass
            message_appended = True

            # 즉시 rerun 금지: 백그라운드 완료 이벤트가 다음 프레임에서 프리뷰를 갱신합니다.
            try:
                print(
                    "[DEBUG] rec.lab_report_saved=",
                    rec.get("lab_report_saved"),
                    "| saved_memories_len=",
                    len(rec.get("saved_memories") or []),
                )
            except Exception:
                pass
            if rec.get("lab_report_saved"):
                try:
                    print(
                        "[DEBUG] Entering lab_report_saved clear path. _uploader_nonce(before)=",
                        st.session_state.get("_uploader_nonce"),
                    )
                except Exception:
                    pass
                _clear_sidebar_uploader_state()
                st.info("검사결과 저장 완료. 첨부 이미지 목록을 초기화했습니다.")
                _request_rerun("lab_report_saved_uploader_reset")
            # 디바운스된 rerun을 한 번만 수행
            _perform_debounced_rerun()
            st.stop()
        except Exception as e:
            # 부분 결과가 있다면 우선 노출하고, 하단에 오류 메시지를 덧붙인다.
            try:
                partial = ""
                try:
                    partial = (client and client) and (rec.get("final_text") or "")  # rec에 누적된 최종 텍스트가 있으면 사용
                except Exception:
                    partial = rec.get("final_text") or ""
                if not message_appended:
                    text = partial or ""
                    if text:
                        text = text + f"\n\n[오류] {e}"
                    else:
                        text = f"오류가 발생했습니다: {e}"
                    st.session_state.messages.append(("assistant", text))
                    try:
                        m = st.session_state.get("_metrics", {})
                        m["last_assistant_append"] = datetime.now().isoformat(timespec="milliseconds")
                        st.session_state["_metrics"] = m
                        _log_event("assistant message appended in except")
                    except Exception:
                        pass
            except Exception:
                # 최후 수단: 오류 메시지만 남김
                st.session_state.messages.append(("assistant", f"오류가 발생했습니다: {e}"))
        finally:
            # 여기서는 rerun을 호출하지 않습니다. (디바운스/플래그 기반 정책 유지)
            pass


ph = render_layout()
render_chat_main()

# 앱 로직 종료
