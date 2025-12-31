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
