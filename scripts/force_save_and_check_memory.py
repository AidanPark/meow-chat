#!/usr/bin/env python
from __future__ import annotations

"""
강제 메모리 저장/조회 점검 스크립트
- 앱 로직과 동일한 경로(services.memory.*)를 통해 쓰기/읽기를 수행합니다.
사용법:
  conda run -n meow-chat python scripts/force_save_and_check_memory.py
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
if str(FRONTEND) not in sys.path:
    sys.path.insert(0, str(FRONTEND))

# .env 로드(선택)
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(dotenv_path=ROOT / ".env", override=False)
except Exception:
    pass

from services.memory.memory_retriever import write_memories, retrieve_memories
from services.memory.core_facts import build_pinned_core_facts_block, CORE_QUERIES
from services.memory.memory_utils import trim_memory_block
from services.memory.memory_store import get_memory_store


def main():
    user_id = os.getenv("USER", "default") or "default"
    # OpenAI API 키 확인 및 로드 시도(수동 파서 폴백)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # 간단 파서: KEY=VALUE 형태만 지원, 따옴표 제거
        env_path = ROOT / ".env"
        if env_path.exists():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k and v and k not in os.environ:
                        os.environ[k] = v
            except Exception:
                pass
        api_key = os.getenv("OPENAI_API_KEY")
    print(f"[DEBUG] OPENAI_API_KEY set: {bool(api_key)}")
    # 요청에 따라 '옹심이'를 프로필로 강제 저장 (앱 추출 결과 형식을 따름)
    memory_item = {
        "content": "고양이 이름은 옹심이",
        "type": "profile",
        "importance": 0.85,
    }

    print(f"[STEP] user_id={user_id} | 강제 저장 시작")
    ids = write_memories(user_id=user_id, memories=[memory_item])
    print("[RESULT] upsert ids (write_memories):", ids)
    if not ids:
        # 내부 예외가 숨겨질 수 있어 직접 저장 경로도 시도하여 에러 메시지 노출
        try:
            store = get_memory_store()
            direct_ids = store.upsert_memories(user_id=user_id, memories=[{"content": memory_item["content"], "type": memory_item["type"], "importance": memory_item["importance"], "user_id": user_id}])
            print("[RESULT] upsert ids (direct store):", direct_ids)
        except Exception as e:
            print("[ERROR] direct store upsert failed:", repr(e))

    # 바로 검색으로 확인
    print("[STEP] 키워드 '옹심이'로 검색")
    results = retrieve_memories(user_id=user_id, user_message="옹심이", summary_text=None, k=8, filters=None)
    for i, r in enumerate(results):
        print(f"  - #{i+1}", {k: r.get(k) for k in ("id", "type", "content")})

    # core_facts 내부 검색 형태를 일부 샘플로 재현해 보기
    print("[STEP] core_facts 스타일 샘플 검색 (프로필, 이름 키워드 포함)")
    for q in ["프로필", "이름"]:
        rr = retrieve_memories(user_id=user_id, user_message=f"{q} 프로필 이름 옹심이", summary_text=None, k=6, filters=None)
        print(f"  - query='{q} 프로필 이름 옹심이' -> hits={len(rr)}")
        for i, r in enumerate(rr[:3]):
            print(f"    • {i+1}:", {k: r.get(k) for k in ("type", "content")})

    # 개인화 컨텍스트(핵심 사실) 블록 확인
    print("[STEP] 개인화 컨텍스트(핵심 사실) 미리보기 생성")
    block = build_pinned_core_facts_block(
        user_id=user_id,
        user_message="프로필 이름 옹심이",
        summary_text=None,
        model=None,  # 내부에서 모델을 사용하지 않으므로 None 전달 허용
        max_tokens=300,
    )
    print("[RESULT] pinned_core_facts:\n", block)

    # 디버그: CORE_QUERIES 상위 6개로 실제 후보 수집을 재현해 확인
    print("[DEBUG] CORE_QUERIES[:6] 개별 검색 결과")
    candidates = []
    for q in CORE_QUERIES[:6]:
        rr = retrieve_memories(user_id=user_id, user_message=f"{q} 프로필 이름 옹심이", summary_text=None, k=6, filters=None)
        texts = [r.get("content", "").strip() for r in rr if (r.get("content") or "").strip()]
        print(f"  - {q}: hits={len(texts)}")
        candidates.extend(texts)
    print("[DEBUG] total candidates:", len(candidates))
    if candidates:
        joined = "\n".join(f"- {c}" for c in candidates[:20])
        trimmed = trim_memory_block([joined], max_tokens=300, per_item_token_cap=160)
        print("[DEBUG] trimmed exists:", bool(trimmed), ", len:", len(trimmed[0]) if trimmed else 0)


if __name__ == "__main__":
    main()
