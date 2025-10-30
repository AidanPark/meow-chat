from __future__ import annotations

from typing import Any, Dict, List, Tuple

from langgraph.prebuilt import create_react_agent


async def run_agent(user_message: str, model, client) -> Tuple[str, List[str], List[Dict[str, Any]]]:
    """Run the ReAct agent once and return final text + tool usage details."""
    tools = await client.get_tools()
    agent = create_react_agent(model, tools)

    result = await agent.ainvoke({
        "messages": [
            {"role": "user", "content": user_message}
        ]
    })

    used_tools: List[str] = []
    tool_details: List[Dict[str, Any]] = []

    if isinstance(result, dict) and "messages" in result:
        for msg in result["messages"]:
            tcalls = getattr(msg, "tool_calls", None)
            if tcalls:
                for t in tcalls:
                    name = t.get("name", "unknown")
                    args = t.get("args", {})
                    used_tools.append(name)
                    tool_details.append({"name": name, "args": args})

    final_text = None
    if isinstance(result, dict) and result.get("messages"):
        final = result["messages"][-1]
        final_text = getattr(final, "content", None) or str(final)

    return final_text or "응답을 생성하지 못했습니다.", used_tools, tool_details
