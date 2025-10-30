from __future__ import annotations

import asyncio
from threading import Thread, Event
from queue import Queue, Empty
import time
from typing import Dict, Any, Generator, List, Set

from langgraph.prebuilt import create_react_agent
from langchain_core.callbacks import BaseCallbackHandler


class UIStreamingCallbackHandler(BaseCallbackHandler):
    """Callback handler to stream tokens into a queue and record tool usage."""

    def __init__(self, token_queue: Queue, done_event: Event, rec: Dict[str, Any]):
        # rec: {"tokens": list[str], "used_tools": set[str], "tool_details": list[dict]}
        self.token_queue = token_queue
        self.done_event = done_event
        self.rec = rec

    # LLM token stream
    def on_llm_new_token(self, token: str, **kwargs):  # type: ignore[override]
        try:
            if token:
                self.rec.setdefault("tokens", []).append(token)
                self.token_queue.put(token)
        except Exception:
            # don't break the stream on callback issues
            pass

    def on_tool_start(self, serialized=None, input_str=None, **kwargs):  # type: ignore[override]
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

    # Keep other lifecycle hooks as no-ops to avoid noise


def stream_agent_generator(
    lc_messages: List[Dict[str, Any]],
    rec: Dict[str, Any],
    model,
    client,
) -> Generator[str, None, None]:
    """Run the async agent in a background thread and yield tokens for Streamlit.

    The 'rec' dict is mutated to include final_text, tokens, and tool details.
    """
    token_queue: Queue[str] = Queue()
    done = Event()

    handler = UIStreamingCallbackHandler(token_queue, done, rec)

    async def _run_async():
        tools = await client.get_tools()
        agent = create_react_agent(model, tools)
        try:
            result = await agent.ainvoke({"messages": lc_messages}, config={"callbacks": [handler]})
            final_text = None
            if isinstance(result, dict) and result.get("messages"):
                final = result["messages"][-1]
                final_text = getattr(final, "content", None) or str(final)
            rec["final_text"] = final_text
        except Exception as e:
            rec["error"] = str(e)
            token_queue.put(f"\n[에러] {e}")
        finally:
            done.set()

    # Start async work in a separate thread
    thread = Thread(target=lambda: asyncio.run(_run_async()), daemon=True)
    thread.start()

    # Yield tokens as they arrive
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
