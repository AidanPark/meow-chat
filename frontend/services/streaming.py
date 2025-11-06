from __future__ import annotations

import asyncio
from threading import Thread, Event, current_thread
from queue import Queue, Empty
import time
from typing import Dict, Any, Generator, List, Set
from collections import deque, deque as _deque_type
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
# 스트리밍 예외 로깅 설정(콘솔 + 파일)
# ------------------------------------------------------------
_LOGGER = logging.getLogger("meow.frontend.streaming")
if not _LOGGER.handlers:
    _LOGGER.setLevel(logging.INFO)
    # 콘솔 핸들러
    _ch = logging.StreamHandler()
    _ch.setLevel(logging.INFO)
    _fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    _ch.setFormatter(_fmt)
    _LOGGER.addHandler(_ch)

    # 파일 핸들러: frontend/logs/
    try:
        _BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # frontend/
        _LOG_DIR = os.path.join(_BASE_DIR, "logs")
        os.makedirs(_LOG_DIR, exist_ok=True)
        _fh = logging.FileHandler(os.path.join(_LOG_DIR, "streaming.log"))
        _fh.setLevel(logging.INFO)
        _fh.setFormatter(_fmt)
        _LOGGER.addHandler(_fh)
    except Exception:
        # 파일 핸들러 실패 시(권한 등) 콘솔 로깅만 사용
        pass


def _format_exception_recursive(exc: BaseException) -> str:
    """예외를 포맷합니다. ExceptionGroup를 재귀적으로 펼쳐 하위 예외까지 캡처합니다."""
    lines: List[str] = []
    try:
        lines.append("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    # Python 3.11 ExceptionGroup 호환 처리
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
    """LangGraph 에이전트를 비동기로 실행하고 토큰을 스트리밍으로 방출합니다."""
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
    last_heartbeat = time.time()
    while not (done.is_set() and token_queue.empty()):
        try:
            token = token_queue.get(timeout=0.05)
            if token:
                aggregated.append(token)
                yield token
            else:
                # 빈 토큰(하트비트 등)은 렌더 트리거로만 사용하고 누적하지 않음
                yield ""
        except Empty:
            # 주기적 하트비트로 UI 갱신 트리거
            if not done.is_set() and (time.time() - last_heartbeat) >= 0.2:
                last_heartbeat = time.time()
                yield ""
            else:
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

    # 오케스트레이터 메모리 내 로그 버퍼(최대 1000줄)
    orch_ring: _deque_type[str] = deque(maxlen=1000)
    # 호출 측에서 사이드바 UI 갱신 시 사용하도록 노출
    try:
        rec["orchestrator_logs"] = orch_ring
    except Exception:
        pass

    class InMemoryBufferHandler(logging.Handler):
        def __init__(self, ring: _deque_type[str]):
            super().__init__(level=logging.INFO)
            self.ring = ring
            fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
            self.setFormatter(fmt)

        def emit(self, record: logging.LogRecord) -> None:  # type: ignore[override]
            try:
                msg = self.format(record)
                self.ring.append(msg)
            except Exception:
                # 로깅 실패는 무시
                pass

    async def _run_async():
        try:
            # 이번 실행에 한해 오케스트레이터 로거에 메모리 핸들러 부착
            _logger = logging.getLogger("meow.frontend.orchestrator")
            _handler = InMemoryBufferHandler(orch_ring)
            _handler.setLevel(logging.INFO)
            _logger.addHandler(_handler)
            # 플래너/셀프평가는 최종 모델과 동일 모델을 사용 (롤백)
            planner_model = model
            evaluator_model = model
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
            # 진행 로그 내부 수집은 제거되었고, UI는 사이드바로만 표시합니다.
            def _preview_args(a: Any, maxlen: int = 180) -> str:
                try:
                    import json as __json
                    s = __json.dumps(a, ensure_ascii=False)
                except Exception:
                    s = str(a)
                return (s if len(s) <= maxlen else (s[:maxlen] + "…"))

            for _ in range(int(max_iters)):
                state = await react_plan_node(state, model, client)
                finish_hint = state.get("react_finish")
                plan = state.get("plan") or {}
                steps = plan.get("steps") or []
                # 계획/실행 진행 로그 수집/스트림은 비활성화했습니다.
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
                    # 실행/관찰 진행 로그의 본문 스트림 출력은 비활성화했습니다.

                state = await react_self_eval_node(state, model)
                cont = bool(state.get("react_should_continue"))
                if cont:
                    continue
                break

            # 최종 메시지 합성
            state = react_compose_node(state)
            final_msg = state.get("message") or ""
            outs = state.get("outputs") or {}
            errs = state.get("errors") or []
            # 하이브리드 규칙 적용:
            # - 작은 인사/스몰토크(도구 사용 없음) + 계획 finish(message) → verbatim 출력
            # - 도구 사용이 포함되면(steps/execute됨) → 아래 일반 합성/리라이팅 경로를 사용
            try:
                finish_hint = state.get("react_finish") or {}
            except Exception:
                finish_hint = {}
            try:
                tools_used = state.get("tools_used") or []
            except Exception:
                tools_used = []
            if isinstance(finish_hint, dict) and (finish_hint.get("use") == "message") and (not tools_used):
                if isinstance(final_msg, str) and final_msg.strip():
                    rec["final_text"] = final_msg
                    try:
                        token_queue.put(final_msg)
                    except Exception:
                        pass
                    return
            # 랩리포트 저장 성공 여부 및 요약을 rec로 전달
            try:
                vars_map = state.get("vars") or {}
                saved = bool(vars_map.get("_lab_report_saved"))
                if saved:
                    rec["lab_report_saved"] = True
                    summ = vars_map.get("_lab_report_saved_summary")
                    if summ:
                        # 통일된 인터페이스: rec["saved_memories"] = [ {type, dates, row_count, ...} ]
                        arr = rec.setdefault("saved_memories", [])
                        arr.append(summ)
            except Exception:
                pass

            # 스몰토크/무플랜 폴백: 모델 스트리밍으로 직접 응답 생성
            no_effective_plan = (not final_msg or str(final_msg).strip() in ("", "실행할 계획이 없었습니다.")) and (not outs) and (not errs)
            if no_effective_plan:
                # '전담 주치의' 페르소나 기반 스몰토크 폴백으로 복원
                sys_prompt = (
                    "당신은 사용자의 고양이를 유아기부터 지속적으로 케어해 온 '전담 주치의'입니다.\n"
                    "톤: 따뜻하고 공감적이되, 의학적 판단/설명은 전문적이고 침착하게.\n"
                    "작은 인사/잡담에도 친근히 응답하되, 불필요한 도구 계획 없이 바로 답변만 출력하세요."
                )
                vars_map = dict(extra_vars or {})
                # 활성 프로필명을 호칭으로 사용
                try:
                    _user_name = vars_map.get("user_id")
                    if isinstance(_user_name, str) and _user_name.strip():
                        sys_prompt += f"\n[호칭 지침]\n- 사용자를 '{_user_name.strip()}'님으로 호칭하세요. '사용자' 대신 프로필명을 사용합니다.\n"
                except Exception:
                    pass
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
                        try:
                            token_queue.put(token)
                        except Exception:
                            pass
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

                # 랩 리포트 특화 합성: lab_env 또는 extract_lab_report 관찰이 있으면 전문 프롬프트 사용으로 복원
                def _get_merge_env() -> Any:
                    try:
                        vmap = state.get("vars") or {}
                        env = vmap.get("lab_env")
                        if env is None:
                            outs = state.get("outputs") or {}
                            env = outs.get("extract_lab_report")
                        # 문자열이면 JSON 파싱 시도
                        if isinstance(env, str):
                            import json as __json
                            try:
                                env = __json.loads(env)
                            except Exception:
                                return None
                        return env
                    except Exception:
                        return None

                merge_env = _get_merge_env()
                use_lab_prompt = False
                if isinstance(merge_env, dict) and merge_env.get("stage") == "merge":
                    use_lab_prompt = True

                # 공통: 호칭/개인화 컨텍스트
                sys_greeting = (
                    "당신은 사용자의 고양이를 아주 어릴 때부터 지금까지 돌봐 온 '전담 주치의'입니다.\n"
                    "말투는 따뜻하고 공감적이되, 의학적 판단/설명은 전문적이고 침착하게 유지하세요."
                )
                try:
                    _vars_map = dict(extra_vars or {})
                    _user_name = _vars_map.get("user_id")
                    if isinstance(_user_name, str) and _user_name.strip():
                        sys_greeting += f"\n[호칭 지침]\n- 사용자를 '{_user_name.strip()}'님으로 호칭하세요. '사용자' 대신 프로필명을 사용합니다.\n"
                except Exception:
                    pass
                pinned = None
                try:
                    pinned = (extra_vars or {}).get("pinned_core_facts")
                except Exception:
                    pinned = None

                if use_lab_prompt:
                    # 수의사 수준 합성 프롬프트: 표 → 임상 소견 순서, 범위/단위 주의, 개인화 반영
                    sys_prompt = (
                        sys_greeting
                        + "\n수의 내과 전문의로서, 제공된 검사결과 표를 기반으로 안정적이고 재현 가능한 해석을 작성합니다.\n"
                        + "반드시 아래 출력 형식을 지키세요.\n"
                        + "\n[출력 형식]\n"
                        + "1) 데이터프레임 표(마크다운 표 허용): 컬럼 = [항목, 값, 단위, 참고범위, 정상여부, 방향, 중증도]\\n"
                        + "   - 정상여부: 정상|비정상|불명(범위 없음)\\n"
                        + "   - 방향: 상(↑)|하(↓)|-\\n"
                        + "   - 중증도: 경도|중등도|중증 (필요 시)\\n"
                        + "2) 종합 임상 판단과 소견: 병태생리/감별진단 후보/권장 추가검사·관리/주의·한계\\n"
                        + "\n[판정 규칙]\n"
                        + "- 우선 리포트에 포함된 참고범위(reference_min/max 또는 low/high/reference_range)를 기준으로 정상/이상 판정\\n"
                        + "- 범위가 누락되면 '불명(범위 없음)'으로 표기하고 소견에서 출처 부족을 명시\\n"
                        + "- 단위가 의심되면 변환 후보만 제시하고, 원 단위를 유지하여 신중히 기술\\n"
                        + "- 응급/중증 임계값은 보수적으로 표시하되 과장 금지\\n"
                        + "\n[개인화 컨텍스트]\n"
                        + (str(pinned)[:800] if isinstance(pinned, str) else "(없음)")
                    )
                    # 사용자 블록: 요청, 관찰 요약, 그리고 초안(검사항목 표 요약 포함)
                    user_blk = (
                        f"요청: {user_request}\n\n"
                        f"관찰 요약:\n" + ("\n".join(brief_obs) if brief_obs else "(없음)") + "\n\n"
                        f"검사표(초안):\n{final_msg}\n\n"
                        "위의 표를 근거로 [출력 형식]을 그대로 따르세요."
                    )
                else:
                    # 일반 프롬프트(비랩 상황)
                    sys_prompt = (
                        sys_greeting
                        + "\n아래 사용자 요청과 도구 관찰을 참고하여 간결하고 도움되는 답변만 출력하세요."
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
                        try:
                            token_queue.put(token)
                        except Exception:
                            pass
                rec["final_text"] = "".join(tokens) if tokens else str(final_msg)
            except Exception as e:
                # 스트리밍 실패 시 최종 메시지를 한 번에 출력
                txt = str(final_msg)
                rec["final_text"] = txt
                try:
                    token_queue.put(txt)
                except Exception:
                    pass
                try:
                    _LOGGER.error(
                        "[STREAMING ERROR] compose streaming failure: %s",
                        str(e),
                    )
                except Exception:
                    pass
            finally:
                # 핸들러 누수 방지를 위해 분리
                try:
                    _logger.removeHandler(_handler)
                except Exception:
                    pass
        except Exception as e:
            rec["error"] = str(e)
            # 구조화 로깅: ExceptionGroup 하위 예외까지 포함해 전체 스택 캡처
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
            # UI 스트림에 짧은 마커도 흘려 사용자에게 즉시 표기
            # UI 진행 로그 스트림은 비활성화 상태이므로 에러 마커를 토큰 스트림에만 남깁니다.
            try:
                token_queue.put("\n[에러] streaming failure - see frontend/logs/streaming.log")
            except Exception:
                pass
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
