from __future__ import annotations

import sys
import types

try:
    from langchain_core.documents import Document
except Exception as exc:
    raise ImportError(
        "langchain_core.documents.Document 를 임포트할 수 없습니다. "
        "LangChain Core 버전을 확인하세요."
    ) from exc


def ensure_langchain_docstore_shim() -> None:
    module_name = "langchain.docstore.document"
    if module_name in sys.modules:
        return

    pkg_name = "langchain.docstore"
    docstore_pkg = sys.modules.get(pkg_name)
    if docstore_pkg is None:
        docstore_pkg = types.ModuleType(pkg_name)
        sys.modules[pkg_name] = docstore_pkg

    module = types.ModuleType(module_name)
    module.Document = Document
    sys.modules[module_name] = module
    docstore_pkg.document = module  # type: ignore[attr-defined]


ensure_langchain_docstore_shim()
