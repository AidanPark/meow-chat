# # Jupyter Notebook GLIBCXX 문제 해결 가이드

# ## 문제 증상

# 노트북에서 `import fitz` (PyMuPDF) 시 다음 에러 발생:
# ```
# ImportError: /lib/x86_64-linux-gnu/libstdc++.so.6: version `GLIBCXX_3.4.31' not found
# ```

# ## 원인

# 1. **PyMuPDF 패키지**가 `libtesseract.so.5`를 포함하고 있음
# 2. 이 라이브러리가 `GLIBCXX_3.4.31` 요구
# 3. **시스템 libstdc++**는 `GLIBCXX_3.4.30`까지만 지원 (Ubuntu 22.04 기준)
# 4. **Conda 환경 libstdc++**는 `GLIBCXX_3.4.34`까지 지원
# 5. 하지만 동적 링커가 시스템 경로를 먼저 찾아서 에러 발생

# ## 해결 방법

# ### ✅ 방법 1: start_jupyter.sh 사용 (가장 간단)

# ```bash
# # 프로젝트 루트에서
# chmod +x start_jupyter.sh
# ./start_jupyter.sh
# ```

# 이 스크립트는:
# - `LD_LIBRARY_PATH`에 Conda 환경의 lib 경로를 최우선으로 추가
# - Jupyter Lab 시작

# ### ✅ 방법 2: 수동으로 환경변수 설정

# ```bash
# # Conda 환경 활성화
# conda activate meow-chat

# # 라이브러리 경로 설정
# export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH

# # Jupyter 시작
# jupyter lab
# ```

# ### ✅ 방법 3: VS Code에서 직접 사용

# 1. 노트북의 첫 번째 Python 셀 실행 (libstdc++ 로드)
# 2. VS Code 명령 팔레트: `Jupyter: Restart Kernel`
# 3. 다시 셀들을 순서대로 실행

# **참고**: 방법 3은 완전하지 않을 수 있어 방법 1 권장

# ## 기술 세부사항

# ### 심볼릭 링크 생성 (이미 완료됨)

# ```bash
# ln -sf $CONDA_PREFIX/lib/libstdc++.so.6.0.34 $CONDA_PREFIX/lib/libstdc++.so.6
# ```

# ### 라이브러리 검색 순서

# Linux 동적 링커는 다음 순서로 라이브러리를 찾습니다:
# 1. `RPATH` (바이너리에 하드코딩)
# 2. `LD_LIBRARY_PATH` (환경변수) ← 우리가 사용
# 3. `RUNPATH` (바이너리에 하드코딩, 낮은 우선순위)
# 4. `/etc/ld.so.conf` (시스템 기본)
# 5. `/lib`, `/usr/lib` 등

# ### 확인 방법

# ```bash
# # 현재 환경의 GLIBCXX 버전 확인
# strings $CONDA_PREFIX/lib/libstdc++.so.6 | grep GLIBCXX_3.4.3

# # 시스템 GLIBCXX 버전 확인
# strings /lib/x86_64-linux-gnu/libstdc++.so.6 | grep GLIBCXX_3.4.3

# # libtesseract가 참조하는 libstdc++ 확인
# ldd $CONDA_PREFIX/lib/python3.10/site-packages/pymupdf/../../.././libtesseract.so.5 | grep libstdc
# ```

# ## 대안 솔루션 (권장하지 않음)

# ### ❌ 시스템 libstdc++ 업그레이드
# - 시스템 전체에 영향
# - 안정성 위험
# - Ubuntu 버전 업그레이드 필요 또는 비공식 PPA 사용

# ### ⚠️ pymupdf 다운그레이드
# ```bash
# pip install 'pymupdf<1.24.0'
# ```
# - 오래된 버전은 낮은 GLIBCXX 요구할 수 있음
# - 기능 제한 가능성
# - 테스트 필요

# ## 참고 문서

# - Linux Dynamic Linker: `man ld.so`
# - GCC libstdc++ ABI: https://gcc.gnu.org/onlinedocs/libstdc++/manual/abi.html



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
