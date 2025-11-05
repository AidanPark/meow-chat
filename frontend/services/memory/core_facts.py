from __future__ import annotations

"""
핵심 사실 코어 슬롯 빌더
- 대상: 프로필, 알레르기, 만성질환, 금기, 복용약, 식단 등 항상 포함해야 하는 안전/정책성 정보
- 접근: 키워드 기반 멀티 쿼리로 관련 메모리를 수집(저장소 전면 조회 API 부재로 우회),
        간단 요약/중복 제거 후 토큰 예산 내로 압축
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from .memory_retriever import retrieve_memories
from .memory_utils import trim_memory_block

# 한국어 키워드(1차 근사). 스키마(type 메타) 정착 전까지 사용
CORE_QUERIES = [
    "프로필", "품종", "중성화", "성별", "생일", "연령",
    "알레르기", "과민", "부작용",
    "만성", "진단", "질환", "병력",
    "금기", "주의",
    "복용", "약", "투약", "용량",
    "식단", "사료", "영양제",
]


def _dedup_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for it in items:
        k = it.strip()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(k)
    return out


def build_pinned_core_facts_block(
    user_id: str,
    user_message: str,
    summary_text: Optional[str],
    model,
    max_tokens: int = 400,
    per_item_cap: int = 160,
    *,
    max_queries: int = 6,
    owner_id: Optional[str] = None,
    cat_id: Optional[str] = None,
    importance_min: float = 0.8,
) -> Optional[str]:
    """핵심 사실 블록을 생성합니다.
    1) 다중 키워드로 검색하여 관련 메모리를 수집
    2) 간단 정제/중복 제거
    3) 토큰 예산 내로 트리밍
    """
    # 1) 검색 수집
    # 질의 수를 제한하여 검색 비용을 제어
    queries = CORE_QUERIES[: max(1, int(max_queries))]
    candidates: List[str] = []
    for q in queries:
        try:
            # 요약 텍스트를 포함하여 질의 재작성 품질 향상 + 메타 필터로 범위 축소
            # 프로필만으로 제한하던 필터를 완화하여, 핵심 키워드가 포함된 다양한 유형을 포괄합니다.
            filters: Dict[str, Any] = {}
            if owner_id:
                filters["owner_id"] = owner_id
            if cat_id:
                filters["cat_id"] = cat_id
            results = retrieve_memories(user_id=user_id, user_message=f"{q} {user_message}", summary_text=summary_text, k=6, filters=filters)
            texts = [r.get("content", "").strip() for r in results if (r.get("content") or "").strip()]
            candidates.extend(texts)
        except Exception:
            continue

    if not candidates:
        return None

    # 2) 정제/중복 제거 + 중요도 임계치 필터(메타가 있을 경우)
    #    retrieve_memories는 content만 꺼내오므로 importance는 재조회 없이 판단하기 어렵다.
    #    간단하게는 텍스트에 'profile' 키워드 기반 검색을 사용했고, 중요도 보장은 저장 시 정책으로 확보합니다.
    #    필요 시 store.retrieve에서 importance를 메타에 포함시켜 반환하도록 확장 가능합니다.
    candidates = _dedup_keep_order(candidates)

    # 3) 토큰 예산 트리밍(문자 기반 근사/슬라이더 값 사용)
    joined = "\n".join(f"- {c}" for c in candidates[:20])
    block = joined
    trimmed_list = trim_memory_block([block], max_tokens=max_tokens, per_item_token_cap=per_item_cap)
    return trimmed_list[0] if trimmed_list else None
