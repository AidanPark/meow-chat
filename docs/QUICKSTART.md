# 🚀 빠른 시작 가이드

냥닥터를 5분 안에 실행해보세요!

## ⚡ 초간단 실행

```bash
# 1. Poetry 설치 (아직 없다면)
curl -sSL https://install.python-poetry.org | python3 -

# 2. 의존성 설치
poetry install

# 3. 가상환경 활성화 및 앱 실행
source scripts/activate_env.sh
streamlit run app/Home.py
```

브라우저에서 http://localhost:8501 로 접속! 🎉

---

## 📝 단계별 상세 가이드

### Step 1: Poetry 설치

```bash
# Linux/Mac/WSL
curl -sSL https://install.python-poetry.org | python3 -

# 또는 pipx 사용
pipx install poetry

# 설치 확인
poetry --version
```

### Step 2: 프로젝트 설정

```bash
# 저장소 이동
cd meow-chat

# 의존성 설치 (가상환경 자동 생성)
poetry install

# 설치 확인
poetry show
```

### Step 3: 환경 설정

`.env` 파일에 API 키를 설정합니다:

```bash
# OCR 설정
OCR_PROVIDER=google
GOOGLE_APPLICATION_CREDENTIALS=.credentials/google-vision-key.json

# LLM 설정
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...

# 앱 설정
APP_DEBUG=true
LOG_LEVEL=INFO
```

📘 **API 키 발급 방법**: [docs/API_KEYS_SETUP.md](./API_KEYS_SETUP.md)

**Google Cloud Vision 서비스 계정 설정:**
- Google Cloud Console에서 서비스 계정 JSON 키 다운로드
- `.credentials/` 디렉토리에 `google-vision-key.json`으로 저장
- `.env` 파일의 경로가 올바른지 확인

### Step 4: 실행

```bash
# 방법 1: 가상환경 활성화 스크립트 사용 (권장)
source scripts/activate_env.sh
streamlit run app/Home.py

# 방법 2: Poetry run
poetry run streamlit run app/Home.py

# 방법 3: Poetry shell 진입 후
poetry shell
streamlit run app/Home.py
```

---

## 🧪 테스트 실행

```bash
# 전체 테스트
poetry run pytest

# 상세 출력
poetry run pytest -v

# 커버리지 포함
poetry run pytest --cov=src --cov-report=html

# 특정 테스트만
poetry run pytest tests/test_ocr.py
```

---

## 🎯 사용 방법

### 1. 검진 결과지 업로드

- 사이드바에서 **"검진 결과지 업로드"**
- 이미지 (JPG, PNG) 또는 PDF 선택
- **"🔍 분석 시작"** 클릭

### 2. AI 분석 결과 확인

- OCR로 텍스트 자동 추출
- AI가 건강 상태 분석
- 이해하기 쉬운 설명 제공

### 3. 후속 질문

- 채팅창에 질문 입력
- "체중이 정상인가요?"
- "이 수치는 무엇을 의미하나요?"
- "어떤 관리가 필요한가요?"

---

## 🔧 문제 해결

### "Poetry를 찾을 수 없습니다"

```bash
# PATH에 Poetry 추가 (Linux/Mac/WSL)
export PATH="$HOME/.local/bin:$PATH"

# 영구 적용
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### "모듈을 찾을 수 없습니다"

```bash
# 의존성 재설치
poetry install --no-cache

# 가상환경 재생성
poetry env remove python
poetry install
```

### "포트가 이미 사용 중입니다"

```bash
# 다른 포트로 실행
poetry run streamlit run app/Home.py --server.port 8502
```

### "파일을 업로드할 수 없습니다"

- 파일 크기: 10MB 이하
- 지원 형식: JPG, PNG, PDF, WEBP
- 파일명에 특수문자 피하기

---

## 📊 프로젝트 구조

```
meow-chat/
├── app/
│   ├── Home.py           # 메인 Streamlit 앱
│   └── pages/            # 추가 페이지 (향후)
├── src/
│   ├── settings.py       # 설정 관리
│   ├── services/
│   │   ├── ocr/         # OCR 서비스
│   │   ├── llm/         # LLM 서비스
│   │   └── chat/        # 채팅 오케스트레이션
│   └── utils/           # 유틸리티
├── tests/               # 테스트 코드
├── docs/                # 문서
├── scripts/
│   └── activate_env.sh  # 가상환경 활성화 스크립트
├── pyproject.toml       # Poetry 설정
└── .env                 # 환경변수 (git 무시)
```

---

## 🎓 다음 단계

### 1. 실제 검진 결과지 테스트
- ✅ 실제 고양이 건강검진 결과지 업로드
- ✅ AI 분석 정확도 확인
- ✅ 다양한 형식(이미지, PDF) 테스트

### 2. API 설정 최적화
- 📘 [API 키 가이드](./API_KEYS_SETUP.md) 참고
- Google Cloud Vision API 사용량 모니터링
- OpenAI API 사용량 확인

### 3. 커스터마이징
- 프롬프트 수정 (`src/services/llm/prompts.py`)
- UI 개선 (`app/Home.py`)
- 추가 기능 구현

---

## 💡 팁

### 개발 모드

```bash
# 가상환경 활성화
source scripts/activate_env.sh

# 앱 실행 (코드 변경 시 자동 재시작)
streamlit run app/Home.py

# 디버그 모드로 실행
streamlit run app/Home.py --server.runOnSave true
```

### 코드 품질

```bash
# 가상환경 활성화 후
source scripts/activate_env.sh

# 린팅
ruff check .

# 포매팅
ruff format .

# 타입 체킹
mypy src/
```

### 로그 확인

```bash
# .env 파일에서 로그 레벨 조정
LOG_LEVEL=DEBUG
APP_DEBUG=true
```

---

## 📞 도움이 필요하신가요?

- 📖 [전체 문서](plan.md)
- 🔑 [API 키 가이드](./API_KEYS_SETUP.md)
- 🐛 [이슈 제보](../../issues)

즐거운 냥닥터 체험 되세요! 🐱✨

**마지막 업데이트**: 2025-01-24

