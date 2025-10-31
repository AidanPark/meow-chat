#!/bin/bash

# Multi-MCP Server 종료 스크립트

echo "🛑 Multi-MCP Server 시스템 종료 중..."

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
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "⚠️ 포트 8000이 여전히 사용 중입니다"
else
    echo "✅ 포트 8000 해제됨"
fi

if lsof -ti:8001 > /dev/null 2>&1; then
    echo "⚠️ 포트 8001이 여전히 사용 중입니다"
else
    echo "✅ 포트 8001 해제됨"
fi

if lsof -ti:8002 > /dev/null 2>&1; then
    echo "⚠️ 포트 8002가 여전히 사용 중입니다"
else
    echo "✅ 포트 8002 해제됨"
fi

if lsof -ti:8003 > /dev/null 2>&1; then
    echo "⚠️ 포트 8003이 여전히 사용 중입니다"
else
    echo "✅ 포트 8003 해제됨"
fi

echo ""
echo "🎉 Multi-MCP Server 시스템이 종료되었습니다!"