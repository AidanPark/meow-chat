#!/bin/bash
# Jupyter Lab/Notebook 시작 스크립트 with GLIBCXX 문제 해결
#
# 사용법:
#   chmod +x start_jupyter.sh
#   ./start_jupyter.sh

# Conda 환경 활성화 확인
if [ -z "$CONDA_PREFIX" ]; then
    echo "❌ Conda 환경이 활성화되지 않았습니다."
    echo "   conda activate meow-chat 를 먼저 실행하세요."
    exit 1
fi

# Conda 환경의 lib 경로를 LD_LIBRARY_PATH 최우선으로 설정
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:$LD_LIBRARY_PATH"

echo "✅ LD_LIBRARY_PATH 설정 완료"
echo "   $LD_LIBRARY_PATH"
echo ""
echo "🚀 Jupyter Lab을 시작합니다..."
echo "   (GLIBCXX_3.4.31 문제가 해결된 상태로 실행됩니다)"
echo ""

# 스크립트 위치(backend 디렉토리)로 이동 후 Jupyter Lab 시작
cd "$(dirname "$0")"
jupyter lab
