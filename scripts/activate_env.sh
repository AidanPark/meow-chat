#!/bin/bash
# meow-chat 프로젝트 가상환경 활성화 스크립트

PROJECT_DIR="/home/aidan/projects/meow-chat"
VENV_ACTIVATE="$PROJECT_DIR/.venv/bin/activate"

if [ -f "$VENV_ACTIVATE" ]; then
    echo "🐱 meow-chat Poetry 가상환경 활성화 중..."
    source "$VENV_ACTIVATE"
    cd "$PROJECT_DIR"
    echo "✅ 활성화 완료!"
    echo "📂 위치: $PROJECT_DIR"
    echo "🐍 Python: $(python --version)"
    echo ""
    echo "사용 가능한 명령어:"
    echo "  streamlit run app/Home.py       - 앱 실행"
    echo "  pytest                          - 테스트 실행"
    echo "  jupyter notebook                - Jupyter 노트북 실행"
    echo "  cd notebooks && jupyter notebook - 노트북 디렉토리에서 실행"
    echo "  deactivate                      - 가상환경 나가기"
else
    echo "❌ 가상환경을 찾을 수 없습니다: $VENV_ACTIVATE"
    exit 1
fi

