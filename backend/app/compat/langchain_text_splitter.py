from __future__ import annotations

import sys
import types

from langchain_text_splitters import RecursiveCharacterTextSplitter


def ensure_text_splitter_shim() -> None:
    module_name = "langchain.text_splitter"
    if module_name in sys.modules:
        return

    langchain_pkg = sys.modules.get("langchain")
    if langchain_pkg is None:
        import langchain as langchain_pkg  # type: ignore[no-redef]

    module = types.ModuleType(module_name)
    module.RecursiveCharacterTextSplitter = RecursiveCharacterTextSplitter
    sys.modules[module_name] = module
    setattr(langchain_pkg, "text_splitter", module)


ensure_text_splitter_shim()
