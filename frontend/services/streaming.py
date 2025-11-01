from __future__ import annotations

import asyncio
from threading import Thread, Event
from queue import Queue, Empty
import time
from typing import Dict, Any, Generator, List, Set

from langchain_core.callbacks import BaseCallbackHandler
from services.langgraph_compat import create_react_agent_executor

# 이 모듈은 LangGraph 기반 에이전트를 백그라운드 스레드에서 실행하고,
# 얻어진 토큰 스트림을 Streamlit UI에 실시간으로 전달하는 역할을 담당한다.
# - UIStreamingCallbackHandler: LangChain 콜백에서 토큰/도구 사용 정보를 수집
# - stream_agent_generator: 비동기로 에이전트를 돌리고, 큐에 쌓인 토큰을 제너레이터로 방출
# rec 딕셔너리에는 최종 응답 텍스트, 토큰 목록, 사용된 도구 내역 등이 채워져
# 호출 측(frontend/app.py)에서 UI 상태를 업데이트하는 데 활용된다.


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
