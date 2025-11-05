from __future__ import annotations

from typing import List, Tuple

MessageTuple = Tuple[str, str]


# ---------------------------------------------------------------------------
# 대화 요약 관리 모듈
# ---------------------------------------------------------------------------
# 오래된 대화 로그를 요약하여 세션 상태에 축약 정보를 보관하고,
# 최근 N턴만 원본 메시지를 유지한다. Streamlit 앱에서는
# summarize_trigger_turns(요약 발동 턴 수)과 recent_turn_window(최근 유지 턴 수)를
# 조절하면서 이 로직을 사용한다.
# ---------------------------------------------------------------------------


def _count_user_turns(messages: List[MessageTuple]) -> int:
    """사용자 발화 수를 셉니다."""
    return sum(1 for role, _ in messages if role == "user")

def maybe_update_summary(
    summary_text: str | None,
    messages: List[MessageTuple],
    recent_turn_window: int,
    summarize_trigger_turns: int,
    model,
) -> tuple[str | None, List[MessageTuple]]:
    """대화 길이가 요약 기준을 넘으면 오래된 부분을 LLM으로 요약한다."""
    turns = _count_user_turns(messages)
    if turns <= summarize_trigger_turns:
        return summary_text, messages

    # 오래된 부분은 요약하고, 최근 부분(recent_part)은 그대로 유지한다.
    keep_items = max(0, 2 * recent_turn_window)
    old_part = messages[:-keep_items] if keep_items else messages
    recent_part = messages[-keep_items:] if keep_items else []

    if not old_part:
        return summary_text, messages

    # 요약을 위한 평문 텍스트 구성
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
        # 실패 시 기존 요약과 전체 메시지를 그대로 유지
        return summary_text, messages
