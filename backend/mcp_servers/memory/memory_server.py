"""
Memory MCP Server - 포트 8005 (기본값)

장기 메모리(RAG 스니펫) 검색/읽기/쓰기용 최소 서버.
간단한 JSON 파일 저장소를 사용하여 빠르게 시작할 수 있도록 구현했습니다.

도구 계약(입출력)
- memory_search(user_id, query, k=8, owner_id=None, cat_id=None, filters=None)
    -> {items: [...], stats: {took_ms}}
- memory_read(user_id, id)
    -> {id, user_id, owner_id?, cat_id?, type, content, importance, timestamp, tags, pii_flags}
- memory_upsert(user_id, items=[{type, content, importance, owner_id?, cat_id?, timestamp?, tags?, pii_flags?}])
    -> {ids: [...], deduped: int}

주의: 운영 전환 시에는 벡터 DB(Qdrant/pgvector 등)로 백엔드를 교체하세요.
"""

import os
import sys
import json
import time
import uuid
import math
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import uvicorn

# Bootstrap sys.path so that `mcp_servers` package can be imported when running from subfolders
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from mcp_servers.common.runtime import setup_logging, load_mcp_server_settings


setup_logging()
logger = logging.getLogger(__name__)

mcp = FastMCP("MemoryServer")

# 네트워크 설정: 외부 설정/환경변수에서 로드 (기본값: 127.0.0.1:8005)
_host, _port = load_mcp_server_settings("memory", default_port=8005)
mcp.settings.host = _host
mcp.settings.port = _port

# 간단한 JSON 파일 저장소 경로
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "vectors"))
os.makedirs(DATA_DIR, exist_ok=True)
STORE_PATH = os.path.join(DATA_DIR, "memory_store.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_store() -> List[Dict[str, Any]]:
    if not os.path.exists(STORE_PATH):
        return []
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_store(items: List[Dict[str, Any]]):
    tmp = STORE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STORE_PATH)


def _norm_text(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


def _tokenize(s: str) -> List[str]:
    return [t for t in _norm_text(s).replace("/", " ").replace("-", " ").split(" ") if t]


def _time_decay(ts: str, lambda_: float = 0.002) -> float:
    try:
        dt = datetime.fromisoformat(ts)
        age_days = (datetime.now(dt.tzinfo) - dt).total_seconds() / 86400.0
        return math.exp(-lambda_ * max(0.0, age_days))
    except Exception:
        return 1.0


def _overlap_score(a: str, b: str) -> float:
    qa = set(_tokenize(a))
    qb = set(_tokenize(b))
    if not qa or not qb:
        return 0.0
    inter = len(qa & qb)
    return inter / max(1, len(qa))


@mcp.tool()
def memory_upsert(user_id: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """장기 메모리 항목을 업서트합니다(간단 디듀프 포함).

    - owner_id, cat_id를 통해 보호자/고양이 구분 저장을 지원합니다(둘 다 없으면 일반 항목).
    - dedup 기준: user_id + owner_id + cat_id + type + content
    """
    logger.info(f"📝 memory_upsert 호출: user_id={user_id}, count={len(items) if items else 0}")
    store = _load_store()
    ids: List[str] = []
    deduped = 0

    for it in items or []:
        content = _norm_text(str(it.get("content", "")))
        if not content:
            continue
        typ = str(it.get("type", "note"))
        importance = float(it.get("importance", 0.5))
        timestamp = it.get("timestamp") or _now_iso()
        tags = list(it.get("tags") or [])
        pii_flags = list(it.get("pii_flags") or [])
        owner_id = it.get("owner_id") or None
        cat_id = it.get("cat_id") or None

        # 단순 디듀프: 동일 user_id/owner_id/cat_id & type & 동일 content 텍스트면 스킵
        exists = next(
            (
                r
                for r in store
                if r.get("user_id") == user_id
                and r.get("type") == typ
                and r.get("owner_id") == owner_id
                and r.get("cat_id") == cat_id
                and _norm_text(r.get("content", "")) == content
            ),
            None,
        )
        if exists:
            deduped += 1
            continue

        rid = str(uuid.uuid4())
        rec = {
            "id": rid,
            "user_id": user_id,
            "owner_id": owner_id,
            "cat_id": cat_id,
            "type": typ,
            "content": content,
            "importance": importance,
            "timestamp": timestamp,
            "tags": tags,
            "pii_flags": pii_flags,
        }
        store.append(rec)
        ids.append(rid)

    _save_store(store)
    return {"ids": ids, "deduped": deduped}


@mcp.tool()
def memory_read(user_id: str, id: str) -> Dict[str, Any]:
    """id로 단일 메모리를 읽습니다."""
    logger.info(f"📖 memory_read 호출: user_id={user_id}, id={id}")
    store = _load_store()
    rec = next((r for r in store if r.get("id") == id and r.get("user_id") == user_id), None)
    if not rec:
        raise ValueError("메모리를 찾을 수 없습니다")
    return rec


@mcp.tool()
def memory_search(user_id: str, query: str, k: int = 8, owner_id: Optional[str] = None, cat_id: Optional[str] = None, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """간단한 토큰 겹침 + 시간 감쇠 + 중요도 가중 기반 검색(MVP).

    - owner_id, cat_id로 보호자/고양이 범위를 필터링합니다(둘 다 None이면 전체).
    """
    t0 = time.time()
    logger.info(f"🔎 memory_search 호출: user_id={user_id}, q='{query}', k={k}")
    store = _load_store()
    filters = filters or {}
    q = str(query or "")

    # 필터 적용(유형/태그 등)
    def _pass(rec: Dict[str, Any]) -> bool:
        if rec.get("user_id") != user_id:
            return False
        if owner_id is not None and rec.get("owner_id") != owner_id:
            return False
        if cat_id is not None and rec.get("cat_id") != cat_id:
            return False
        f_type = filters.get("type")
        if f_type and rec.get("type") != f_type:
            return False
        f_tags = filters.get("tags")
        if f_tags:
            tags = set(rec.get("tags") or [])
            if not set(f_tags).issubset(tags):
                return False
        return True

    cand = [r for r in store if _pass(r)]
    scored = []
    for r in cand:
        sim = _overlap_score(q, r.get("content", ""))  # 0..1
        tdec = _time_decay(r.get("timestamp") or _now_iso())  # 0..1
        imp = float(r.get("importance", 0.5))  # 0..1
        score = 0.7 * sim + 0.2 * tdec + 0.1 * imp
        scored.append((score, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    items = [r for _, r in scored[: max(1, int(k or 8))]]
    took_ms = int((time.time() - t0) * 1000)
    return {"items": items, "stats": {"took_ms": took_ms, "total": len(cand)}}


if __name__ == "__main__":
    logger.info("🚀 Memory MCP 서버 시작 중...")
    logger.info("📋 등록된 도구들: memory_search, memory_read, memory_upsert")
    logger.info(f"🌐 서버 주소: http://{mcp.settings.host or '127.0.0.1'}:{mcp.settings.port or 8005} (SSE: /sse, Health: /health)")

    async def health(_request):
        return JSONResponse({"status": "ok", "server": "MemoryServer"})

    sse_app = mcp.sse_app()
    routes = [
        Route("/health", endpoint=health),
        *sse_app.routes,
    ]

    app = Starlette(
        routes=routes,
        middleware=sse_app.user_middleware,
    )

    uvicorn.run(app, host=mcp.settings.host or "127.0.0.1", port=mcp.settings.port or 8005)
