from __future__ import annotations

from typing import List, Tuple

MessageTuple = Tuple[str, str]


def _count_user_turns(messages: List[MessageTuple]) -> int:
    # Count user messages as turns; assumes alternating user/assistant
    return sum(1 for role, _ in messages if role == "user")


def _prune_history(messages: List[MessageTuple], recent_turn_window: int) -> List[MessageTuple]:
    keep = max(0, 2 * recent_turn_window)
    return messages[-keep:] if keep else []


def maybe_update_summary(
    summary_text: str | None,
    messages: List[MessageTuple],
    recent_turn_window: int,
    summarize_trigger_turns: int,
    model,
) -> tuple[str | None, List[MessageTuple]]:
    """If turn count exceeds threshold, summarize older part and prune history.

    Returns: (new_summary_text, pruned_messages)
    """
    turns = _count_user_turns(messages)
    if turns <= summarize_trigger_turns:
        # No change
        return summary_text, messages

    # Split into old part (to summarize) and recent part to keep
    keep_items = max(0, 2 * recent_turn_window)
    old_part = messages[:-keep_items] if keep_items else messages
    recent_part = messages[-keep_items:] if keep_items else []

    if not old_part:
        return summary_text, messages

    # Build plain text for summarization
    old_text = []
    for role, content in old_part:
        role_k = "사용자" if role == "user" else "어시스턴트"
        old_text.append(f"[{role_k}] {content}")
    old_text_str = "\n".join(old_text)

    system = {
        "role": "system",
        "content": (
            "당신은 대화 요약가입니다. 오래된 대화 로그에서 핵심 사실, 결정, 선호, 제약, 중요한 이벤트를\n"
            "간결하고 자체완결적으로 요약하세요. 불필요한 세부를 줄이고, 향후 대화에 유용한 내용 중심으로 정리합니다."
        ),
    }
    user = {
        "role": "user",
        "content": (
            "다음 대화 로그를 요약해 주세요.\n\n" + old_text_str
        ),
    }

    try:
        resp = model.invoke([system, user])
        new_summary = getattr(resp, "content", None) or str(resp)
        if summary_text:
            merged = summary_text.strip() + "\n\n" + new_summary.strip()
        else:
            merged = new_summary.strip()
        return merged, recent_part
    except Exception:
        # On failure, keep prior summary and full messages
        return summary_text, messages
