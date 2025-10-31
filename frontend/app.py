"""
Streamlit Chat App (Meow Chat)
- Multi MCP server tools via langchain_mcp_adapters
- Streaming responses, rolling summary + recent N turns
- Long-term memory (Chroma + OpenAIEmbeddings) with tiktoken trimming
"""

import os
import sys
import asyncio
import time
from datetime import datetime
import io
import streamlit as st

# LangChain MCP Adapters
from langchain_mcp_adapters.client import MultiServerMCPClient


from dotenv import load_dotenv, find_dotenv
from ruamel.yaml import YAML

# Ensure this directory is import-first (avoid clashing with top-level `config/`)
CURRENT_DIR = os.path.dirname(__file__)
if CURRENT_DIR and CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# Local modules
from config.loader import load_mcp_server_config
from config.defaults import RECENT_TURN_WINDOW, SUMMARIZE_TRIGGER_TURNS, RETRIEVAL_TOP_K
from services.streaming import stream_agent_generator
from services.context_builder import build_context_messages
from services.summarizer import maybe_update_summary
from ui.styles import inject_core_css
from services.memory.memory_retriever import retrieve_memories, write_memories
from services.memory.memory_writer import extract_candidates
from services.memory.memory_utils import trim_memory_block
from services.memory.core_facts import build_pinned_core_facts_block
from services.memory.memory_search import search_memories, MEMORY_TYPES

# Load .env
load_dotenv(find_dotenv())

# Streamlit page config
st.set_page_config(page_title="Meow Chat", page_icon="🐱", layout="wide")

# CSS
inject_core_css()

# Servers config
SERVERS = load_mcp_server_config()

# Session state init
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


@st.cache_resource
def get_model_and_client():
    if not os.getenv("OPENAI_API_KEY"):
        st.error("OPENAI_API_KEY가 설정되지 않았습니다. .env 또는 환경변수를 확인해주세요.")
        st.stop()
    # Lazy import with diagnostics to avoid hard crashes from version mismatches
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
        key="sidebar_image_uploader",
    )
    if uploaded_files:
        previous_names = [getattr(img, "name", "") for img in st.session_state.uploaded_images]
        stored: list[io.BytesIO] = []
        current_names: list[str] = []
        for file in uploaded_files:
            data = file.getvalue()
            buf = io.BytesIO(data)
            buf.name = file.name  # type: ignore[attr-defined]
            stored.append(buf)
            current_names.append(file.name)
        st.session_state.uploaded_images = stored
        st.session_state.previous_uploaded_count = len(stored)
        # No additional notification; chat input 이미 첨부 개수를 표시합니다.
    else:
        if st.session_state.uploaded_images:
            st.session_state.uploaded_images = []
            st.session_state.previous_uploaded_count = 0

    # 첨부 초기화 버튼은 제거함 (사용자는 새로 업로드하거나 새 프로필/세션으로 리셋 가능)

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

    # 환경/백엔드 배지
    import importlib.util as _import_util
    tiktoken_ok = _import_util.find_spec("tiktoken") is not None
    chroma_ok = _import_util.find_spec("chromadb") is not None
    st.markdown("---")
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


# 채팅 메시지 렌더
st.markdown('<div class="chat-messages">', unsafe_allow_html=True)
for role, content in st.session_state.messages:
    with st.chat_message(role):
        st.markdown(content)

st.markdown('</div>', unsafe_allow_html=True)

# 입력
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

    st.session_state.messages.append(("user", user_message))

    with st.chat_message("user"):
        st.markdown(user_message)
        if st.session_state.uploaded_images:
            img_cols = st.columns(min(len(st.session_state.uploaded_images), 3))
            for i, img_file in enumerate(st.session_state.uploaded_images):
                with img_cols[i % 3]:
                    st.image(img_file, caption=img_file.name, width=120)

    with st.chat_message("assistant"):
        try:
            rec = {"tokens": [], "used_tools": set(), "tool_details": [], "final_text": None}
            model, client = get_model_and_client()

            summary = st.session_state.get("summary_text")
            rt_window = int(st.session_state.recent_turn_window)
            sum_trig = int(st.session_state.summarize_trigger_turns)
            summary, pruned_messages = maybe_update_summary(
                summary,
                st.session_state.messages,
                recent_turn_window=rt_window,
                summarize_trigger_turns=sum_trig,
                model=model,
            )
            st.session_state.summary_text = summary
            st.session_state.messages = pruned_messages

            user_id = st.session_state.user_id
            retrieved_texts: list[str] = []
            pinned_text: str | None = None
            if st.session_state.use_memory and st.session_state.pinned_core_enabled:
                try:
                    now_ts = time.time()
                    cache = st.session_state.get("_pinned_cache", {})
                    cache_uid = f"{user_id}"
                    cache_ok = (
                        isinstance(cache, dict)
                        and cache.get("user_id") == cache_uid
                        and (now_ts - float(cache.get("ts", 0))) < 60.0
                        and cache.get("settings") == {
                            "max_tokens": int(st.session_state.pinned_token_budget),
                            "per_item_cap": int(st.session_state.memory_item_token_cap),
                            "compact": bool(st.session_state.pinned_compact_with_model),
                            "max_queries": int(st.session_state.pinned_max_queries),
                        }
                    )
                    if cache_ok:
                        pinned_text = cache.get("text")
                    else:
                        pinned_text = build_pinned_core_facts_block(
                            user_id=user_id,
                            user_message=user_message,
                            summary_text=summary,
                            model=model,
                            max_tokens=int(st.session_state.pinned_token_budget),
                            per_item_cap=int(st.session_state.memory_item_token_cap),
                            compact_with_model=bool(st.session_state.pinned_compact_with_model),
                            max_queries=int(st.session_state.pinned_max_queries),
                        )
                        st.session_state._pinned_cache = {
                            "user_id": cache_uid,
                            "ts": now_ts,
                            "text": pinned_text,
                            "settings": {
                                "max_tokens": int(st.session_state.pinned_token_budget),
                                "per_item_cap": int(st.session_state.memory_item_token_cap),
                                "compact": bool(st.session_state.pinned_compact_with_model),
                                "max_queries": int(st.session_state.pinned_max_queries),
                            },
                        }
                except Exception:
                    pinned_text = None
            if st.session_state.use_memory:
                try:
                    retrieved_items = retrieve_memories(user_id=user_id, user_message=user_message, summary_text=summary, k=int(st.session_state.retrieval_top_k))
                    retrieved_texts = [it.get("content", "").strip() for it in retrieved_items if (it.get("content") or "").strip()]
                    retrieved_texts = trim_memory_block(
                        texts=retrieved_texts,
                        max_tokens=int(st.session_state.memory_token_budget),
                        per_item_token_cap=int(st.session_state.memory_item_token_cap),
                    )
                except Exception:
                    retrieved_texts = []

            manual = st.session_state.get("manual_injected_memories", [])
            if manual:
                seen = set()
                merged: list[str] = []
                for it in manual + retrieved_texts:
                    k = it.strip()
                    if not k or k in seen:
                        continue
                    seen.add(k)
                    merged.append(k)
                retrieved_texts = merged
            st.session_state.last_retrieved_memories = retrieved_texts

            lc_messages = build_context_messages(
                summary_text=summary,
                history_messages=st.session_state.messages,
                new_user_message=user_message,
                recent_turn_window=rt_window,
                retrieved_memories=(retrieved_texts or None) if st.session_state.use_memory else None,
                pinned_core_facts=pinned_text if (st.session_state.use_memory and st.session_state.pinned_core_enabled) else None,
            )

            text = st.write_stream(stream_agent_generator(lc_messages, rec, model, client))

            now = datetime.now().strftime("%H:%M:%S")
            for d in rec["tool_details"]:
                st.session_state.tool_history.append({"time": now, **d})

            used_tools = list(rec["used_tools"]) if rec.get("used_tools") else []
            if used_tools:
                st.info(f"🛠️ 사용된 도구: {', '.join(used_tools)}")

            final_str = text if isinstance(text, str) else (rec.get("final_text") or "")
            st.session_state.messages.append(("assistant", final_str))

            if st.session_state.use_memory:
                try:
                    candidates = extract_candidates(recent_turns=st.session_state.messages, assistant_reply=final_str, model=model)
                    if candidates:
                        saved_ids = write_memories(user_id=user_id, memories=candidates)
                        st.session_state.last_saved_memory_ids = saved_ids
                        if saved_ids:
                            st.caption(f"🧠 장기 메모리 {len(saved_ids)}개 저장됨")
                except Exception:
                    pass

        except Exception as e:
            err = f"오류가 발생했습니다: {e}"
            st.markdown(err)
            st.session_state.messages.append(("assistant", err))

# End of app
