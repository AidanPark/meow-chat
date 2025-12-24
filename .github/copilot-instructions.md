# GitHub Copilot Instructions for meow-chat

> **프로젝트 자동 컨텍스트**: 이 파일은 GitHub Copilot이 자동으로 읽습니다.

## 프로젝트 개요

**고양이 건강검진 OCR 챗봇 MVP** - Streamlit 기반 웹앱

### 기술 스택
- **백엔드**: Python 3.10+, Poetry
- **프레임워크**: Streamlit (UI)
- **OCR**: Google Cloud Vision API
- **LLM**: OpenAI GPT-4o / Anthropic Claude
- **테스트**: pytest, pytest-cov
- **린터**: ruff, mypy

### 프로젝트 구조
```
meow-chat/
├── app/                    # Streamlit UI 레이어
│   ├── Home.py            # 메인 화면
│   └── pages/             # 멀티페이지 앱
├── src/                    # 비즈니스 로직
│   ├── settings.py        # 환경변수 관리
│   ├── services/
│   │   ├── ocr/           # OCR Provider (추상 인터페이스 + 구현체)
│   │   ├── llm/           # LLM Provider (OpenAI, Anthropic)
│   │   └── chat/          # 채팅 오케스트레이션
│   └── utils/             # 이미지/PDF 처리
└── tests/                  # pytest 테스트
```

---

## 개발 가이드라인

### 코드 스타일
- **타입 힌트 필수**: 모든 함수/클래스에 타입 어노테이션 사용
- **docstring**: 공개 API는 Google Style docstring 작성
- **명명 규칙**: 
  - 클래스: `PascalCase`
  - 함수/변수: `snake_case`
  - 상수: `UPPER_SNAKE_CASE`
- **린팅**: `ruff check .` 통과 필수
- **포매팅**: `ruff format .` 적용

### 아키텍처 원칙
1. **레이어 분리**: UI(`app/`)와 로직(`src/`)을 엄격히 분리
2. **추상화 우선**: Provider 패턴으로 외부 서비스 의존성 격리
   - 예: `OcrProvider`, `LlmProvider` 인터페이스
3. **의존성 주입**: 생성자로 의존성을 주입받아 테스트 용이성 확보
4. **설정 관리**: 환경변수는 `src/settings.py`에서 중앙 관리

### 환경변수 규칙
- **절대 하드코딩 금지**: API 키, 시크릿은 `.env` 파일 사용
- **`.env.example` 제공**: 필요한 환경변수 템플릿 유지
- **타입 안전**: `pydantic.BaseSettings`로 환경변수 검증

### 테스트 전략
- **단위 테스트**: 각 Provider 클래스별 독립 테스트
- **통합 테스트**: `ChatService`의 OCR→LLM 파이프라인 검증
- **Fixture 활용**: `tests/conftest.py`에 공통 fixture 정의
- **외부 API 모킹**: 실제 API 호출은 CI에서 스킵 가능하도록

---

## 도메인 지식

### 고양이 건강검진 용어
- **CBC (Complete Blood Count)**: 전혈구 검사
- **Chemistry Panel**: 혈액 화학 검사
- **T4, FT4**: 갑상선 호르몬 (고양이 갑상선기능항진증 진단)
- **Creatinine, BUN**: 신장 기능 지표
- **ALT, AST**: 간 기능 효소

### 프롬프트 작성 원칙 (LLM)
- **역할 명시**: "수의학 지식을 갖춘 어시스턴트"
- **안전장치**: 
  - 직접 진단/처방 금지
  - 응급 상황 시 즉시 동물병원 방문 권고
  - 불확실한 정보는 명시
- **사용자 경험**: 
  - 전문 용어는 쉽게 풀어서 설명
  - 차분하고 친근한 톤
  - 이모지 적절히 사용 (🐱, 💊, ⚠️ 등)

---

## 현재 개발 상태

### 완료된 작업 (Phase 1)
- ✅ 프로젝트 스캐폴딩 (Poetry + 디렉토리 구조)
- ✅ 설정 관리 (`src/settings.py`)
- ✅ OCR Provider 인터페이스 + Dummy 구현
- ✅ LLM Provider 인터페이스 + OpenAI/Anthropic 구현
- ✅ 기본 Streamlit UI (Home.py)
- ✅ 채팅 서비스 오케스트레이션
- ✅ Google Cloud Vision 연동 완료

### 진행 중 (Phase 2)
- 🔄 Google Vision API 실제 이미지 테스트
- 🔄 프롬프트 튜닝 (고양이 건강 상담 품질 개선)
- 🔄 에러 핸들링 강화

### 다음 작업 (Phase 3)
- ⏳ PDF 다중 페이지 처리 개선
- ⏳ 이미지 전처리 (회전 보정, 노이즈 제거)
- ⏳ UI/UX 개선 (모바일 최적화)

---

## 자주 사용하는 명령어

```bash
# 의존성 설치
poetry install

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
poetry run mypy src/

# Poetry 가상환경 활성화
poetry shell
```

---

## AI 어시스턴트 응답 가이드

### 코드 생성 시
- **타입 힌트 포함**: 반환 타입, 매개변수 타입 명시
- **docstring 작성**: 함수 목적, 매개변수, 반환값 설명
- **에러 처리**: 예외 발생 가능 지점에 try-except 또는 명시적 검증
- **테스트 코드 제안**: 주요 기능은 테스트 케이스와 함께 제공

### 설명 시
- **초보자 친화적**: 전문 용어는 쉬운 말로 풀어서 설명
- **실행 가능한 예제**: 추상적인 설명보다 구체적인 코드 예제 제공
- **컨텍스트 유지**: 이 프로젝트의 기존 구조와 패턴을 따름

### 디버깅 지원 시
1. 에러 메시지 분석
2. 관련 파일/코드 위치 파악
3. 원인 설명 + 해결 방법 제시
4. 재발 방지를 위한 개선 제안

---

## 참고 문서

- **프로젝트 상세 명세**: `CLAUDE.md` (전체 아키텍처 및 구현 가이드)
- **API 키 설정**: `docs/API_KEYS_SETUP.md`
- **빠른 시작**: `docs/QUICKSTART.md`
- **Poetry 가이드**: `docs/POETRY_SHELL_GUIDE.md`

---

## 보안 및 주의사항

### 절대 금지
- ❌ API 키를 코드에 하드코딩
- ❌ `.env` 파일을 Git에 커밋
- ❌ 서비스 계정 JSON 파일 노출
- ❌ 의료 진단/처방 제공 (법적 책임)

### 권장 사항
- ✅ `.env.example`만 Git에 포함
- ✅ `.gitignore`에 민감 파일 추가
- ✅ 사용자에게 "참고용 정보"임을 명시
- ✅ 응급 상황 시 동물병원 방문 유도

---

**마지막 업데이트**: 2025-01-24  
**프로젝트 상태**: Phase 1 완료, Phase 2 진행 중

