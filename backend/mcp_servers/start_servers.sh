#!/bin/bash

# Multi-MCP Server 실행 스크립트

echo "🚀 Multi-MCP Server 시스템 시작 중..."

# 현재 실행 중인 서버들 종료
echo "기존 서버 프로세스 종료 중..."
pkill -f "math_utility_server.py"
pkill -f "weather_api_server.py" 
pkill -f "cat_health_server.py"
pkill -f "core_ocr_server.py"
pkill -f "extract_lab_report_server.py"
pkill -f "memory_server.py"

sleep 2

# 실행 환경 체크(선택): 로컬에선 conda 권장, 컨테이너/CI에선 건너뜀
if [[ -z "$CI" && -z "$DOCKER" ]]; then
    if [[ "$CONDA_DEFAULT_ENV" != "meow-chat" ]]; then
            echo "ℹ️ conda 환경(meow-chat)이 활성화되어 있지 않습니다. 로컬 환경이라면 'conda activate meow-chat' 후 실행을 권장합니다."
    fi
fi

# 스크립트 기준 경로 설정
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

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

load_env_file "$SCRIPT_DIR/../../.env"
load_env_file "$SCRIPT_DIR/../.env"
load_env_file "$SCRIPT_DIR/.env"

# 설정(환경변수)에서 호스트/포트 읽기
MATH_HOST="${MCP_MATH_UTILITY_HOST:-${MCP_HOST:-127.0.0.1}}"
MATH_PORT="${MCP_MATH_UTILITY_PORT:-${MCP_PORT:-8000}}"
WEATHER_HOST="${MCP_WEATHER_API_HOST:-${MCP_HOST:-127.0.0.1}}"
WEATHER_PORT="${MCP_WEATHER_API_PORT:-${MCP_PORT:-8001}}"
HEALTH_HOST="${MCP_CAT_HEALTH_HOST:-${MCP_HOST:-127.0.0.1}}"
HEALTH_PORT="${MCP_CAT_HEALTH_PORT:-${MCP_PORT:-8002}}"
CORE_HOST="${MCP_OCR_CORE_HOST:-${MCP_HOST:-127.0.0.1}}"
CORE_PORT="${MCP_OCR_CORE_PORT:-${MCP_PORT:-8003}}"
LAB_HOST="${MCP_EXTRACT_LAB_REPORT_HOST:-${MCP_HOST:-127.0.0.1}}"
LAB_PORT="${MCP_EXTRACT_LAB_REPORT_PORT:-8004}"
MEM_HOST="${MCP_MEMORY_HOST:-${MCP_HOST:-127.0.0.1}}"
MEM_PORT="${MCP_MEMORY_PORT:-8005}"

# 각 서버를 백그라운드에서 실행
echo "1️⃣ Math & Utility Server 시작 (${MATH_HOST}:${MATH_PORT})..."
cd "$SCRIPT_DIR/utility"
python math_utility_server.py &
MATH_PID=$!

echo "2️⃣ Weather & API Server 시작 (${WEATHER_HOST}:${WEATHER_PORT})..."
cd "$SCRIPT_DIR/weather"
python weather_api_server.py &
WEATHER_PID=$!

echo "3️⃣ Cat Health Server 시작 (${HEALTH_HOST}:${HEALTH_PORT})..."
cd "$SCRIPT_DIR/health"
python cat_health_server.py &
HEALTH_PID=$!

# OCR API Server
echo "4️⃣ OCR Core Server 시작 (${CORE_HOST}:${CORE_PORT})..."
cd "$SCRIPT_DIR/ocr_core"
python core_ocr_server.py &
CORE_PID=$!

echo "5️⃣ Lab Report OCR Server 시작 (${LAB_HOST}:${LAB_PORT})..."
cd "$SCRIPT_DIR/lab_report"
python extract_lab_report_server.py &
LAB_PID=$!

echo "6️⃣ Memory Server 시작 (${MEM_HOST}:${MEM_PORT})..."
cd "$SCRIPT_DIR/memory"
python memory_server.py &
MEM_PID=$!

# 서버 시작 대기
echo "⏳ 서버들이 시작되기를 기다리는 중... (10초)"
sleep 10

# 서버 상태 확인
echo "🔍 서버 상태 확인 중..."

if curl -s http://${MATH_HOST}:${MATH_PORT}/health > /dev/null 2>&1; then
    echo "✅ Math & Utility Server (${MATH_HOST}:${MATH_PORT}) - 정상"
else
    echo "❌ Math & Utility Server (${MATH_HOST}:${MATH_PORT}) - 오류"
fi

if curl -s http://${WEATHER_HOST}:${WEATHER_PORT}/health > /dev/null 2>&1; then
    echo "✅ Weather & API Server (${WEATHER_HOST}:${WEATHER_PORT}) - 정상"
else
    echo "❌ Weather & API Server (${WEATHER_HOST}:${WEATHER_PORT}) - 오류"
fi

if curl -s http://${HEALTH_HOST}:${HEALTH_PORT}/health > /dev/null 2>&1; then
    echo "✅ Cat Health Server (${HEALTH_HOST}:${HEALTH_PORT}) - 정상"
else
    echo "❌ Cat Health Server (${HEALTH_HOST}:${HEALTH_PORT}) - 오류"
fi

if curl -s http://${CORE_HOST}:${CORE_PORT}/health > /dev/null 2>&1; then
    echo "✅ OCR Core Server (${CORE_HOST}:${CORE_PORT}) - 정상"
else
    echo "❌ OCR Core Server (${CORE_HOST}:${CORE_PORT}) - 오류"
fi

if curl -s http://${LAB_HOST}:${LAB_PORT}/health > /dev/null 2>&1; then
    echo "✅ Lab Report OCR Server (${LAB_HOST}:${LAB_PORT}) - 정상"
else
    echo "❌ Lab Report OCR Server (${LAB_HOST}:${LAB_PORT}) - 오류"
fi

if curl -s http://${MEM_HOST}:${MEM_PORT}/health > /dev/null 2>&1; then
    echo "✅ Memory Server (${MEM_HOST}:${MEM_PORT}) - 정상"
else
    echo "❌ Memory Server (${MEM_HOST}:${MEM_PORT}) - 오류"
fi

echo ""
echo "🎉 Multi-MCP Server 시스템이 실행되었습니다!"
echo ""
echo "📊 서버 정보:"
echo "   🧮 Math & Utility: http://${MATH_HOST}:${MATH_PORT}"
echo "   🌤️ Weather & API:   http://${WEATHER_HOST}:${WEATHER_PORT}"
echo "   🐱 Cat Health:      http://${HEALTH_HOST}:${HEALTH_PORT}"
echo "   🖼️ OCR Core:        http://${CORE_HOST}:${CORE_PORT}"
echo "   🗂️ Lab Report OCR:  http://${LAB_HOST}:${LAB_PORT}"
echo "   🧠 Memory:          http://${MEM_HOST}:${MEM_PORT}"
echo ""
echo "🚀 클라이언트 실행 방법:"
echo "   streamlit run frontend/app.py"
echo "   # 또는 다음과 같이 실행할 수 있습니다:"
echo "   cd $(cd "$SCRIPT_DIR/../../frontend" && pwd) && streamlit run app.py"
echo ""
echo "🛑 서버 종료 방법:"
echo "   bash stop_servers.sh"
echo ""
echo "📋 프로세스 ID:"
echo "   Math Server PID: $MATH_PID"
echo "   Weather Server PID: $WEATHER_PID"  
echo "   Health Server PID: $HEALTH_PID"
echo "   OCR Core PID:     $CORE_PID"
echo "   Lab OCR PID:      $LAB_PID"
echo "   Memory PID:       $MEM_PID"

# PID 정보를 파일에 저장 (종료시 사용)
echo "$MATH_PID" > /tmp/math_server.pid
echo "$WEATHER_PID" > /tmp/weather_server.pid
echo "$HEALTH_PID" > /tmp/health_server.pid
echo "$CORE_PID" > /tmp/ocr_core_server.pid
echo "$LAB_PID" > /tmp/extract_lab_report_server.pid
echo "$MEM_PID" > /tmp/memory_server.pid

echo ""
echo "💡 팁: 로그를 보려면 각 서버 디렉토리에서 로그 파일을 확인하세요."
