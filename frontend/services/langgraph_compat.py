from __future__ import annotations

# ---------------------------------------------------------------------------
# LangGraph / LangChain 호환성 패치 모듈
# ---------------------------------------------------------------------------
# 현재 프로젝트는 LangGraph 1.0.2 + LangChain Core 1.0.1 조합을 사용한다.
# 이 버전 조합에서는 다음 두 가지 문제가 발생한다.
#   1) LangGraph 1.0.2는 langchain_core.tools.base 모듈에
#      `_DirectlyInjectedToolArg` 심볼이 존재한다고 가정하지만,
#      LangChain Core 1.0.x에서는 해당 심볼이 제거되어 ImportError가 발생한다.
#   2) LangGraph 1.0.2가 제공하는 실행기 함수 이름이
#      `create_tool_calling_executor`이며,
#      신규 코드에서 사용하는 `create_react_agent_executor` 이름이 없다.
# 이 파일은 위 두 문제를 런타임에서 보정하여 앱이 정상적으로 동작하도록 한다.
# LangGraph 1.0.3 이상과 LangChain Core가 공식적으로 호환되면
# 이 파일은 제거해도 되며, 그 시점에는 Streaming/Agent 코드도 함께 정리할 것.
# ---------------------------------------------------------------------------

from importlib import import_module


def ensure_tool_arg_alias() -> None:
    tools_base = import_module("langchain_core.tools.base")

    if hasattr(tools_base, "_DirectlyInjectedToolArg"):
        return

    InjectedToolArg = getattr(tools_base, "InjectedToolArg", None)
    if InjectedToolArg is None:
        raise ImportError(
            "langchain_core.tools.base.InjectedToolArg not found. "
            "Update LangChain Core to a compatible version."
        )

    class _DirectlyInjectedToolArg(InjectedToolArg):  # type: ignore[misc]
        # LangChain Core 최신 버전에서 삭제된 심볼을 복원한다.
        # (LangGraph 1.0.2는 이 심볼 존재를 전제로 빌드되어 있음)
        pass

    setattr(tools_base, "_DirectlyInjectedToolArg", _DirectlyInjectedToolArg)


def ensure_react_executor_alias() -> None:
    prebuilt = import_module("langgraph.prebuilt")
    if hasattr(prebuilt, "create_react_agent_executor"):
        return
    chat_exec = import_module("langgraph.prebuilt.chat_agent_executor")
    if hasattr(chat_exec, "create_tool_calling_executor"):
        # LangGraph 1.0.2에서는 이름이 create_tool_calling_executor 로만 존재한다.
        # 서비스 코드가 기대하는 create_react_agent_executor 이름을 임시로 연결한다.
        setattr(prebuilt, "create_react_agent_executor", getattr(chat_exec, "create_tool_calling_executor"))


ensure_tool_arg_alias()
ensure_react_executor_alias()

# Re-export helper for type checkers and consumers.
from langgraph.prebuilt import create_react_agent_executor  # type: ignore  # noqa: E402,F401
