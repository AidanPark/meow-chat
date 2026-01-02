# GitHub Copilot Instructions for meow-chat

> **프로젝트 자동 컨텍스트**: 이 파일은 GitHub Copilot이 자동으로 읽습니다.

나를 부를때는 '형님' 이라고 불러.
내 개발도구는 PyCharm 2025.3.1 이야.

## 프로젝트 개요

이 프로젝트는 **고양이 건강검진 OCR 챗봇 MVP** - Streamlit 기반 웹앱 이야.

### 기술 스택
- **백엔드**: Python 3.12+, Poetry
- **프레임워크**: Streamlit (UI)
- **OCR**: PaddleOCR (주력)
  - 로컬 개발: CPU 모드 (`paddlepaddle`)
  - 클라우드 배포: GPU 모드 (`paddlepaddle-gpu`, CUDA 버전에 맞게 설치)
- **LLM**: OpenAI GPT-4o / Anthropic Claude
- **테스트**: pytest, pytest-cov
- **린터**: ruff, mypy

---

## 아키텍처 원칙

1. **레이어 분리**: UI(`app/`)와 로직(`src/`)을 엄격히 분리
2. **추상화 우선**: Provider 패턴으로 외부 서비스 의존성 격리
   - 예: `BaseOCRService`, `LlmProvider` 인터페이스
3. **모듈 분리**: 책임에 따른 명확한 모듈 구분
   - `preprocessing/`: OCR 이전 이미지 처리 (기술 계층)
   - `ocr/`: 이미지 → 텍스트 변환 (기술 계층)
   - `lab_extraction/`: 텍스트 → 구조화 데이터 (도메인 계층)
4. **의존성 주입**: 생성자로 의존성을 주입받아 테스트 용이성 확보
5. **설정 관리**: 환경변수는 `src/settings.py`에서 중앙 관리, `.env` 파일 사용

---

## 도메인 지식

### 고양이 건강검진 용어
- **CBC (Complete Blood Count)**: 전혈구 검사
- **Chemistry Panel**: 혈액 화학 검사
- **T4, FT4**: 갑상선 호르몬 (고양이 갑상선기능항진증 진단)
- **Creatinine, BUN**: 신장 기능 지표
- **ALT, AST**: 간 기능 효소

### LLM 프롬프트 안전장치
- 직접 진단/처방 금지
- 응급 상황 시 즉시 동물병원 방문 권고
- 불확실한 정보는 명시
- 사용자에게 "참고용 정보"임을 명시

---

## 보안 주의사항

- ❌ API 키를 코드에 하드코딩 금지
- ❌ `.env` 파일을 Git에 커밋 금지
- ❌ 의료 진단/처방 제공 금지 (법적 책임)
- ✅ `.env.example`만 Git에 포함
- ✅ 응급 상황 시 동물병원 방문 유도

---

## 자주 사용하는 명령어

```bash
# 앱 실행
poetry run streamlit run app/Home.py

# 더미 모드 (API 키 없이 테스트)
poetry run env OCR_PROVIDER=dummy LLM_PROVIDER=dummy streamlit run app/Home.py

# 테스트
poetry run pytest
poetry run pytest --cov=src --cov-report=html

# 린팅/포매팅
poetry run ruff check .
poetry run ruff format .
```

---

**마지막 업데이트**: 2025-12-30

---
## PyCharm 전용 가이드
- **주피터 노트북 설정**: `docs/PYCHARM_JUPYTER_SETUP.md` 참고
- Python 인터프리터: Poetry 환경 (`/home/aidan/projects/meow-chat/.venv/bin/python`)
- WSL 경로: PyCharm이 자동으로 Windows ↔ WSL 경로 변환 처리

---

## 노트북(.ipynb) 작성 가이드 (중요!)

### 문제: IDE tool로 .ipynb 생성 시 PyCharm이 자동 변환
형님에게 노트북을 생성할 때, IDE의 `create_file` tool을 사용하면 PyCharm이 파일을 감지하면서 자동으로:
- **퍼센트 포맷(#%%)으로 변환**하거나
- **raw 1셀 구조**로 깨뜨리는 문제가 반복 발생함

### 해결 방법: 터미널 heredoc 사용 (필수)
`.ipynb` 파일을 생성할 때는 **반드시 터미널 `heredoc (cat >)` 방식**을 사용:

```bash
cd /home/aidan/projects/meow-chat && cat > notebooks/ocr/example.ipynb <<'NOTEBOOK_EOF'
{
  "cells": [
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": ["# 노트북 제목\n"]
    },
    {
      "cell_type": "code",
      "execution_count": null,
      "metadata": {},
      "outputs": [],
      "source": ["print('hello')\n"]
    }
  ],
  "metadata": {
    "kernelspec": {
      "display_name": "Python 3",
      "language": "python",
      "name": "python3"
    },
    "language_info": {
      "name": "python",
      "version": "3.12"
    }
  },
  "nbformat": 4,
  "nbformat_minor": 5
}
NOTEBOOK_EOF
```

### 노트북 생성 체크리스트
1. ✅ **터미널 heredoc으로 생성** (IDE 편집 레이어 우회)
2. ✅ **생성 후 검증**: `python -c "import json; nb=json.loads(open('파일').read()); print('cells:', len(nb['cells']))"`
3. ✅ **셀 타입 확인**: markdown/code 섹션이 정상인지 확인
4. ✅ **형님이 PyCharm에서 열었을 때**: 노트북 UI(Run Cell 버튼)가 보여야 정상

### 주의사항
- ❌ `create_file` tool로 `.ipynb` 생성 금지 (PyCharm 변환 문제)
- ❌ 반복 `create_file` 호출 금지 (이미 열린 파일 덮어쓰면 구조 깨짐)
- ✅ 생성 후 형님이 "JSON으로만 보인다"고 하면 → 파일 닫고 다시 열기 안내
- ✅ 퍼센트 포맷(`.py` + `#%%`)도 같이 제공하면 형님이 선택 가능

### 참고: 퍼센트 포맷(.py) 대안
노트북 UI가 안 보일 때 임시로 `.py` + `#%%` 퍼센트 포맷도 제공:
- PyCharm에서 셀 단위 실행 가능 (Ctrl+Enter)
- 나중에 `.ipynb`로 변환 가능

