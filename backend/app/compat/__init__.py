"""LangChain 관련 호환성 패치 모듈."""

from .langchain_docstore import ensure_langchain_docstore_shim  # noqa: F401
from .langchain_text_splitter import ensure_text_splitter_shim  # noqa: F401
