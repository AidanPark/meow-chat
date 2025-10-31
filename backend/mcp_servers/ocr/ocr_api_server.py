"""
OCR API 서버 - 포트 8003
OCRPipelineManager.image_to_ocr 를 실행하여 표준 OCR 결과(envelope)를 반환합니다.
"""

import os
import sys
import json
import logging
import asyncio
from typing import Any
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import uvicorn

"""패키지 임포트를 위한 sys.path 부트스트랩 후 런타임 초기화"""
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from mcp_servers.common.runtime import setup_logging, load_mcp_server_settings


setup_logging()
logger = logging.getLogger(__name__)

# OCR 파이프라인 매니저용 DI 프로바이더
from app.core.deps import get_pipeline_manager  # noqa: E402

mcp = FastMCP("OCRAPIServer")

# 네트워크 설정: 외부 설정/환경변수에서 로드 (기본값: 127.0.0.1:8003)
_host, _port = load_mcp_server_settings("ocr_api", default_port=8003)
mcp.settings.host = _host
mcp.settings.port = _port


def _serialize_envelope(env: Any) -> str:
    """Pydantic 1.x/2.x 및 일반 객체에 대한 최대한의 JSON 직렬화 시도.

    다음 우선순위로 직렬화를 시도합니다.
    1) Pydantic v2: model_dump_json
    2) Pydantic v1: json
    3) dict/dict-유사 객체: .dict() 또는 __dict__
    4) 최후 수단: str(env) 를 감싼 JSON
    """
    # Try Pydantic v2
    try:
        return env.model_dump_json(indent=2, ensure_ascii=False)  # type: ignore[attr-defined]
    except Exception:
        pass
    # Try Pydantic v1
    try:
        return env.json(indent=2, ensure_ascii=False)  # type: ignore[attr-defined]
    except Exception:
        pass
    # Try dict-like
    try:
        if hasattr(env, "dict"):
            return json.dumps(env.dict(), indent=2, ensure_ascii=False)  # type: ignore[attr-defined]
        if hasattr(env, "__dict__"):
            return json.dumps(env.__dict__, indent=2, ensure_ascii=False, default=str)
    except Exception:
        pass
    # Fallback to string
    try:
        return json.dumps({"result": str(env)}, indent=2, ensure_ascii=False)
    except Exception:
        return json.dumps({"error": "unable to serialize result"}, indent=2, ensure_ascii=False)


@mcp.tool()
async def ocr_image_file(path: str, do_preprocess: bool = True, debug: bool = False) -> str:
    """이미지 파일에 OCR을 수행하고 OCR 결과(envelope)를 JSON 문자열로 반환합니다.

    Args:
        path: 이미지 파일의 절대/상대 경로.
        do_preprocess: OCR 이전에 이미지 전처리를 수행할지 여부.
        debug: 가능한 경우 전처리 디버그 옵션 활성화.
    """
    logger.info(f"🖼️ OCR_IMAGE_FILE 호출: path={path}, do_preprocess={do_preprocess}, debug={debug}")

    if not path or not os.path.exists(path):
        msg = f"File not found: {path}"
        logger.error(msg)
        return json.dumps({"error": msg}, ensure_ascii=False)

    try:
        with open(path, "rb") as f:
            b = f.read()
    except Exception as e:
        msg = f"Failed to read file: {e}"
        logger.error(msg)
        return json.dumps({"error": msg}, ensure_ascii=False)

    # 중앙 DI에서 매니저 생성
    manager = get_pipeline_manager(progress_cb=None)

    # OCR 실행 (async 도구 내부에서 동기 호출 실행)
    loop = asyncio.get_running_loop()
    env = await loop.run_in_executor(
        None,
        lambda: manager.image_to_ocr(
            b,
            do_preprocess=do_preprocess,
            preprocess_kwargs={"debug": bool(debug)},
        ),
    )

    out = _serialize_envelope(env)
    logger.info("🖨️ OCR 결과 반환")
    return out


if __name__ == "__main__":
    logger.info("🚀 OCR API MCP 서버 시작 중...")
    logger.info("📋 등록된 도구들: ocr_image_file")
    logger.info(f"🌐 서버 주소: http://{mcp.settings.host or '127.0.0.1'}:{mcp.settings.port or 8003} (SSE: /sse, Health: /health)")

    async def health(_request):
        return JSONResponse({"status": "ok", "server": "OCRAPIServer"})

    sse_app = mcp.sse_app()
    routes = [
        Route("/health", endpoint=health),
        *sse_app.routes,
    ]

    app = Starlette(
        routes=routes,
        middleware=sse_app.user_middleware,
    )

    uvicorn.run(app, host=mcp.settings.host or "127.0.0.1", port=mcp.settings.port or 8003)
