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
    # 프로필/기본 정보
    "프로필", "품종", "중성화", "성별", "생일", "연령",
    # 체중/몸무게(회상 강화를 위해 명시적 키워드 추가)
    "몸무게", "체중", "킬로그램", "weight", "kg",
    # 안전/의료
    "알레르기", "과민", "부작용",
    "만성", "진단", "질환", "병력",
    "금기", "주의",
    # 약/식단
    "복용", "약", "투약", "용량",
    "식단", "사료", "영양제",
]


def _normalize_for_compare(text: str) -> str:
    """중복 비교용 정규화 함수
    - 앞머리 라벨(예: '사실:', '프로필:')은 비교 시 제거
    - 공백/구두점/불릿 차이로 인한 미묘한 중복을 줄이기 위해 최소 정규화 수행
    주의: 표시는 원문 그대로 유지하며, 비교에만 사용합니다.
    """
    import re

    s = (text or "").strip()
    # 불릿/대시 제거
    s = re.sub(r"^[-•\s]+", "", s)
    # 번호 매김 제거 (예: "1.", "2)")
    s = re.sub(r"^\d+[\.)]\s*", "", s)
    # 대표 라벨 제거 (비교용). 한국어/영문 혼용 케이스 최소 대응
    s = re.sub(r"^(사실|프로필|profile|fact)\s*[:：]\s*", "", s, flags=re.IGNORECASE)
    # 불필요한 접두어 정규화(비교용)
    s = s.replace("사용자의 집 ", "")
    # 고양이 이름 문장 정규화(비교용): "고양이 이름은 옹심이다/입니다/임" → "고양이 이름은 옹심"
    s = re.sub(r"^(고양이\s*이름은)\s*(.+?)\s*(이다|입니다|임)[\.!\s]*$", r"\1 \2", s, flags=re.IGNORECASE)
    # 끝의 마침표/불필요 공백 제거
    s = re.sub(r"[\.!\s]+$", "", s)
    # 다중 공백 축소
    s = re.sub(r"\s+", " ", s)
    return s


def _dedup_keep_order(items: List[str]) -> List[str]:
    """순서를 유지하면서 중복 제거
    - 완전 동일 문자열은 제거
    - 위 정규화 기준으로도 중복으로 간주하여 제거(예: '사실: X' vs 'X')
    """
    seen_raw = set()
    seen_norm = set()
    out: List[str] = []
    for it in items:
        k = (it or "").strip()
        if not k:
            continue
        norm = _normalize_for_compare(k)
        if k in seen_raw or norm in seen_norm:
            continue
        seen_raw.add(k)
        seen_norm.add(norm)
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
            # 'todo' 항목은 개인화 고정 블록에서 제외
            texts = []
            for r in results:
                txt = (r.get("content") or "").strip()
                if not txt:
                    continue
                rtype = (r.get("type") or "").strip()
                if rtype.lower() == "todo":
                    continue
                texts.append(txt)
            candidates.extend(texts)
        except Exception:
            continue

    if not candidates:
        return None

    # 2) 정제/중복 제거 + 중요도 임계치 필터(메타가 있을 경우)
    #    retrieve_memories는 content만 꺼내오므로 importance는 재조회 없이 판단하기 어렵습니다.
    #    중요도는 저장 정책(importance>=0.8 선별)으로 보장하고, 여기서는 중복 제거에 집중합니다.
    candidates = _dedup_keep_order(candidates)

    # 3) 토큰 예산 트리밍(문자 기반 근사/슬라이더 값 사용)
    joined = "\n".join(f"- {c}" for c in candidates[:20])
    block = joined
    trimmed_list = trim_memory_block([block], max_tokens=max_tokens, per_item_token_cap=per_item_cap)
    return trimmed_list[0] if trimmed_list else None
