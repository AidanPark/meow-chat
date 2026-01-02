#!/bin/bash
# meow-chat Streamlit 앱 실행 스크립트 (더미 모드 - API 키 불필요)

PROJECT_DIR="/home/aidan/projects/meow-chat"

# 프로젝트 루트로 이동
cd "$PROJECT_DIR" || exit 1

echo "🐱 meow-chat 앱을 더미 모드로 실행합니다..."
echo "📂 위치: $PROJECT_DIR"
echo "🧪 OCR/LLM 더미 제공자 사용 (API 키 불필요)"
echo ""

# 더미 모드로 실행
OCR_PROVIDER=dummy LLM_PROVIDER=dummy poetry run streamlit run app/Home.py

