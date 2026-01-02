#!/bin/bash
# meow-chat Streamlit 앱 실행 스크립트

PROJECT_DIR="/home/aidan/projects/meow-chat"

# 프로젝트 루트로 이동
cd "$PROJECT_DIR" || exit 1

echo "🐱 meow-chat 앱을 실행합니다..."
echo "📂 위치: $PROJECT_DIR"
echo ""

# Poetry를 통해 Streamlit 앱 실행
poetry run streamlit run app/Home.py

# ============================================================================
# 실행 옵션 예시
# ============================================================================

# 1. 더미 모드 (API 키 없이 테스트)
# OCR_PROVIDER=dummy LLM_PROVIDER=dummy poetry run streamlit run app/Home.py

# 2. 오케스트레이션 모델 분리 (권장)
# - 의도분류: gpt-5-nano (빠르고 저렴)
# - 스몰톡: gpt-5-mini (중간 품질)
# - 검사분석: gpt-4.1 (고품질)
#
# OPENAI_MODEL_INTENT=gpt-5-nano \
# OPENAI_MODEL_CHAT=gpt-5-mini \
# OPENAI_MODEL_ANALYSIS=gpt-4.1 \
# poetry run streamlit run app/Home.py

# 3. 디버그 모드 (사이드바에 라우팅 정보 표시)
# APP_DEBUG=true poetry run streamlit run app/Home.py

# 4. 종료 명령
# pkill -f "streamlit run app/Home.py"
# 또는: ./scripts/manage_app.sh stop
