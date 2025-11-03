from __future__ import annotations

"""
메모리 리트리버: 현재 쿼리(사용자 입력+요약)에 기반해 장기 메모리에서 Top-K 항목을 검색합니다.
혼합 스코어링(time/importance)은 저장소에서 제공되는 경우 활용하고, 기본 구현은 유사도 중심입니다.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from .memory_store import get_memory_store


def rewrite_query(user_message: str, summary_text: str | None) -> str:
    """요약 텍스트가 있으면 쿼리에 보강하여 검색 품질을 높입니다."""
    if summary_text:
        return f"요약: {summary_text}\n\n질문: {user_message}"
    return user_message


def retrieve_memories(user_id: str, user_message: str, summary_text: str | None, k: int = 8, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """장기 메모리에서 관련 항목 Top-K를 검색합니다.

    filters: 메타데이터 기반 필터(예: {"type": "profile", "owner_id": "owner:aidan", "cat_id": "cat:momo"})
    """
    store = get_memory_store()
    query = rewrite_query(user_message, summary_text)
    results = store.retrieve(user_id=user_id, query=query, k=k, filters=filters)
    return results


def write_memories(user_id: str, memories: List[Dict[str, Any]]) -> List[str]:
    """추출된 메모리를 저장소에 기록합니다. 간단 중복 방지와 필드 정규화 포함."""
    if not memories:
        return []
    store = get_memory_store()
    now = datetime.utcnow().isoformat()
    saved_ids: List[str] = []

    for m in memories:
        content = (m.get("content") or "").strip()
        if not content:
            continue
        # 간단 중복 체크: 동일 텍스트가 이미 존재하는지 확인(similarity 검색 후 내용 일치 검사)
        try:
            exist = store.retrieve(user_id=user_id, query=content, k=1)
            if exist and (exist[0].get("content") or "").strip() == content:
                continue
        except Exception:
            pass
        md = m.copy()
        md["content"] = content
        # 타입/중요도 기본값 보강
        md.setdefault("type", "fact")
        md.setdefault("importance", 0.5)
        md.setdefault("timestamp", now)
        md.setdefault("user_id", user_id)
        try:
            ids = store.upsert_memories(user_id=user_id, memories=[md])
            saved_ids.extend(ids)
        except Exception:
            continue
    return saved_ids
