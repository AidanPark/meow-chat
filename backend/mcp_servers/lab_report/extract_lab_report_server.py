"""
건강검진(혈액검사) 리포트 전용 OCR 후처리 서버 (포트 8004)
- 공통 OCR 결과(JSON)를 받아 추출/병합을 거쳐 최종 MergeEnvelope JSON을 반환한다.
"""

import os
import sys
import json
import logging
from logging.handlers import RotatingFileHandler
from typing import Any, List, Sequence

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import uvicorn

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
LOG_PATH = os.path.join(LOG_DIR, "lab_report.log")
if not any(getattr(h, "baseFilename", None) == LOG_PATH for h in logger.handlers):
    file_handler = RotatingFileHandler(LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)

from app.core.deps import get_lab_report_extractor, get_image_preprocessor, get_ocr_service  # noqa: E402
from app.models.envelopes import OCRResultEnvelope, OCRData, OCRMeta, MergeEnvelope


mcp = FastMCP("LabReportServer")

_host, _port = load_mcp_server_settings("extract_lab_report", default_port=8004)
mcp.settings.host = _host
mcp.settings.port = _port


_IMAGE_PREPROCESSOR = None
_OCR_SVC = None


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
async def extract_lab_report(paths: Sequence[str], do_preprocess: bool = True, debug: bool = False) -> str:
    """이미지 경로를 입력받아 내부에서 OCR→추출→병합까지 수행하고 MergeEnvelope(JSON)로 반환합니다.

    입력:
    - paths: 이미지 경로들의 시퀀스(str). 한 장 이상 허용합니다.
    - do_preprocess: 전처리 사용 여부(기본값 True)
    - debug: 디버그 모드(기본값 False)

    출력:
    - MergeEnvelope(JSON 문자열). RBC/HCT/HGB/WBC 등 핵심 수치 및 메타를 포함합니다.
    """
    if isinstance(paths, str):  # type: ignore[arg-type]
        paths = [paths]
    if not isinstance(paths, Sequence) or not paths:
        return json.dumps({"error": "paths must be a non-empty list"}, ensure_ascii=False)

    lab_report_extractor = get_lab_report_extractor(progress_cb=None)
    extractions: List[dict] = []
    failures: List[dict] = []

    loop = None
    try:
        import asyncio as _asyncio
        loop = _asyncio.get_running_loop()
    except Exception:
        loop = None

    for idx, path in enumerate(paths):
        logger.info("🖼️ EXTRACT_LAB_REPORT 호출: path=%s, do_preprocess=%s, debug=%s", path, do_preprocess, debug)
        if not path or not os.path.exists(path):
            msg = f"File not found: {path}"
            logger.error(msg)
            failures.append({"index": idx, "path": path, "error": msg})
            continue

        try:
            with open(path, "rb") as f:
                b = f.read()
        except Exception as e:
            msg = f"Failed to read file: {e}"
            logger.error(msg)
            failures.append({"index": idx, "path": path, "error": msg})
            continue

        try:
            if loop:
                ocr_env = await loop.run_in_executor(
                    None,
                    lambda b=b: _run_ocr_pipeline(
                        b,
                        do_preprocess=do_preprocess,
                        debug=debug,
                    ),
                )
            else:
                ocr_env = _run_ocr_pipeline(b, do_preprocess=do_preprocess, debug=debug)
        except Exception as exc:
            logger.exception("OCR 파이프라인 실패: path=%s", path)
            failures.append({"index": idx, "path": path, "error": str(exc)})
            continue

        try:
            extraction_env = lab_report_extractor.ocr_to_extraction(ocr_env)
            extractions.append(extraction_env.data)
        except Exception as exc:
            logger.exception("extraction 실패: path=%s", path)
            failures.append({"index": idx, "path": path, "error": f"extraction_failed: {exc}"})
            continue

    if not extractions:
        return json.dumps(
            {
                "error": "no_valid_images",
                "message": "유효한 이미지에서 OCR/추출을 수행하지 못했습니다.",
                "failures": failures,
            },
            ensure_ascii=False,
        )

    try:
        merged_env: MergeEnvelope = lab_report_extractor.merge_extractions(extractions)
        return merged_env.model_dump_json(indent=2, ensure_ascii=False)
    except Exception as exc:  # pragma: no cover
        logger.error("merge_extractions 실패: %s", exc)
        return json.dumps({"error": str(exc), "failures": failures}, ensure_ascii=False)


if __name__ == "__main__":
    logger.info("🚀 건강검진 OCR 후처리 MCP 서버 시작 중...")
    logger.info("📋 등록된 도구들: extract_lab_report")
    logger.info(f"🌐 서버 주소: http://{mcp.settings.host or '127.0.0.1'}:{mcp.settings.port or 8004} (SSE: /sse, Health: /health)")

    async def health(_request):
        return JSONResponse({"status": "ok", "server": "LabReportServer"})

    sse_app = mcp.sse_app()
    routes = [
        Route("/health", endpoint=health),
        *sse_app.routes,
    ]

    app = Starlette(routes=routes, middleware=sse_app.user_middleware)

    uvicorn.run(app, host=mcp.settings.host or "127.0.0.1", port=mcp.settings.port or 8004)
