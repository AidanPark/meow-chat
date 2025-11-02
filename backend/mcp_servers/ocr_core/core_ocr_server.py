"""
공통 OCR 코어 서버 (포트 8003)
- 이미지 경로 목록을 받아 전처리/패들OCR을 수행하고 OCRResultEnvelope JSON을 반환한다.
"""

import os
import sys
import json
import logging
from logging.handlers import RotatingFileHandler
import asyncio
from typing import Any, List, Sequence

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import uvicorn

"""패키지 임포트를 위한 sys.path 부트스트랩 후 런타임 초기화"""
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from mcp_servers.common.runtime import (
    setup_logging,
    load_mcp_server_settings,
    get_project_root,
)


setup_logging()
logger = logging.getLogger(__name__)

LOG_DIR = os.path.join(get_project_root(), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "ocr_core.log")
if not any(getattr(h, "baseFilename", None) == LOG_PATH for h in logger.handlers):
    file_handler = RotatingFileHandler(LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)

from app.core.deps import get_image_preprocessor, get_ocr_service  # noqa: E402
from app.models.envelopes import OCRData, OCRMeta, OCRResultEnvelope

mcp = FastMCP("OCRCoreServer")

_IMAGE_PREPROCESSOR = None
_OCR_SVC = None

# 네트워크 설정: 외부 설정/환경변수에서 로드 (기본값: 127.0.0.1:8003)
_host, _port = load_mcp_server_settings("ocr_core", default_port=8003)
mcp.settings.host = _host
mcp.settings.port = _port


def _get_preprocessor():
    global _IMAGE_PREPROCESSOR
    if _IMAGE_PREPROCESSOR is None:
        _IMAGE_PREPROCESSOR = get_image_preprocessor()
    return _IMAGE_PREPROCESSOR


def _get_ocr_service():
    global _OCR_SVC
    if _OCR_SVC is None:
        _OCR_SVC = get_ocr_service()
    return _OCR_SVC


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


def _run_ocr_pipeline(image_bytes: bytes, do_preprocess: bool, debug: bool) -> OCRResultEnvelope:
    data = image_bytes
    if do_preprocess:
        try:
            data = _get_preprocessor().process_bytes(data, debug=bool(debug))
        except Exception as exc:
            logger.exception("이미지 전처리 실패: do_preprocess=%s, debug=%s", do_preprocess, debug)
            raise RuntimeError(f"image preprocessing failed: {exc}") from exc

    ocr_service = _get_ocr_service()
    try:
        ocr_result_raw = ocr_service.run_ocr_from_bytes(data)
    except Exception as exc:
        logger.exception("PaddleOCR 실행 실패")
        raise RuntimeError(f"paddleocr execution failed: {exc}") from exc

    if ocr_result_raw is None:
        logger.error("PaddleOCR가 None을 반환했습니다.")
        raise RuntimeError("paddleocr returned no result")

    if hasattr(ocr_result_raw, "data") and hasattr(ocr_result_raw, "meta"):
        return ocr_result_raw  # type: ignore[return-value]

    logger.warning("예상치 못한 OCR 반환 형태: %r", type(ocr_result_raw))
    return OCRResultEnvelope(stage="ocr", data=OCRData(items=[]), meta=OCRMeta(items=0))


@mcp.tool()
async def ocr_image_file(paths: Sequence[str], do_preprocess: bool = True, debug: bool = False) -> List[dict]:
    """여러 이미지 경로를 받아 OCR 결과(envelope JSON)를 반환합니다."""
    if isinstance(paths, str):  # type: ignore[arg-type]
        paths = [paths]  # pragma: no cover

    if not isinstance(paths, Sequence) or not paths:
        return []

    results: List[dict] = []
    loop = asyncio.get_running_loop()

    for path in paths:
        logger.info(f"🖼️ OCR_IMAGE_FILE 호출: path={path}, do_preprocess={do_preprocess}, debug={debug}")
        if not path or not os.path.exists(path):
            msg = f"File not found: {path}"
            logger.error(msg)
            results.append({"path": path, "error": msg})
            continue

        try:
            with open(path, "rb") as f:
                b = f.read()
        except Exception as e:
            msg = f"Failed to read file: {e}"
            logger.error(msg)
            results.append({"path": path, "error": msg})
            continue

        try:
            env = await loop.run_in_executor(
                None,
                lambda b=b: _run_ocr_pipeline(
                    b,
                    do_preprocess=do_preprocess,
                    debug=debug,
                ),
            )
        except Exception as exc:
            logger.exception("OCR 파이프라인 실패: path=%s", path)
            results.append({"path": path, "error": str(exc)})
            continue

        out = _serialize_envelope(env)
        logger.info("🖨️ OCR 결과 반환")
        results.append({"path": path, "ocr_result": out})

    return results


if __name__ == "__main__":
    logger.info("🚀 OCR 코어 MCP 서버 시작 중...")
    logger.info("📋 등록된 도구들: ocr_image_file")
    logger.info(f"🌐 서버 주소: http://{mcp.settings.host or '127.0.0.1'}:{mcp.settings.port or 8003} (SSE: /sse, Health: /health)")

    async def health(_request):
        return JSONResponse({"status": "ok", "server": "OCRCoreServer"})

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
