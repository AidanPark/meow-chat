#!/bin/bash
# meow-chat Poetry 가상환경 활성화 스크립트
# 사용법: source scripts/activate.sh

PROJECT_DIR="/home/aidan/projects/meow-chat"
VENV_ACTIVATE="$PROJECT_DIR/.venv/bin/activate"

if [ -f "$VENV_ACTIVATE" ]; then
    source "$VENV_ACTIVATE"
    cd "$PROJECT_DIR" || exit 1
    echo "🐱 meow-chat 가상환경 활성화 완료!"
    echo "📂 위치: $PROJECT_DIR"
    echo "🐍 Python: $(python --version)"
else
    echo "❌ 가상환경을 찾을 수 없습니다: $VENV_ACTIVATE"
    echo "💡 poetry install 을 먼저 실행하세요."
    exit 1
fi

