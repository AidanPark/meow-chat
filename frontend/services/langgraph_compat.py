from __future__ import annotations

"""Compatibility helpers for LangGraph against newer LangChain releases.

LangGraph's prebuilt executors (<=1.0.2) expect ``langchain_core.tools.base`` to
expose the private symbol ``_DirectlyInjectedToolArg``. This attribute was
renamed/removed in LangChain Core 0.3.7x+, causing ImportError during import.

Import this module before ``langgraph.prebuilt`` to patch the missing symbol.
"""

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
        """Backwards-compatible alias for LangGraph < 1.0.3."""

        pass

    setattr(tools_base, "_DirectlyInjectedToolArg", _DirectlyInjectedToolArg)


def ensure_react_executor_alias() -> None:
    prebuilt = import_module("langgraph.prebuilt")
    if hasattr(prebuilt, "create_react_agent_executor"):
        return
    chat_exec = import_module("langgraph.prebuilt.chat_agent_executor")
    if hasattr(chat_exec, "create_tool_calling_executor"):
        setattr(prebuilt, "create_react_agent_executor", getattr(chat_exec, "create_tool_calling_executor"))


ensure_tool_arg_alias()
ensure_react_executor_alias()
