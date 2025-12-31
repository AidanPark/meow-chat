# 운영/설정 가이드 (meow-chat)

> **목적**: 실행 방법, 환경변수, 외부 API 설정 등 "운영/세팅" 정보를 한 곳에 모읍니다.
> `docs/plan.md`는 순수 계획(우선순위/로드맵/성공 기준)만 남깁니다.

## 1) 환경변수

- 환경변수는 `.env` 파일로 관리합니다.
- 레포에는 `.env`를 커밋하지 않고, `.env.example`만 포함합니다.

### 1.1 주요 환경변수

- OCR
  - `OCR_PROVIDER`: `paddleocr | google | easy | dummy`
  - `GOOGLE_APPLICATION_CREDENTIALS`: Google Vision 사용 시 서비스 계정 JSON 경로
- LLM
  - `LLM_PROVIDER`: `openai | anthropic | dummy`
  - `OPENAI_API_KEY`
  - `ANTHROPIC_API_KEY`

> 최신 값/예시는 `.env.example`를 단일 소스로 봅니다.

## 2) Google Cloud Vision API 설정

1. Google Cloud Console에서 프로젝트 생성
2. Cloud Vision API 활성화
3. 서비스 계정 생성 및 JSON 키 다운로드
4. `GOOGLE_APPLICATION_CREDENTIALS` 환경변수 설정

자세한 내용은 `docs/API_KEYS_SETUP.md`를 참고합니다.

## 3) 로컬 실행

- 앱 실행
  - `poetry run streamlit run app/Home.py`
- 더미 모드
  - `poetry run env OCR_PROVIDER=dummy LLM_PROVIDER=dummy streamlit run app/Home.py`

자세한 실행 흐름은 `docs/QUICKSTART.md`도 참고합니다.

## 4) Jupyter (PyCharm)

- 기본적으로 PyCharm의 Jupyter 지원을 사용합니다.
- 커널/인터프리터 이슈가 있으면 `docs/PYCHARM_JUPYTER_SETUP.md`를 참고합니다.

## 5) 테스트/품질

- 테스트
  - `poetry run pytest`
  - `poetry run pytest --cov=src --cov-report=html`
- 린트/포맷
  - `poetry run ruff check .`
  - `poetry run ruff format .`
- 타입체크
  - `poetry run mypy src/`

자세한 내용은 `docs/TEST_GUIDE.md`를 참고합니다.

