"""
날씨 & 외부 API 서버 - 포트 8001
날씨 정보, 지역 정보, 외부 서비스 연동
"""

import os
import sys
import logging
import asyncio
import random
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

mcp = FastMCP("WeatherAPIServer")

# 네트워크 설정: 외부 설정/환경변수에서 로드 (기본값: 127.0.0.1:8001)
_host, _port = load_mcp_server_settings("weather_api", default_port=8001)
mcp.settings.host = _host
mcp.settings.port = _port

@mcp.tool()
async def get_weather(location: str) -> str:
    """Get current weather information for a specific city or location"""
    logger.info(f"🌤️ WEATHER 도구 호출: {location}")
    
    # 실제로는 OpenWeatherMap API 등을 호출
    # 여기서는 시뮬레이션
    await asyncio.sleep(0.5)  # API 호출 시뮬레이션
    
    weather_conditions = ["sunny", "cloudy", "rainy", "snowy", "partly cloudy"]
    temp = random.randint(15, 30)
    condition = random.choice(weather_conditions)
    
    result = f"The weather in {location} is {condition} and {temp}°C"
    logger.info(f"🌤️ WEATHER 결과: {result}")
    return result

@mcp.tool()
async def get_forecast(location: str, days: int = 3) -> str:
    """Get weather forecast for multiple days (1-7 days)"""
    logger.info(f"🌤️ FORECAST 도구 호출: {location}, {days}일간")
    
    if days < 1 or days > 7:
        days = 3
    
    await asyncio.sleep(0.3)  # API 호출 시뮬레이션
    
    forecast_data = []
    weather_conditions = ["sunny", "cloudy", "rainy", "partly cloudy"]
    
    for i in range(days):
        temp = random.randint(12, 28)
        condition = random.choice(weather_conditions)
        forecast_data.append(f"Day {i+1}: {condition}, {temp}°C")
    
    result = f"{days}-day forecast for {location}: " + ", ".join(forecast_data)
    logger.info(f"🌤️ FORECAST 결과: {result}")
    return result

@mcp.tool()
async def get_air_quality(location: str) -> str:
    """Get air quality information for a location"""
    logger.info(f"🌫️ AIR_QUALITY 도구 호출: {location}")
    
    await asyncio.sleep(0.4)  # API 호출 시뮬레이션
    
    aqi_levels = ["Good", "Moderate", "Unhealthy for Sensitive Groups", "Unhealthy"]
    aqi_value = random.randint(50, 150)
    aqi_level = random.choice(aqi_levels)
    
    result = f"Air quality in {location}: AQI {aqi_value} ({aqi_level})"
    logger.info(f"🌫️ AIR_QUALITY 결과: {result}")
    return result

@mcp.tool()
async def get_time_zone(location: str) -> str:
    """Get timezone information for a location"""
    logger.info(f"🕐 TIMEZONE 도구 호출: {location}")
    
    await asyncio.sleep(0.2)
    
    # 주요 도시들의 시간대 매핑 (간단한 예시)
    timezone_map = {
        "서울": "KST (UTC+9)",
        "seoul": "KST (UTC+9)",
        "도쿄": "JST (UTC+9)",
        "tokyo": "JST (UTC+9)",
        "뉴욕": "EST (UTC-5)",
        "new york": "EST (UTC-5)",
        "런던": "GMT (UTC+0)",
        "london": "GMT (UTC+0)",
        "파리": "CET (UTC+1)",
        "paris": "CET (UTC+1)"
    }
    
    timezone = timezone_map.get(location.lower(), "UTC+0 (Unknown timezone)")
    result = f"Timezone for {location}: {timezone}"
    logger.info(f"🕐 TIMEZONE 결과: {result}")
    return result

@mcp.tool()
async def search_location(query: str) -> str:
    """Search for location information and coordinates"""
    logger.info(f"📍 LOCATION 도구 호출: {query}")
    
    await asyncio.sleep(0.3)
    
    # 간단한 위치 정보 시뮬레이션
    locations = {
        "서울": "Seoul, South Korea (37.5665°N, 126.9780°E)",
        "seoul": "Seoul, South Korea (37.5665°N, 126.9780°E)",
        "부산": "Busan, South Korea (35.1796°N, 129.0756°E)",
        "busan": "Busan, South Korea (35.1796°N, 129.0756°E)",
        "뉴욕": "New York, USA (40.7128°N, 74.0060°W)",
        "new york": "New York, USA (40.7128°N, 74.0060°W)"
    }
    
    result = locations.get(query.lower(), f"Location '{query}' found (coordinates unknown)")
    logger.info(f"📍 LOCATION 결과: {result}")
    return result

if __name__ == "__main__":
    logger.info("🚀 날씨 & 외부 API MCP 서버 시작 중...")
    logger.info("📋 등록된 도구들: get_weather, get_forecast, get_air_quality, get_time_zone, search_location")
    logger.info(f"🌐 서버 주소: http://{mcp.settings.host or '127.0.0.1'}:{mcp.settings.port or 8001} (SSE: /sse, Health: /health)")

    async def health(_request):
        return JSONResponse({"status": "ok", "server": "WeatherAPIServer"})

    sse_app = mcp.sse_app()
    routes = [
        Route("/health", endpoint=health),
        *sse_app.routes,
    ]

    app = Starlette(
        routes=routes,
        middleware=sse_app.user_middleware,
    )

    uvicorn.run(app, host=mcp.settings.host or "127.0.0.1", port=mcp.settings.port or 8001)
