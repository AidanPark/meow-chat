#!/usr/bin/env python
from __future__ import annotations

"""
샘플 대화로 메모리 저장→검색→미리보기까지 검증하는 스크립트.
앱과 동일한 경로(LLM 프롬프트 → extract_candidates → write_memories → retrieve)로 수행합니다.

Usage:
  conda run -n meow-chat python scripts/test_memory_flow.py
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
sys.path.insert(0, str(FRONTEND))

from services.memory.memory_writer import extract_candidates
from services.memory.memory_retriever import write_memories, retrieve_memories
from services.memory.core_facts import build_pinned_core_facts_block

# 환경 변수(.env) 로드
try:
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv())
except Exception:
    pass


def main():
    # 앱과 동일 환경 가정
    user_id = os.getenv("USER", "default") or "default"

    # Streamlit 컨텍스트 없이 직접 모델을 생성하여 경고를 방지
    try:
        from langchain_openai import ChatOpenAI  # type: ignore
    except Exception as e:
        print("[ERROR] ChatOpenAI 임포트 실패:", e)
        return
    default_model = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4.1-mini")
    test_model = os.getenv("TEST_MEMORY_FLOW_MODEL", default_model) or default_model
    model = ChatOpenAI(model=test_model, streaming=False)

    # 샘플 대화 구성 (최근 메시지 1~2턴 + 어시스턴트 응답)
    recent_turns = [
        ("user", "안녕? 우리집 고양이 이름은 옹심이야. 닭고기 알레르기가 있고, 중성화 완료야."),
        ("assistant", "반가워요! 옹심이에 대해 더 알려주세요."),
        ("user", "몸무게는 4.2kg이고 암컷이야. 실내생활만 하고 있어."),
    ]
    assistant_reply = "도움이 필요하면 알려주세요!"

    print("[STEP] extract_candidates with real LLM")
    cands = extract_candidates(recent_turns=recent_turns, assistant_reply=assistant_reply, model=model)
    print("[RESULT] candidates:")
    for i, c in enumerate(cands):
        print(f"  - {i+1}:", c)

    if not cands:
        print("[WARN] LLM이 항목을 반환하지 않았습니다. 프롬프트/모델 파라미터를 조정하세요.")
        return

    print("[STEP] write_memories")
    ids = write_memories(user_id=user_id, memories=cands)
    print("[RESULT] upsert ids:", ids)

    print("[STEP] retrieve by keywords")
    for q in ["옹심이", "알레르기", "중성화", "몸무게", "암컷", "실내생활"]:
        res = retrieve_memories(user_id=user_id, user_message=q, summary_text=None, k=6, filters=None)
        print(f"  - query='{q}' -> {len(res)} hits")
        for r in res[:3]:
            print("    •", {k: r.get(k) for k in ("type", "content")})

    print("[STEP] build pinned core facts block")
    block = build_pinned_core_facts_block(
        user_id=user_id,
        user_message="개인화 컨텍스트 미리보기",
        summary_text=None,
        model=model,
        max_tokens=400,
        per_item_cap=160,
        max_queries=6,
    )
    print("[RESULT] pinned_core_facts:\n", block)


if __name__ == "__main__":
    main()
