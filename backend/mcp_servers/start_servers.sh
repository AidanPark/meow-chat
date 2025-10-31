#!/bin/bash

# Multi-MCP Server 실행 스크립트

echo "🚀 Multi-MCP Server 시스템 시작 중..."

# 현재 실행 중인 서버들 종료
echo "기존 서버 프로세스 종료 중..."
pkill -f "math_utility_server.py"
pkill -f "weather_api_server.py" 
pkill -f "cat_health_server.py"
pkill -f "ocr_api_server.py"

sleep 2

# conda 환경 활성화 체크
if [[ "$CONDA_DEFAULT_ENV" != "meow-chat" ]]; then
    echo "⚠️  meow-chat conda 환경을 먼저 활성화해주세요:"
    echo "conda activate meow-chat"
    exit 1
fi

# 각 서버를 백그라운드에서 실행
echo "1️⃣ Math & Utility Server 시작 (포트 8000)..."
cd /home/aidan/work/meow-chat/mcp_servers/utility
python math_utility_server.py &
MATH_PID=$!

echo "2️⃣ Weather & API Server 시작 (포트 8001)..."
cd /home/aidan/work/meow-chat/mcp_servers/weather
python weather_api_server.py &
WEATHER_PID=$!

echo "3️⃣ Cat Health Server 시작 (포트 8002)..."
cd /home/aidan/work/meow-chat/mcp_servers/health
python cat_health_server.py &
HEALTH_PID=$!

# OCR API Server
echo "4️⃣ OCR API Server 시작 (포트 8003)..."
cd /home/aidan/work/meow-chat/mcp_servers/ocr
python ocr_api_server.py &
OCR_PID=$!

# 서버 시작 대기
echo "⏳ 서버들이 시작되기를 기다리는 중... (5초)"
sleep 5

# 서버 상태 확인
echo "🔍 서버 상태 확인 중..."

if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Math & Utility Server (8000) - 정상"
else
    echo "❌ Math & Utility Server (8000) - 오류"
fi

if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "✅ Weather & API Server (8001) - 정상"
else
    echo "❌ Weather & API Server (8001) - 오류"
fi

if curl -s http://localhost:8002/health > /dev/null 2>&1; then
    echo "✅ Cat Health Server (8002) - 정상"
else
    echo "❌ Cat Health Server (8002) - 오류"
fi

if curl -s http://localhost:8003/health > /dev/null 2>&1; then
    echo "✅ OCR API Server (8003) - 정상"
else
    echo "❌ OCR API Server (8003) - 오류"
fi

echo ""
echo "🎉 Multi-MCP Server 시스템이 실행되었습니다!"
echo ""
echo "📊 서버 정보:"
echo "   🧮 Math & Utility: http://localhost:8000"
echo "   🌤️ Weather & API:   http://localhost:8001"
echo "   🐱 Cat Health:      http://localhost:8002"
echo "   🖼️ OCR API:         http://localhost:8003"
echo ""
echo "🚀 클라이언트 실행 방법:"
echo "   streamlit run frontend/app.py"
echo "   # 또는 다음과 같이 실행할 수 있습니다:"
echo "   cd /home/aidan/work/meow-chat/frontend && streamlit run app.py"
echo ""
echo "🛑 서버 종료 방법:"
echo "   bash stop_servers.sh"
echo ""
echo "📋 프로세스 ID:"
echo "   Math Server PID: $MATH_PID"
echo "   Weather Server PID: $WEATHER_PID"  
echo "   Health Server PID: $HEALTH_PID"
echo "   OCR Server PID:   $OCR_PID"

# PID 정보를 파일에 저장 (종료시 사용)
echo "$MATH_PID" > /tmp/math_server.pid
echo "$WEATHER_PID" > /tmp/weather_server.pid
echo "$HEALTH_PID" > /tmp/health_server.pid
echo "$OCR_PID" > /tmp/ocr_server.pid

echo ""
echo "💡 팁: 로그를 보려면 각 서버 디렉토리에서 로그 파일을 확인하세요."