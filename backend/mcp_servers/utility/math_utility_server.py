"""
수학 & 유틸리티 서버 - 포트 8000
기본적인 계산과 유틸리티 기능 제공
"""

import os
import sys
import logging
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount
import uvicorn

# Bootstrap sys.path so that `mcp_servers` package can be imported when running from subfolders
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from mcp_servers.common.runtime import setup_logging


setup_logging()
logger = logging.getLogger(__name__)

mcp = FastMCP("MathUtilityServer")

# 네트워크 설정: 포트 충돌 방지를 위해 명시적으로 설정
mcp.settings.host = "127.0.0.1"
mcp.settings.port = 8000

# 수학 도구들
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    logger.info(f"🧮 ADD 도구 호출: {a} + {b}")
    result = a + b
    logger.info(f"🧮 ADD 결과: {result}")
    return result

@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    logger.info(f"🧮 MULTIPLY 도구 호출: {a} × {b}")
    result = a * b
    logger.info(f"🧮 MULTIPLY 결과: {result}")
    return result

@mcp.tool()
def subtract(a: int, b: int) -> int:
    """Subtract two numbers"""
    logger.info(f"🧮 SUBTRACT 도구 호출: {a} - {b}")
    result = a - b
    logger.info(f"🧮 SUBTRACT 결과: {result}")
    return result

@mcp.tool()
def divide(a: float, b: float) -> float:
    """Divide two numbers"""
    logger.info(f"🧮 DIVIDE 도구 호출: {a} ÷ {b}")
    if b == 0:
        logger.error("🧮 DIVIDE 오류: 0으로 나눌 수 없음")
        raise ValueError("Cannot divide by zero")
    result = a / b
    logger.info(f"🧮 DIVIDE 결과: {result}")
    return result

@mcp.tool()
async def convert_units(value: float, from_unit: str, to_unit: str) -> float:
    """Convert between different units (temperature, weight, length)"""
    logger.info(f"🔧 CONVERT 도구 호출: {value} {from_unit} → {to_unit}")
    
    # 온도 변환
    if from_unit == "celsius" and to_unit == "fahrenheit":
        result = (value * 9/5) + 32
    elif from_unit == "fahrenheit" and to_unit == "celsius":
        result = (value - 32) * 5/9
    # 무게 변환 (kg <-> lb)
    elif from_unit == "kg" and to_unit == "lb":
        result = value * 2.20462
    elif from_unit == "lb" and to_unit == "kg":
        result = value / 2.20462
    # 길이 변환 (cm <-> inch)
    elif from_unit == "cm" and to_unit == "inch":
        result = value / 2.54
    elif from_unit == "inch" and to_unit == "cm":
        result = value * 2.54
    else:
        result = value
    
    logger.info(f"🔧 CONVERT 결과: {result}")
    return result

@mcp.tool()
def calculate_percentage(part: float, total: float) -> float:
    """Calculate percentage of part from total"""
    logger.info(f"📊 PERCENTAGE 도구 호출: {part}/{total}")
    if total == 0:
        logger.error("📊 PERCENTAGE 오류: 전체값이 0입니다")
        raise ValueError("Total cannot be zero")
    result = (part / total) * 100
    logger.info(f"📊 PERCENTAGE 결과: {result}%")
    return result

if __name__ == "__main__":
    logger.info("🚀 수학 & 유틸리티 MCP 서버 시작 중...")
    logger.info("📋 등록된 도구들: add, multiply, subtract, divide, convert_units, calculate_percentage")
    logger.info("🌐 서버 주소: http://127.0.0.1:8000 (SSE: /sse, Health: /health)")

    async def health(_request):
        return JSONResponse({"status": "ok", "server": "MathUtilityServer"})

    app = Starlette(
        routes=[
            Route("/health", endpoint=health),
            Mount("/sse", app=mcp.sse_app()),
        ]
    )

    uvicorn.run(app, host=mcp.settings.host or "127.0.0.1", port=mcp.settings.port or 8000)