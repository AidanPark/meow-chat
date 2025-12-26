#!/bin/bash
# Jupyter Notebook 실행 스크립트

echo "🚀 Jupyter Notebook 시작..."
echo ""
echo "📂 notebooks/ 디렉토리에서 실행합니다."
echo "🌐 브라우저에서 자동으로 열립니다."
echo ""

cd "$(dirname "$0")/../notebooks" || exit

poetry run jupyter notebook


