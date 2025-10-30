from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from .memory_store import get_memory_store

MEMORY_TYPES = [
    "profile", "allergy", "chronic", "contraindication", "medication", "diet",
    "fact", "preference", "constraint", "decision", "todo", "timeline", "note",
]


def _year_from_timestamp(ts: Optional[str]) -> Optional[int]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).year
    except Exception:
        return None


def search_memories(
    user_id: str,
    query: str = "",
    types: Optional[List[str]] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """장기 메모리에서 키워드/타입/연도 범위로 검색합니다. 백엔드별로 후처리 필터를 적용합니다."""
    store = get_memory_store()
    q = query.strip() or "*"
    # 넉넉히 가져온 뒤 파이썬에서 필터링
    raw = store.retrieve(user_id=user_id, query=q, k=max(limit * 4, 50))

    def _ok(rec: Dict[str, Any]) -> bool:
        if types:
            rtype = rec.get("type")
            if rtype not in types:
                return False
        y = _year_from_timestamp(rec.get("timestamp"))
        if year_from is not None and (y is None or y < year_from):
            return False
        if year_to is not None and (y is None or y > year_to):
            return False
        return True

    out = [r for r in raw if _ok(r)]
    # 상위 limit개만 반환
    return out[:limit]
