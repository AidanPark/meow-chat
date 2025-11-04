from __future__ import annotations

"""
메모리 작성기: 각 턴 이후 대화에서 기억할 가치가 있는 내용을 추출하여 저장 형식으로 변환합니다.
간단한 1차 구현으로, LLM에 요약/추출을 요청해 라인 단위 항목을 생성합니다.
운영에서는 휴리스틱/스키마 기반 정규화, 중요도 추정 고도화가 가능합니다.
"""

from typing import List, Dict, Any, Tuple

MessageTuple = Tuple[str, str]


def _normalize_text(s: str) -> str:
    return " ".join((s or "").strip().split())


def _infer_type(text: str) -> str:
    t = text.lower()
    # 간단 휴리스틱 기반 타입 추정
    if any(k in t for k in ["알레르기", "과민", "부작용", "allergy"]):
        return "allergy"
    if any(k in t for k in ["만성", "진단", "질환", "병력", "diagnosis", "chronic"]):
        return "chronic"
    if any(k in t for k in ["금기", "주의", "contraindication", "금지", "피해야"]):
        return "contraindication"
    if any(k in t for k in ["복용", "약", "투약", "용량", "med", "dosage"]):
        return "medication"
    if any(k in t for k in ["식단", "사료", "영양제", "diet", "food"]):
        return "diet"
    # 기본 프로필: 이름/나이/성별/중성화/성격/몸무게 등 포함
    if any(k in t for k in [
        "프로필", "품종", "성별", "중성화", "생일", "연령", "profile",
        "이름", "name", "성격", "temperament", "몸무게", "체중", "weight", "kg",
    ]):
        return "profile"
    # 선호/의사결정/제약/할일/타임라인 등 추가 유형
    if any(k in t for k in ["선호", "좋아", "싫어", "preference"]):
        return "preference"
    if any(k in t for k in ["결정", "정하기", "의사결정", "decision"]):
        return "decision"
    if any(k in t for k in ["제약", "제한", "constraint", "cannot", "하지 말"]):
        return "constraint"
    if any(k in t for k in ["할일", "todo", "해야", "할 예정", "일정"]):
        return "todo"
    if any(k in t for k in ["타임라인", "timeline", "기록", "지난", "과거"]):
        return "timeline"
    return "fact"


def _importance_for_type(t: str) -> float:
    # 안전/의료 관련 우선순위 가중치
    weights = {
        "contraindication": 0.95,
        "allergy": 0.9,
        "medication": 0.85,
        "chronic": 0.8,
        "diet": 0.7,
        # 기본 프로필은 프롬프트 기본 포함을 위해 가중치 상향
        "profile": 0.85,
        "fact": 0.5,
        "preference": 0.45,
        "decision": 0.5,
        "constraint": 0.7,
        "todo": 0.45,
        "timeline": 0.5,
        "note": 0.4,
    }
    return weights.get(t, 0.5)


def extract_candidates(recent_turns: List[MessageTuple], assistant_reply: str, model) -> List[Dict[str, Any]]:
    """
    최근 턴과 어시스턴트 응답을 바탕으로 저장할 후보 메모리를 추출합니다.
    출력 형식(간단): {content: str, type: str, importance: float}
    """
    # 최근 대화 일부를 텍스트로 결합
    turns_txt = []
    for role, content in recent_turns[-6:]:  # 너무 길지 않게 최근 일부만 사용
        role_k = "사용자" if role == "user" else "어시스턴트"
        turns_txt.append(f"[{role_k}] {content}")
    turns_block = "\n".join(turns_txt)

    system = {
        "role": "system",
        "content": (
            "당신은 메모리 추출기입니다. 아래 대화에서 향후 대화에 유용할 사실/결정/선호/제약/할일을\n"
            "최소 1개, 최대 5개 항목으로 간결하게 추출하세요. 각 항목은 한 줄로 요약합니다."
        ),
    }
    user = {
        "role": "user",
        "content": (
            "다음 대화 로그와 최신 어시스턴트 응답에서 기억할 항목을 추출하세요.\n\n"
            f"대화 로그:\n{turns_block}\n\n최신 응답:\n{assistant_reply}"
        ),
    }
    try:
        resp = model.invoke([system, user])
        text = getattr(resp, "content", None) or str(resp)
        lines = [ln.strip("- •\t ") for ln in text.splitlines() if ln.strip()]
        out: List[Dict[str, Any]] = []
        for ln in lines[:5]:
            norm = _normalize_text(ln)
            if not norm:
                continue
            t = _infer_type(norm)
            imp = _importance_for_type(t)
            out.append({
                "content": norm,
                "type": t,
                "importance": imp,
            })
        return out
    except Exception:
        return []
