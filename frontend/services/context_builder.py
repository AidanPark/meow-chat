from __future__ import annotations

from typing import List, Tuple, Dict, Any, Optional

MessageTuple = Tuple[str, str]  # (role, content)


def _last_n_turns(messages: List[MessageTuple], n_turns: int) -> List[MessageTuple]:
    # A turn is typically (user, assistant). We keep last 2*n items.
    keep = max(0, 2 * n_turns)
    return messages[-keep:] if keep else []


def build_context_messages(
    summary_text: str | None,
    history_messages: List[MessageTuple],
    new_user_message: str,
    recent_turn_window: int = 10,
    retrieved_memories: Optional[List[str]] = None,
    pinned_core_facts: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """LLM 입력 메시지 조립: system 요약 + (선택)핵심 사실 + (선택)장기 메모리 + 최근 N턴 + 신규 사용자 입력.

    - summary_text: 롤링 요약 문자열(선택)
    - history_messages: (role, content) 목록
    - new_user_message: 현재 사용자 입력
    - recent_turn_window: 최근 N턴 유지(턴= user+assistant 2개 메시지)
    - retrieved_memories: 장기 메모리에서 검색된 텍스트 목록(선택)
    """
    lc_messages: List[Dict[str, Any]] = []

    if summary_text:
        lc_messages.append({
            "role": "system",
            "content": (
                "아래 요약은 이전 대화의 핵심 맥락입니다. 이를 반영해 응답하세요.\n" + summary_text
            ),
        })

    # 고정 핵심 사실 블록을 system에 포함(선택)
    if pinned_core_facts:
        lc_messages.append({
            "role": "system",
            "content": (
                "아래는 이 사용자/반려묘에 대한 핵심 사실 요약입니다. 반드시 우선적으로 고려하세요.\n" + pinned_core_facts
            ),
        })

    # 장기 메모리 블록을 system에 포함(선택)
    if retrieved_memories:
        memories_block = "\n".join(f"- {m}" for m in retrieved_memories if m)
        lc_messages.append({
            "role": "system",
            "content": (
                "아래 항목은 과거 대화에서 검색된 관련 장기 메모리입니다. 필요 시 참고하여 응답하세요.\n" + memories_block
            ),
        })

    recent = _last_n_turns(history_messages, recent_turn_window)
    for role, content in recent:
        # ensure only user/assistant roles are forwarded
        if role in ("user", "assistant"):
            lc_messages.append({"role": role, "content": content})

    lc_messages.append({"role": "user", "content": new_user_message})
    return lc_messages
