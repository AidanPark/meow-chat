# 이 파일은 프론트엔드에서 ReAct 기반 LLM 에이전트(LangGraph 등)를 실행하는 핵심 유틸리티입니다.
# 주요 역할:
# - run_agent 함수: 사용자 메시지, 모델, 클라이언트를 받아 비동기적으로 에이전트 실행
# - LangGraph의 ReAct 에이전트 실행(executor) 생성 및 메시지 전달
# - 에이전트가 사용한 툴 목록과 각 툴의 호출 상세 정보(이름, 인자)를 추출
# - 최종 응답 텍스트(에이전트의 마지막 메시지)와 툴 사용 내역을 반환
# 즉, 챗봇/에이전트가 사용자 입력을 받아 LLM 기반 추론 및 툴 호출을 수행하고, 결과와 툴 사용 내역을 프론트엔드에 전달하는 역할
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from services.langgraph_compat import create_react_agent_executor


async def run_agent(user_message: str, model, client) -> Tuple[str, List[str], List[Dict[str, Any]]]:
    # ReAct 에이전트를 한 번 실행하고, 최종 응답 텍스트와 툴 사용 내역을 반환합니다.
    tools = await client.get_tools()

    agent = create_react_agent_executor(model, tools)

    result = await agent.ainvoke({
        "messages": [
            {"role": "user", "content": user_message}
        ]
    })

    used_tools: List[str] = []
    tool_details: List[Dict[str, Any]] = []

    messages = None
    if isinstance(result, dict):
        messages = result.get("messages") or result.get("outputs")
    elif isinstance(result, list):
        messages = result

    if messages:
        for msg in messages:
            tcalls = getattr(msg, "tool_calls", None)
            if tcalls:
                for t in tcalls:
                    name = t.get("name", "unknown")
                    args = t.get("args", {})
                    used_tools.append(name)
                    tool_details.append({"name": name, "args": args})

    final_text = None
    if messages:
        final = messages[-1]
        final_text = getattr(final, "content", None) or str(final)

    return final_text or "응답을 생성하지 못했습니다.", used_tools, tool_details
