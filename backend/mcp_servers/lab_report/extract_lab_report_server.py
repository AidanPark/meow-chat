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

from app.core.deps import get_lab_report_extractor  # noqa: E402
from app.models.envelopes import OCRResultEnvelope, MergeEnvelope


mcp = FastMCP("LabReportServer")

_host, _port = load_mcp_server_settings("extract_lab_report", default_port=8004)
mcp.settings.host = _host
mcp.settings.port = _port


@mcp.tool()
async def extract_lab_report(ocr_results: Sequence[str]) -> str:
    """OCR 결과 JSON 목록을 받아 추출/병합 결과 JSON을 반환합니다."""
    if not isinstance(ocr_results, Sequence) or not ocr_results:
        return json.dumps({"error": "ocr_results must be a non-empty list"}, ensure_ascii=False)

    lab_report_extractor = get_lab_report_extractor(progress_cb=None)
    extractions: List[dict] = []
    failures: List[dict] = []

    for idx, raw in enumerate(ocr_results):
        logger.info("수신된 OCR 결과: index=%s, type=%s", idx, type(raw))
        payload = raw
        source_path = None
        if isinstance(raw, dict):
            source_path = raw.get("path")
            if "ocr_result" in raw:
                payload = raw["ocr_result"]
            elif "error" in raw:
                failures.append({"index": idx, "path": source_path, "error": raw.get("error")})
                logger.error("OCR 결과에 오류가 포함되어 있습니다(index=%s, path=%s): %s", idx, source_path, raw.get("error"))
                continue
            else:
                failures.append({"index": idx, "path": source_path, "error": "missing ocr_result field"})
                logger.error("OCR 결과에 ocr_result 필드가 없습니다(index=%s, path=%s)", idx, source_path)
                continue

        try:
            if isinstance(payload, str):
                ocr_env = OCRResultEnvelope.model_validate_json(payload)
            elif isinstance(payload, dict):
                ocr_env = OCRResultEnvelope.model_validate(payload)
            else:
                raise ValueError(f"Invalid OCR result type: {type(payload)}")
        except Exception as exc:
            logger.error("OCR 결과 파싱 실패 (index=%s, path=%s): %s", idx, source_path, exc)
            return json.dumps(
                {
                    "error": f"invalid ocr result at index {idx}: {exc}",
                    "path": source_path,
                    "failures": failures,
                },
                ensure_ascii=False,
            )

        extraction_env = lab_report_extractor.ocr_to_extraction(ocr_env)
        extractions.append(extraction_env.data)

    if not extractions:
        return json.dumps(
            {
                "error": "no_valid_ocr_results",
                "message": "유효한 OCR 결과가 없어 분석을 진행할 수 없습니다.",
                "failures": failures,
            },
            ensure_ascii=False,
        )

    try:
        merged_env: MergeEnvelope = lab_report_extractor.merge_extractions(extractions)
        return merged_env.model_dump_json(indent=2, ensure_ascii=False)
    except Exception as exc:  # pragma: no cover - 추출/병합 실패 시 메시지 반환
        logger.error("merge_extractions 실패: %s", exc)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


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
