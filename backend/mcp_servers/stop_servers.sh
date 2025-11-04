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
LAB_HOST="${MCP_EXTRACT_LAB_REPORT_HOST:-${MCP_HOST:-127.0.0.1}}"
LAB_PORT="${MCP_EXTRACT_LAB_REPORT_PORT:-8004}"
MEM_HOST="${MCP_MEMORY_HOST:-${MCP_HOST:-127.0.0.1}}"
MEM_PORT="${MCP_MEMORY_PORT:-8005}"

kill_processes_by_port() {
    local port="$1"
    local label="$2"
    if [[ -z "$port" ]]; then
        return
    fi
    local pids
    pids=$(lsof -ti:"$port" 2>/dev/null)
    if [[ -n "$pids" ]]; then
        echo "⚠️ ${label} 포트(${port})가 사용 중입니다. 프로세스 종료 시도: $pids"
        kill $pids 2>/dev/null
        sleep 1
        if lsof -ti:"$port" > /dev/null 2>&1; then
            echo "   … SIGTERM 실패 → SIGKILL 시도"
            kill -9 $pids 2>/dev/null
            sleep 1
        fi
        if lsof -ti:"$port" > /dev/null 2>&1; then
            echo "   ❌ 포트 ${port} 여전히 점유 중입니다."
        else
            echo "   ✅ 포트 ${port} 해제 완료"
        fi
    fi
}

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


if [ -f /tmp/extract_lab_report_server.pid ]; then
    LAB_PID=$(cat /tmp/extract_lab_report_server.pid)
    kill $LAB_PID 2>/dev/null && echo "✅ Lab Report OCR Server 종료됨 (PID: $LAB_PID)" || echo "⚠️ Lab Report OCR 종료 실패"
    rm /tmp/extract_lab_report_server.pid
fi

if [ -f /tmp/memory_server.pid ]; then
    MEM_PID=$(cat /tmp/memory_server.pid)
    kill $MEM_PID 2>/dev/null && echo "✅ Memory Server 종료됨 (PID: $MEM_PID)" || echo "⚠️ Memory Server 종료 실패"
    rm /tmp/memory_server.pid
fi

# 남은 프로세스들도 강제 종료
echo "🔍 남은 프로세스 정리 중..."
pkill -f "math_utility_server.py" 2>/dev/null
pkill -f "weather_api_server.py" 2>/dev/null
pkill -f "cat_health_server.py" 2>/dev/null
pkill -f "extract_lab_report_server.py" 2>/dev/null
pkill -f "memory_server.py" 2>/dev/null

sleep 2

# 포트 점유 프로세스도 정리
kill_processes_by_port "$MATH_PORT" "Math & Utility"
kill_processes_by_port "$WEATHER_PORT" "Weather & API"
kill_processes_by_port "$HEALTH_PORT" "Cat Health"
kill_processes_by_port "$LAB_PORT" "Lab Report OCR"
kill_processes_by_port "$MEM_PORT" "Memory"

# 포트 사용 확인
echo "📊 포트 사용 상태 확인:"
echo "   🧮 Math & Utility: http://${MATH_HOST}:${MATH_PORT}"
echo "   🌤️ Weather & API:   http://${WEATHER_HOST}:${WEATHER_PORT}"
echo "   🐱 Cat Health:      http://${HEALTH_HOST}:${HEALTH_PORT}"
echo "   🗂️ Lab Report OCR:  http://${LAB_HOST}:${LAB_PORT}"
echo "   🧠 Memory:          http://${MEM_HOST}:${MEM_PORT}"
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

if lsof -ti:${LAB_PORT} > /dev/null 2>&1; then
    echo "⚠️ 포트 ${LAB_PORT}이(가) 여전히 사용 중입니다"
else
    echo "✅ 포트 ${LAB_PORT} 해제됨"
fi

if lsof -ti:${MEM_PORT} > /dev/null 2>&1; then
    echo "⚠️ 포트 ${MEM_PORT}이(가) 여전히 사용 중입니다"
else
    echo "✅ 포트 ${MEM_PORT} 해제됨"
fi

echo ""
echo "🎉 Multi-MCP Server 시스템이 종료되었습니다!"
