from __future__ import annotations

"""
메모리 블록 토큰 예산 트리머(엄격 모드).
- tiktoken 기반의 정확한 토큰 카운트를 사용합니다.
- 항목당 상한과 전체 블록 상한을 적용해 잘라냅니다.
"""

from typing import List, Optional

import tiktoken  # 정확한 토큰 카운팅 필수 의존성


def _count_tokens(s: str, model_name: Optional[str] = None) -> int:
    s = s or ""
    enc = tiktoken.get_encoding("cl100k_base") if not model_name else tiktoken.encoding_for_model(model_name)
    return len(enc.encode(s))


def trim_memory_block(
    texts: List[str],
    max_tokens: int = 1200,
    per_item_token_cap: int = 150,
    *,
    model_name: Optional[str] = None,
) -> List[str]:
    """텍스트 목록을 토큰 예산 내로 잘라냅니다.

    정책:
    1) 각 항목을 per_item_token_cap으로 1차 절단(토큰 기준)
    2) 누적 토큰이 max_tokens를 넘지 않도록 순차적으로 채움
    3) 마지막 항목에서 약간의 절단을 허용하여 예산을 맞춤
    """
    if not texts:
        return []

    # 1차: 항목별 토큰 상한 적용
    capped: List[str] = []
    for t in texts:
        if not t:
            continue
        if _count_tokens(t, model_name) > per_item_token_cap:
            # 대략적으로 토큰 상한에 맞춰 인코딩 기반 슬라이싱
            enc = tiktoken.get_encoding("cl100k_base") if not model_name else tiktoken.encoding_for_model(model_name)
            ids = enc.encode(t)
            capped.append(enc.decode(ids[:per_item_token_cap]) + "…")
        else:
            capped.append(t)

    # 2차: 전체 블록 상한 적용
    out: List[str] = []
    used = 0
    for t in capped:
        t_tokens = _count_tokens(t, model_name)
        if used + t_tokens <= max_tokens:
            out.append(t)
            used += t_tokens
            continue
        # 남은 예산에 맞춰 마지막 항목을 절단 시도
        remaining = max(0, max_tokens - used)
        if remaining <= 0:
            break
        enc = tiktoken.get_encoding("cl100k_base") if not model_name else tiktoken.encoding_for_model(model_name)
        ids = enc.encode(t)
        if remaining <= 1:
            break
        out.append(enc.decode(ids[:remaining]) + "…")
        used = max_tokens
        break

    return out
