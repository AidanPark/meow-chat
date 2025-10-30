from __future__ import annotations

"""
장기 메모리 저장소 인터페이스 및 기본 구현(엄격 모드).
- 필수 의존성: Chroma + OpenAIEmbeddings
- 운영 환경에서는 Qdrant/Weaviate/Milvus/pgvector 등으로 교체할 수 있도록 인터페이스를 최소화했습니다.
"""

import os
import uuid
from typing import List, Dict, Any, Optional
from importlib import import_module

try:
    from langchain_openai import OpenAIEmbeddings
except Exception as e:
    raise ImportError(
        "langchain-openai is required. Install with `pip install langchain-openai`."
    ) from e

def _get_chroma_class():
    try:
        mod = import_module("langchain_community.vectorstores")
        return getattr(mod, "Chroma")
    except Exception as e:
        raise ImportError(
            "langchain-community and chromadb are required. Install with `pip install langchain-community chromadb`."
        ) from e


class MemoryStore:
    """메모리 저장/검색을 위한 최소 인터페이스."""

    def upsert_memories(self, user_id: str, memories: List[Dict[str, Any]]) -> List[str]:
        raise NotImplementedError

    def retrieve(self, user_id: str, query: str, k: int = 8, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        raise NotImplementedError


class ChromaMemoryStore(MemoryStore):
    """Chroma 기반 구현.
    - 컬렉션 이름: meow_memory_{user_id}
    - 임베딩: OpenAIEmbeddings 사용
    """

    def __init__(self, base_dir: str = "data/vectors"):
        os.makedirs(base_dir, exist_ok=True)
        self.base_dir = base_dir
        self.embeddings = OpenAIEmbeddings()

    def _collection(self, user_id: str):
        collection_name = f"meow_memory_{user_id}"
        Chroma = _get_chroma_class()
        return Chroma(collection_name=collection_name, embedding_function=self.embeddings, persist_directory=self.base_dir)

    def upsert_memories(self, user_id: str, memories: List[Dict[str, Any]]) -> List[str]:
        col = self._collection(user_id)
        ids = []
        texts = []
        metadatas = []
        for m in memories:
            mid = m.get("id") or str(uuid.uuid4())
            ids.append(mid)
            texts.append(m.get("content", ""))
            md = m.copy()
            md.pop("content", None)
            metadatas.append(md)
        col.add(documents=texts, metadatas=metadatas, ids=ids)
        return ids

    def retrieve(self, user_id: str, query: str, k: int = 8, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        col = self._collection(user_id)
        docs = col.similarity_search(query, k=k, filter=filters)
        results: List[Dict[str, Any]] = []
        for d in docs:
            md = d.metadata or {}
            results.append({
                "id": md.get("id"),
                "content": d.page_content,
                **md,
            })
        return results


def get_memory_store() -> MemoryStore:
    """엄격 모드: 필수 의존성이 없으면 ImportError가 발생합니다."""
    return ChromaMemoryStore()
