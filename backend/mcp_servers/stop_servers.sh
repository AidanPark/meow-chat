#!/bin/bash

# Multi-MCP Server 종료 스크립트

echo "🛑 Multi-MCP Server 시스템 종료 중..."

# .env 자동 로드 (루트/백엔드/현재 디렉토리 우선순위)
load_env_file() {
    local f="$1"
    if [[ -f "$f" ]]; then
        set -a
        # shellcheck disable=SC1090
        . "$f"
        set +a
        echo "📦 .env 로드: $f"
    fi
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
load_env_file "$SCRIPT_DIR/../../.env"
load_env_file "$SCRIPT_DIR/../.env"
load_env_file "$SCRIPT_DIR/.env"

# 설정(환경변수)에서 호스트/포트 읽기 (포트 확인용)
MATH_HOST="${MCP_MATH_UTILITY_HOST:-${MCP_HOST:-127.0.0.1}}"
MATH_PORT="${MCP_MATH_UTILITY_PORT:-${MCP_PORT:-8000}}"
WEATHER_HOST="${MCP_WEATHER_API_HOST:-${MCP_HOST:-127.0.0.1}}"
WEATHER_PORT="${MCP_WEATHER_API_PORT:-${MCP_PORT:-8001}}"
HEALTH_HOST="${MCP_CAT_HEALTH_HOST:-${MCP_HOST:-127.0.0.1}}"
HEALTH_PORT="${MCP_CAT_HEALTH_PORT:-${MCP_PORT:-8002}}"
OCR_HOST="${MCP_OCR_API_HOST:-${MCP_HOST:-127.0.0.1}}"
OCR_PORT="${MCP_OCR_API_PORT:-${MCP_PORT:-8003}}"

# PID 파일에서 프로세스 ID 읽기
if [ -f /tmp/math_server.pid ]; then
    MATH_PID=$(cat /tmp/math_server.pid)
    kill $MATH_PID 2>/dev/null && echo "✅ Math & Utility Server 종료됨 (PID: $MATH_PID)" || echo "⚠️ Math Server 종료 실패"
    rm /tmp/math_server.pid
fi

if [ -f /tmp/weather_server.pid ]; then
    WEATHER_PID=$(cat /tmp/weather_server.pid)
    kill $WEATHER_PID 2>/dev/null && echo "✅ Weather & API Server 종료됨 (PID: $WEATHER_PID)" || echo "⚠️ Weather Server 종료 실패"
    rm /tmp/weather_server.pid
fi

if [ -f /tmp/health_server.pid ]; then
    HEALTH_PID=$(cat /tmp/health_server.pid)
    kill $HEALTH_PID 2>/dev/null && echo "✅ Cat Health Server 종료됨 (PID: $HEALTH_PID)" || echo "⚠️ Health Server 종료 실패"
    rm /tmp/health_server.pid
fi

if [ -f /tmp/ocr_server.pid ]; then
    OCR_PID=$(cat /tmp/ocr_server.pid)
    kill $OCR_PID 2>/dev/null && echo "✅ OCR API Server 종료됨 (PID: $OCR_PID)" || echo "⚠️ OCR Server 종료 실패"
    rm /tmp/ocr_server.pid
fi

# 남은 프로세스들도 강제 종료
echo "🔍 남은 프로세스 정리 중..."
pkill -f "math_utility_server.py" 2>/dev/null
pkill -f "weather_api_server.py" 2>/dev/null
pkill -f "cat_health_server.py" 2>/dev/null
pkill -f "ocr_api_server.py" 2>/dev/null

sleep 2

# 포트 사용 확인
echo "📊 포트 사용 상태 확인:"
echo "   🧮 Math & Utility: http://${MATH_HOST}:${MATH_PORT}"
echo "   🌤️ Weather & API:   http://${WEATHER_HOST}:${WEATHER_PORT}"
echo "   🐱 Cat Health:      http://${HEALTH_HOST}:${HEALTH_PORT}"
echo "   🖼️ OCR API:         http://${OCR_HOST}:${OCR_PORT}"
if lsof -ti:${MATH_PORT} > /dev/null 2>&1; then
    echo "⚠️ 포트 ${MATH_PORT}이(가) 여전히 사용 중입니다"
else
    echo "✅ 포트 ${MATH_PORT} 해제됨"
fi

if lsof -ti:${WEATHER_PORT} > /dev/null 2>&1; then
    echo "⚠️ 포트 ${WEATHER_PORT}이(가) 여전히 사용 중입니다"
else
    echo "✅ 포트 ${WEATHER_PORT} 해제됨"
fi

if lsof -ti:${HEALTH_PORT} > /dev/null 2>&1; then
    echo "⚠️ 포트 ${HEALTH_PORT}이(가) 여전히 사용 중입니다"
else
    echo "✅ 포트 ${HEALTH_PORT} 해제됨"
fi

if lsof -ti:${OCR_PORT} > /dev/null 2>&1; then
    echo "⚠️ 포트 ${OCR_PORT}이(가) 여전히 사용 중입니다"
else
    echo "✅ 포트 ${OCR_PORT} 해제됨"
fi

echo ""
echo "🎉 Multi-MCP Server 시스템이 종료되었습니다!"