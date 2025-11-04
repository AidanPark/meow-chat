from __future__ import annotations

import asyncio
from threading import Thread, Event, current_thread
from queue import Queue, Empty
import time
from typing import Dict, Any, Generator, List, Set
import logging
import traceback
import os
import asyncio

from langchain_core.callbacks import BaseCallbackHandler
from services.orchestrator import (
    react_plan_node,
    react_execute_node,
    react_self_eval_node,
    react_compose_node,
    OrchestratorState,
)

# 이 모듈은 LangGraph 기반 에이전트를 백그라운드 스레드에서 실행하고,
# 얻어진 토큰 스트림을 Streamlit UI에 실시간으로 전달하는 역할을 담당한다.
# - UIStreamingCallbackHandler: LangChain 콜백에서 토큰/도구 사용 정보를 수집
# - stream_agent_generator: 비동기로 에이전트를 돌리고, 큐에 쌓인 토큰을 제너레이터로 방출
# rec 딕셔너리에는 최종 응답 텍스트, 토큰 목록, 사용된 도구 내역 등이 채워져
# 호출 측(frontend/app.py)에서 UI 상태를 업데이트하는 데 활용된다.


# ------------------------------------------------------------
# Logging setup (console + file) for streaming exceptions
# ------------------------------------------------------------
_LOGGER = logging.getLogger("meow.frontend.streaming")
if not _LOGGER.handlers:
    _LOGGER.setLevel(logging.INFO)
    # Console handler
    _ch = logging.StreamHandler()
    _ch.setLevel(logging.INFO)
    _fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    _ch.setFormatter(_fmt)
    _LOGGER.addHandler(_ch)

    # File handler under frontend/logs/
    try:
        _BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # frontend/
        _LOG_DIR = os.path.join(_BASE_DIR, "logs")
        os.makedirs(_LOG_DIR, exist_ok=True)
        _fh = logging.FileHandler(os.path.join(_LOG_DIR, "streaming.log"))
        _fh.setLevel(logging.INFO)
        _fh.setFormatter(_fmt)
        _LOGGER.addHandler(_fh)
    except Exception:
        # If file handler fails (permissions, etc.), continue with console-only
        pass


def _format_exception_recursive(exc: BaseException) -> str:
    """Format an exception, expanding ExceptionGroup recursively to capture sub-exceptions."""
    lines: List[str] = []
    try:
        lines.append("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
        # Python 3.11 ExceptionGroup compatibility
        subs = getattr(exc, "exceptions", None)
        if isinstance(subs, (list, tuple)) and subs:
            for idx, sub in enumerate(subs):
                lines.append(f"\n-- Sub-exception #{idx+1} ------------------------------------------------\n")
                try:
                    lines.append("".join(traceback.format_exception(type(sub), sub, sub.__traceback__)))
                except Exception:
                    lines.append(repr(sub))
    except Exception:
        try:
            lines.append(repr(exc))
        except Exception:
            pass
    return "".join(lines)


class UIStreamingCallbackHandler(BaseCallbackHandler):
    """LLM 토큰과 도구 호출 정보를 큐에 흘려보내는 스트리밍 콜백."""

    def __init__(self, token_queue: Queue, done_event: Event, rec: Dict[str, Any]):
        # rec에는 실행 중 수집한 토큰, 사용된 도구, 도구 인자, 최종 응답 등을 누적한다.
        self.token_queue = token_queue
        self.done_event = done_event
        self.rec = rec

    def on_llm_new_token(self, token: str, **kwargs):  # type: ignore[override]
        # 새 토큰이 들어오면 즉시 토큰 큐와 기록에 추가한다.
        try:
            if token:
                self.rec.setdefault("tokens", []).append(token)
                self.token_queue.put(token)
        except Exception:
            pass

    def on_tool_start(self, serialized=None, input_str=None, **kwargs):  # type: ignore[override]
        # LangGraph 에이전트가 도구를 실행하기 직전에 도구 이름과 인자를 기록한다.
        try:
            name = None
            if isinstance(serialized, dict):
                name = serialized.get("name") or serialized.get("id")
            if name:
                used: Set[str] = self.rec.setdefault("used_tools", set())
                used.add(name)
                details: List[Dict[str, Any]] = self.rec.setdefault("tool_details", [])
                details.append({"name": name, "args": input_str})
        except Exception:
            pass


def stream_agent_generator(
    lc_messages: List[Dict[str, Any]],
    rec: Dict[str, Any],
    model,
    client,
) -> Generator[str, None, None]:
    """LangGraph 에이전트를 비동기 실행하고 토큰을 스트리밍으로 내보낸다."""
    token_queue: Queue[str] = Queue()
    done = Event()

    handler = UIStreamingCallbackHandler(token_queue, done, rec)

    async def _run_async():
        try:
            # 지연 임포트: 환경별 호환성 보정을 위해 함수 내부에서 임포트
            from services.langgraph_compat import create_react_agent_executor  # type: ignore
            tools = await client.get_tools()
            agent = create_react_agent_executor(model, tools)
            result = await agent.ainvoke({"messages": lc_messages}, config={"callbacks": [handler]})

            messages = None
            if isinstance(result, dict):
                messages = result.get("messages") or result.get("outputs")
            elif isinstance(result, list):
                messages = result

            if messages:
                final = messages[-1]
                rec["final_text"] = getattr(final, "content", None) or str(final)
        except Exception as e:
            rec["error"] = str(e)
            token_queue.put(f"\n[에러] {e}")
        finally:
            done.set()

    thread = Thread(target=lambda: asyncio.run(_run_async()), daemon=True)
    thread.start()

    aggregated: List[str] = []
    while not (done.is_set() and token_queue.empty()):
        try:
            token = token_queue.get(timeout=0.05)
            aggregated.append(token)
            yield token
        except Empty:
            time.sleep(0.01)

    if not aggregated:
        final_text = rec.get("final_text")
        if final_text:
            yield final_text


def stream_react_rag_generator(
    user_request: str,
    rec: Dict[str, Any],
    model,
    client,
    allowed_tools: List[str] | None = None,
    max_iters: int = 4,
    extra_vars: Dict[str, Any] | None = None,
) -> Generator[str, None, None]:
    """ReAct 오케스트레이터를 단계별로 실행하며 스트리밍 텍스트를 방출합니다.

    - 계획/실행/자가평가 루프를 직접 호출하여 진행 상황을 즉시 보여줍니다.
    - 최종 답변은 모델 astream으로 자연스럽게 서술하며 토큰 스트림을 그대로 전달합니다.
    - rec에는 tokens, used_tools, tool_details, final_text를 누적합니다.
    """
    token_queue: Queue[str] = Queue()
    done = Event()

    def _qput(txt: str):
        try:
            if txt:
                token_queue.put(txt)
        except Exception:
            pass

    async def _run_async():
        try:
            # 초기 상태 구성
            from typing import cast
            state: OrchestratorState = cast(OrchestratorState, {
                "user_request": user_request,
                "allowed_tools": allowed_tools or [],
                "vars": dict(extra_vars or {}),
                "outputs": {},
                "errors": [],
                "warnings": [],
                "tools_used": [],
                "react_iteration": 0,
                "react_max_iters": int(max_iters),
                "react_history": [],
            })

            # 루프 실행: 계획 → 실행 → 자가평가
            for _ in range(int(max_iters)):
                state = await react_plan_node(state, model, client)
                finish_hint = state.get("react_finish")
                plan = state.get("plan") or {}
                steps = plan.get("steps") or []
                if steps:
                    step = steps[0]
                    tool = step.get("tool")
                    args = step.get("args") or {}
                    _qput(f"계획: {tool} 실행 준비\n")
                if finish_hint:
                    break

                state = await react_execute_node(state, client)
                # 마지막 관찰 스트리밍
                hist = state.get("react_history") or []
                if hist:
                    last = hist[-1]
                    step = last.get("step") or {}
                    tool = step.get("tool")
                    args = step.get("args") or {}
                    obs = last.get("observation")
                    # 사용된 도구 기록
                    try:
                        used: Set[str] = rec.setdefault("used_tools", set())
                        if tool:
                            used.add(str(tool))
                        details: List[Dict[str, Any]] = rec.setdefault("tool_details", [])
                        details.append({"name": tool, "args": args})
                    except Exception:
                        pass
                    if tool:
                        _qput(f"🛠️ {tool} 호출\n")
                    if obs is not None:
                        # 너무 길면 요약해서 출력
                        try:
                            txt = str(obs)
                            if len(txt) > 600:
                                txt = txt[:600] + "…"
                            _qput(f"관찰: {txt}\n")
                        except Exception:
                            pass

                state = await react_self_eval_node(state, model)
                cont = bool(state.get("react_should_continue"))
                if cont:
                    _qput("계속 진행합니다…\n")
                    continue
                break

            # 최종 메시지 합성
            state = react_compose_node(state)
            final_msg = state.get("message") or ""
            outs = state.get("outputs") or {}
            errs = state.get("errors") or []

            # 스몰토크/무플랜 폴백: 모델 스트리밍으로 직접 응답 생성
            no_effective_plan = (not final_msg or str(final_msg).strip() in ("", "실행할 계획이 없었습니다.")) and (not outs) and (not errs)
            if no_effective_plan:
                sys_prompt = (
                    "당신은 친절하고 간결한 한국어 비서입니다. 작은 인사말이나 잡담에도 따뜻하게 응답하세요.\n"
                    "불필요한 도구 사용 계획은 만들지 말고, 지금 입력에 친근하게 답변만 출력하세요."
                )
                vars_map = dict(extra_vars or {})
                pinned = vars_map.get("pinned_core_facts") if isinstance(vars_map, dict) else None
                if pinned:
                    sys_prompt += f"\n[핵심 사실 요약]\n{str(pinned)[:800]}\n"
                async for chunk in model.astream([
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_request.strip()},
                ]):
                    # LangChain의 AIMessageChunk 등에서 content만 추출, 메타/빈 청크는 무시
                    token = None
                    try:
                        token = getattr(chunk, "content", None)
                    except Exception:
                        token = None
                    if token:
                        rec.setdefault("tokens", []).append(token)
                        _qput(token)
                rec["final_text"] = "".join(rec.get("tokens", []))
                return

            # 일반 케이스: 관찰을 바탕으로 최종 답변을 자연스럽게 정리하여 스트리밍
            try:
                history = state.get("react_history") or []
                brief_obs: List[str] = []
                for h in history[-5:]:  # 최근 5개만 요약
                    step = (h or {}).get("step") or {}
                    tool = step.get("tool")
                    obs = (h or {}).get("observation")
                    line = f"- {tool}: {str(obs)[:200]}" if tool else f"- {str(obs)[:200]}"
                    brief_obs.append(line)

                sys_prompt = (
                    "당신은 친절한 한국어 어시스턴트입니다. 아래 사용자 요청과 도구 관찰을 참고하여 간결하고 도움되는 답변만 출력하세요."
                )
                user_blk = (
                    f"요청: {user_request}\n\n"
                    f"관찰 요약:\n" + ("\n".join(brief_obs) if brief_obs else "(없음)") + "\n\n"
                    f"초안: {final_msg}\n"
                )
                tokens: List[str] = []
                async for chunk in model.astream([
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_blk},
                ]):
                    # content만 출력하고, 빈/메타 청크는 건너뜁니다.
                    token = None
                    try:
                        token = getattr(chunk, "content", None)
                    except Exception:
                        token = None
                    if token:
                        tokens.append(token)
                        rec.setdefault("tokens", []).append(token)
                        _qput(token)
                rec["final_text"] = "".join(tokens) if tokens else str(final_msg)
            except Exception as e:
                # 스트리밍 실패 시 최종 메시지를 한 번에 출력
                txt = str(final_msg)
                rec["final_text"] = txt
                _qput(txt)
                try:
                    _LOGGER.error(
                        "[STREAMING ERROR] compose streaming failure: %s",
                        str(e),
                    )
                except Exception:
                    pass
        except Exception as e:
            rec["error"] = str(e)
            # Structured logging: capture full stack including ExceptionGroup sub-exceptions
            try:
                loop_info = None
                try:
                    loop = asyncio.get_running_loop()
                    loop_info = f"loop_id={id(loop)}"
                except Exception:
                    loop_info = "loop_id=NA"
                ctx = {
                    "thread": current_thread().name,
                    "loop": loop_info,
                }
                _LOGGER.error(
                    "[STREAMING ERROR] ReAct astream failure | thread=%s | %s | request_head=%r\n%s",
                    ctx["thread"], ctx["loop"], (user_request[:200] if isinstance(user_request, str) else user_request), _format_exception_recursive(e)
                )
            except Exception:
                pass
            # Also surface a short marker to the UI stream so user sees something immediate
            _qput("\n[에러] streaming failure - see frontend/logs/streaming.log")
        finally:
            done.set()

    thread = Thread(target=lambda: asyncio.run(_run_async()), daemon=True)
    thread.start()

    aggregated: List[str] = []
    while not (done.is_set() and token_queue.empty()):
        try:
            token = token_queue.get(timeout=0.05)
            aggregated.append(token)
            yield token
        except Empty:
            time.sleep(0.01)

    if not aggregated:
        final_text = rec.get("final_text")
        if final_text:
            yield final_text
