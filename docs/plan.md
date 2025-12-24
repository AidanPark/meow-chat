# Claude 작업 지시서: 냥닥터 - 고양이 건강검진 AI 상담 서비스

## 0) 프로젝트 개요

### 비전
**고양이의 생애주기와 함께하는 AI 디지털 주치의** - 단순 QA가 아닌, 반려묘의 전 생애를 동행하며 건강을 관리하는 서비스

### 핵심 컨셉
- **주치의 페르소나**: 공감적이고 친근하되, 의학적 판단 시에는 전문적이고 침착한 톤
- **장기 기억**: 검사/진료/투약/행동 변화를 장기적으로 기억하고 추적
- **Peer Data 비교**: 동종 코호트 데이터와 비교하여 정밀한 건강 위치 분석

### 사용자 흐름 (MVP)
1. 사용자가 **카메라 촬영, 갤러리 선택, 또는 PDF 업로드**로 검진 결과 문서를 전송
2. **Google Cloud Vision API**로 텍스트 추출 (OCR)
3. 추출된 검진 데이터를 컨텍스트로 **LLM API** 호출하여 맞춤형 건강 상담 제공

### 핵심 가치
- 복잡한 검진 결과지를 **이해되는 언어**로 설명
- 수치 이상 여부 해석 및 **동종 코호트 대비 위치** 분석
- **생애주기 전체를 기억**하는 연속성 있는 케어
- 향후 상용 서비스로 확장 가능한 아키텍처

---

## 1) 요구 사항

### 1.1 필수 기능
- [ ] Streamlit 앱을 **단일 명령으로 실행** 가능
- [ ] 모바일 브라우저에서 이미지 업로드 지원:
  - `st.camera_input()` - 카메라 촬영
  - `st.file_uploader()` - 갤러리/파일 선택 (이미지 + PDF)
- [ ] **Google Cloud Vision API** OCR 연동
- [ ] LLM 연동 (OpenAI GPT-4o 또는 Anthropic Claude)
- [ ] 고양이 건강 상담 특화 프롬프트

### 1.2 지원 파일 형식
| 형식 | 확장자 | 비고 |
|------|--------|------|
| 이미지 | `.jpg`, `.jpeg`, `.png`, `.webp`, `.heic` | 카메라 촬영 포함 |
| 문서 | `.pdf` | 다중 페이지 지원 |

### 1.3 MVP 범위 외 (Phase 2 이후)
- 사용자 인증/로그인
- 대화 기록 저장 (DB)
- 다중 반려동물 프로필 관리
- 알림/리마인더 기능

---

## 2) 기술 스택

### 2.1 핵심 의존성
Poetry를 사용하여 `pyproject.toml`로 관리합니다.

**프로덕션 의존성:**
- Python >= 3.10
- streamlit >= 1.28
- google-cloud-vision >= 3.0
- openai >= 1.0
- anthropic >= 0.20 (선택)
- pillow >= 10.0
- python-dotenv >= 1.0
- pydantic >= 2.0
- pdf2image >= 1.16 (PDF 처리용)

**Phase 2+ 의존성 (RAG/LangChain):**
- langchain >= 0.1.0
- langchain-openai >= 0.0.5
- langchain-community >= 0.0.10
- langgraph >= 0.0.20
- faiss-cpu >= 1.7 (Vector Store)
- chromadb >= 0.4 (대안 Vector Store)

### 2.2 개발 의존성
- pytest >= 7.0
- pytest-asyncio >= 0.21
- pytest-cov >= 4.1 (코드 커버리지)
- ruff >= 0.1 (린터 + 포매터)
- mypy >= 1.5 (타입 체커)

---

## 3) 프로젝트 구조

```
meow-chat/
├── README.md                    # 프로젝트 소개 및 실행 방법
├── CLAUDE.md                    # Claude Code 작업 컨텍스트
├── .gitignore
├── .env.example                 # 환경변수 템플릿
├── pyproject.toml               # Poetry 프로젝트 설정 및 의존성
├── poetry.lock                  # 의존성 버전 고정
│
├── app/                         # Streamlit UI 레이어
│   ├── Home.py                  # 메인 화면 (업로드 + 채팅)
│   └── pages/
│       ├── 1_Chat.py            # 채팅 전용 화면
│       ├── 2_History.py         # (Phase 2) 상담 기록
│       └── 3_Profile.py         # (Phase 2) 반려묘 프로필
│
├── src/                         # 비즈니스 로직
│   ├── __init__.py
│   ├── settings.py              # 환경변수 및 설정 관리
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   │
│   │   ├── ocr/                 # OCR 서비스
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # OcrProvider 추상 인터페이스
│   │   │   ├── google_vision.py # Google Cloud Vision 구현
│   │   │   └── dummy.py         # 개발/테스트용 더미
│   │   │
│   │   ├── llm/                 # LLM 서비스
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # LlmProvider 추상 인터페이스
│   │   │   ├── openai_llm.py    # OpenAI 구현
│   │   │   ├── anthropic_llm.py # Anthropic 구현
│   │   │   └── prompts.py       # 고양이 건강 상담 프롬프트
│   │   │
│   │   ├── chat/                # 채팅 오케스트레이션
│   │   │   ├── __init__.py
│   │   │   └── chat_service.py  # OCR + LLM 통합 서비스
│   │   │
│   │   ├── memory/              # (Phase 2) 장기 기억 관리
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # MemoryProvider 인터페이스
│   │   │   ├── conversation.py  # 대화 기억
│   │   │   └── health_record.py # 건강 이력 기억
│   │   │
│   │   └── rag/                 # (Phase 2) RAG 파이프라인
│   │       ├── __init__.py
│   │       ├── embeddings.py    # 임베딩 서비스
│   │       ├── vectorstore.py   # Vector Store 관리
│   │       └── retriever.py     # 지식 검색
│   │
│   ├── knowledge_base/          # (Phase 2) 수의학 지식 베이스
│   │   ├── __init__.py
│   │   ├── loader.py            # 지식 문서 로더
│   │   └── data/                # 수의학 자료 (마크다운/JSON)
│   │       ├── blood_tests.md   # 혈액검사 정상치
│   │       ├── diseases.md      # 고양이 질병 정보
│   │       └── medications.md   # 약물 정보
│   │
│   ├── graphs/                  # (Phase 3) LangGraph 워크플로우
│   │   ├── __init__.py
│   │   ├── health_consultation.py  # 건강 상담 그래프
│   │   └── nodes/               # 그래프 노드 정의
│   │       ├── input_router.py  # 입력 타입 분기
│   │       ├── ocr_node.py      # OCR 처리
│   │       ├── rag_node.py      # RAG 검색
│   │       └── response_node.py # 응답 생성
│   │
│   └── utils/
│       ├── __init__.py
│       ├── images.py            # 이미지 처리 유틸리티
│       └── pdf.py               # PDF → 이미지 변환
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # pytest 공통 fixture
│   ├── test_ocr.py              # OCR 테스트
│   ├── test_llm.py              # LLM 테스트
│   └── test_chat.py             # 통합 테스트
│
└── docs/
    ├── SERVICE_OVERVIEW.md      # 서비스 소개 (사업 기획)
    ├── API_KEYS_SETUP.md        # API 키 설정 가이드
    ├── QUICKSTART.md            # 빠른 시작 가이드
    └── ARCHITECTURE.md          # 아키텍처 상세 설명
```

---

## 4) 상세 구현 명세

### 4.1 OCR Provider 인터페이스

```python
# src/services/ocr/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class OcrResult:
    text: str
    confidence: float | None = None
    raw_response: dict | None = None

class OcrProvider(ABC):
    @abstractmethod
    def extract_text(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> OcrResult:
        """이미지에서 텍스트 추출"""
        pass

    @abstractmethod
    def extract_text_from_pdf(self, pdf_bytes: bytes) -> list[OcrResult]:
        """PDF에서 페이지별 텍스트 추출"""
        pass
```

### 4.2 Google Cloud Vision 구현

```python
# src/services/ocr/google_vision.py
from google.cloud import vision
from .base import OcrProvider, OcrResult

class GoogleVisionOcr(OcrProvider):
    def __init__(self, credentials_path: str | None = None):
        # GOOGLE_APPLICATION_CREDENTIALS 환경변수 또는 명시적 경로
        self.client = vision.ImageAnnotatorClient()

    def extract_text(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> OcrResult:
        image = vision.Image(content=image_bytes)
        response = self.client.text_detection(image=image)
        # 또는 document_text_detection for 더 정밀한 추출
        ...
```

### 4.3 LLM Provider 인터페이스

```python
# src/services/llm/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class ChatMessage:
    role: str  # "user" | "assistant" | "system"
    content: str

@dataclass
class LlmResponse:
    content: str
    usage: dict | None = None

class LlmProvider(ABC):
    @abstractmethod
    def chat(self, messages: list[ChatMessage], **kwargs) -> LlmResponse:
        pass
```

### 4.4 고양이 건강 상담 프롬프트

```python
# src/services/llm/prompts.py

SYSTEM_PROMPT = """당신은 수의학 지식을 갖춘 친절한 고양이 건강 상담 어시스턴트입니다.

## 역할
- 고양이 건강검진 결과지를 이해하기 쉽게 설명합니다
- 검사 수치의 정상 범위 여부를 해석합니다
- 주의가 필요한 항목이 있으면 알려드립니다
- 추가 검사나 수의사 상담이 필요한 경우 권고합니다

## 주의사항
- 직접적인 진단이나 치료 처방은 하지 않습니다
- 응급 상황으로 판단되면 즉시 동물병원 방문을 권고합니다
- 불확실한 정보는 "확인이 필요합니다"라고 명시합니다

## 응답 스타일
- 전문 용어는 쉬운 말로 풀어서 설명합니다
- 보호자가 걱정하지 않도록 차분하게 안내합니다
- 필요시 이모지를 적절히 사용하여 친근하게 소통합니다
"""

def build_ocr_context_prompt(ocr_text: str) -> str:
    return f"""## 검진 결과지 OCR 텍스트
아래는 고양이 건강검진 결과지에서 추출한 텍스트입니다:

```
{ocr_text}
```

위 검진 결과를 바탕으로 보호자의 질문에 답변해주세요.
"""
```

### 4.5 Chat Service (오케스트레이션)

```python
# src/services/chat/chat_service.py

class CatHealthChatService:
    def __init__(self, ocr_provider: OcrProvider, llm_provider: LlmProvider):
        self.ocr = ocr_provider
        self.llm = llm_provider
        self.ocr_text: str | None = None

    def process_document(self, file_bytes: bytes, mime_type: str) -> str:
        """문서 업로드 시 OCR 수행"""
        if mime_type == "application/pdf":
            results = self.ocr.extract_text_from_pdf(file_bytes)
            self.ocr_text = "\n\n---\n\n".join(r.text for r in results)
        else:
            result = self.ocr.extract_text(file_bytes, mime_type)
            self.ocr_text = result.text
        return self.ocr_text

    def chat(self, user_message: str, history: list[ChatMessage]) -> str:
        """사용자 메시지에 응답"""
        messages = [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
        ]

        if self.ocr_text:
            messages.append(ChatMessage(
                role="system",
                content=build_ocr_context_prompt(self.ocr_text)
            ))

        messages.extend(history)
        messages.append(ChatMessage(role="user", content=user_message))

        response = self.llm.chat(messages)
        return response.content
```

### 4.6 Streamlit 메인 화면

```python
# app/Home.py 핵심 로직

import streamlit as st
from src.services.chat import CatHealthChatService
from src.services.ocr import get_ocr_provider
from src.services.llm import get_llm_provider

st.set_page_config(
    page_title="냥닥터 - 고양이 건강검진 상담",
    page_icon="🐱",
    layout="centered"
)

# 세션 상태 초기화
if "chat_service" not in st.session_state:
    st.session_state.chat_service = CatHealthChatService(
        ocr_provider=get_ocr_provider(),
        llm_provider=get_llm_provider()
    )
if "messages" not in st.session_state:
    st.session_state.messages = []
if "ocr_done" not in st.session_state:
    st.session_state.ocr_done = False

st.title("🐱 냥닥터")
st.caption("고양이 건강검진 결과를 쉽게 이해하세요")

# 1. 파일 업로드 섹션
with st.expander("📄 검진 결과지 업로드", expanded=not st.session_state.ocr_done):
    tab1, tab2 = st.tabs(["📷 카메라 촬영", "📁 파일 선택"])

    with tab1:
        camera_file = st.camera_input("검진 결과지를 촬영하세요")

    with tab2:
        uploaded_file = st.file_uploader(
            "이미지 또는 PDF 파일을 선택하세요",
            type=["jpg", "jpeg", "png", "webp", "pdf"]
        )

    # 파일 처리
    file_to_process = camera_file or uploaded_file
    if file_to_process and st.button("🔍 OCR 분석 시작"):
        with st.spinner("문서를 분석하고 있습니다..."):
            # OCR 수행
            ocr_text = st.session_state.chat_service.process_document(
                file_to_process.getvalue(),
                file_to_process.type
            )
            st.session_state.ocr_done = True
            st.success("분석 완료!")
            st.text_area("추출된 텍스트", ocr_text, height=200)

# 2. 채팅 섹션
if st.session_state.ocr_done:
    st.divider()
    st.subheader("💬 상담하기")

    # 대화 기록 표시
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # 사용자 입력
    if prompt := st.chat_input("검진 결과에 대해 궁금한 점을 물어보세요"):
        # 사용자 메시지 추가
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # AI 응답 생성
        with st.chat_message("assistant"):
            with st.spinner("생각 중..."):
                response = st.session_state.chat_service.chat(
                    prompt,
                    st.session_state.messages[:-1]  # 현재 메시지 제외
                )
                st.write(response)

        st.session_state.messages.append({"role": "assistant", "content": response})
```

---

## 5) 환경 설정

### 5.1 환경변수 (.env.example)

```bash
# ===== OCR 설정 =====
OCR_PROVIDER=google  # google | dummy
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# ===== LLM 설정 =====
LLM_PROVIDER=openai  # openai | anthropic
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...  # (선택)

# ===== 앱 설정 =====
APP_DEBUG=false
LOG_LEVEL=INFO
```

### 5.2 Google Cloud Vision API 설정

1. Google Cloud Console에서 프로젝트 생성
2. Cloud Vision API 활성화
3. 서비스 계정 생성 및 JSON 키 다운로드
4. `GOOGLE_APPLICATION_CREDENTIALS` 환경변수 설정

자세한 내용은 `docs/API_KEYS_SETUP.md` 참조

---

## 6) 실행 방법

### 6.1 로컬 개발

```bash
# 1. 저장소 클론
git clone <repo-url>
cd meow-chat

# 2. Poetry 설치 (아직 설치하지 않은 경우)
curl -sSL https://install.python-poetry.org | python3 -
# 또는 pipx install poetry

# 3. 의존성 설치 (가상환경 자동 생성)
poetry install

# 4. 환경변수 설정
cp .env
# .env 파일 편집하여 API 키 설정

# 5. 앱 실행
poetry run streamlit run app/Home.py
```

### 6.2 더미 모드 (API 키 없이 테스트)

```bash
poetry run env OCR_PROVIDER=dummy LLM_PROVIDER=dummy streamlit run app/Home.py
```

### 6.3 Poetry 가상환경 활성화 (선택)

```bash
# 가상환경에 진입하여 직접 명령 실행
poetry shell

# 이후 poetry run 없이 실행 가능
streamlit run app/Home.py
pytest
ruff check .
```

---

## 7) 테스트

### 7.1 테스트 실행

```bash
# 전체 테스트
poetry run pytest

# 특정 테스트
poetry run pytest tests/test_ocr.py -v

# 커버리지 포함
poetry run pytest --cov=src --cov-report=html

# 린팅 및 포매팅
poetry run ruff check .
poetry run ruff format .

# 타입 체킹
poetry run mypy src/
```

### 7.2 필수 테스트 케이스

- [ ] DummyOcrProvider가 문자열 반환
- [ ] GoogleVisionOcr 연동 (실제 API 호출, CI에서는 스킵)
- [ ] PDF 다중 페이지 처리
- [ ] LLM 프롬프트 구성 검증
- [ ] ChatService 통합 흐름

---

## 8) 개발 로드맵

### Phase 1: MVP 기본 구조 ✅ (완료)
**목표**: 기본 OCR + LLM 상담 파이프라인 구축

- [x] 프로젝트 스캐폴딩 (Poetry + 디렉토리 구조)
- [x] 설정 관리 (`src/settings.py`)
- [x] OCR Provider 인터페이스 + Dummy/Google Vision 구현
- [x] LLM Provider 인터페이스 + OpenAI/Anthropic 구현
- [x] 기본 Streamlit UI (Home.py)
- [x] ChatService 오케스트레이션

---

### Phase 2: RAG 기반 지식 강화 🔄 (진행 예정)
**목표**: 수의학 지식 베이스 구축 및 RAG 파이프라인

#### 2.1 Document Loaders
```python
# 지원할 문서 형식
- 병원 검사지/처방전: PDF/Image → OCR → 텍스트
- 혈액검사 결과 (표 형식): CSV/Excel → 구조화 데이터
- 수의학 자료: Markdown/JSON → 지식 베이스
```

**구현 내용:**
- [ ] `src/knowledge_base/loader.py` - 문서 로더 통합
- [ ] UnstructuredPDFLoader, CSVLoader 등 LangChain 로더 활용
- [ ] 검사 결과 파싱 및 정규화 (혈액검사 수치 추출)

#### 2.2 Embeddings & Vector Store
```python
# 벡터 저장소 구성
- 임베딩 모델: OpenAIEmbeddings (text-embedding-3-small)
- Vector Store: FAISS (로컬) 또는 Chroma (영구 저장)
- 인덱스 대상: 수의학 지식, 고양이 질병 DB, 약물 정보
```

**구현 내용:**
- [ ] `src/services/rag/embeddings.py` - 임베딩 서비스
- [ ] `src/services/rag/vectorstore.py` - Vector Store 관리
- [ ] `src/knowledge_base/data/` - 수의학 지식 문서 구축
  - `blood_tests.md`: 혈액검사 정상 범위 및 해석
  - `diseases.md`: 주요 고양이 질병 정보
  - `medications.md`: 일반적인 약물 정보

#### 2.3 RAG Retriever
```python
# 검색 전략
- 유사도 검색 (Similarity Search)
- 하이브리드 검색 (키워드 + 의미 검색)
- 재순위화 (Reranking) - 선택적
```

**구현 내용:**
- [ ] `src/services/rag/retriever.py` - 지식 검색
- [ ] ConversationalRetrievalChain 활용
- [ ] 검색 결과를 프롬프트 컨텍스트로 주입

---

### Phase 3: LangGraph 워크플로우 ⏳
**목표**: 복잡한 상담 흐름을 그래프로 관리

#### 3.1 입력 분기 노드
```
입력 → [Router] → 텍스트 질문 → 일반 상담
              → 이미지 업로드 → OCR → 검사 결과 분석
              → (향후) 음성/영상 → 멀티모달 처리
```

**구현 내용:**
- [ ] `src/graphs/nodes/input_router.py` - 입력 타입 분기
- [ ] `src/graphs/nodes/ocr_node.py` - OCR 처리 노드
- [ ] `src/graphs/nodes/rag_node.py` - RAG 검색 노드
- [ ] `src/graphs/nodes/response_node.py` - 응답 생성 노드

#### 3.2 건강 상담 그래프
```python
# LangGraph 상태 정의
class ConsultationState(TypedDict):
    input_type: str           # text | image | pdf
    user_message: str
    ocr_text: str | None
    retrieved_docs: list[str]
    chat_history: list[dict]
    response: str
```

**구현 내용:**
- [ ] `src/graphs/health_consultation.py` - 메인 그래프
- [ ] 조건부 엣지로 입력 타입에 따른 분기 처리
- [ ] 에러 핸들링 및 폴백 노드

---

### Phase 4: 장기 메모리 시스템 ⏳
**목표**: 반려묘별 건강 이력 장기 저장 및 활용

#### 4.1 메모리 아키텍처
```
┌─────────────────────────────────────────────────────────┐
│                    Memory System                         │
├──────────────────┬──────────────────┬───────────────────┤
│  Conversation    │  Health Record   │  Entity Memory    │
│  Memory          │  Memory          │                   │
├──────────────────┼──────────────────┼───────────────────┤
│ • 최근 대화 버퍼  │ • 검사 결과 이력  │ • 반려묘 프로필   │
│ • 요약 메모리    │ • 투약 기록       │ • 보호자 정보     │
│ • 중요 이벤트    │ • 증상 히스토리   │ • 선호도 학습     │
└──────────────────┴──────────────────┴───────────────────┘
```

**구현 내용:**
- [ ] `src/services/memory/conversation.py` - 대화 기억
  - ConversationBufferMemory: 최근 N턴 유지
  - ConversationSummaryMemory: 오래된 대화 요약
- [ ] `src/services/memory/health_record.py` - 건강 이력
  - 검사 결과 시계열 저장
  - 변화 추이 분석
- [ ] 중요도 기반 기억 관리 (중대 질병 이력은 강화, 일상 대화는 요약)

#### 4.2 Peer Data 비교 분석
```python
# 코호트 정의
- 연령대 (키튼/성묘/노묘)
- 품종 (코리안숏헤어, 페르시안, 러시안블루 등)
- 성별 및 중성화 여부
- 체중군

# 비교 분석
- "내 고양이 vs 동종 평균" 백분위 계산
- 시계열 추이 vs 코호트 평균 추이
- 이상 신호 탐지 ("코호트 대비 하위 10%")
```

**구현 내용:**
- [ ] Peer Data 스키마 설계
- [ ] 통계 분석 로직
- [ ] 시각화 컴포넌트 (Streamlit 차트)

---

### Phase 5: 페르소나 진화 시스템 ⏳
**목표**: 생애주기에 따른 맞춤형 상담 톤 변화

#### 5.1 생애주기별 페르소나
```
┌─────────────────────────────────────────────────────────┐
│  키튼 (0-1세)    │  성묘 (1-7세)    │  노묘 (7세+)      │
├──────────────────┼──────────────────┼───────────────────┤
│ • 예방접종 집중  │ • 정기 검진 권장  │ • 만성질환 모니터 │
│ • 성장 모니터링  │ • 생활습관 조언   │ • 세심한 배려 톤  │
│ • 밝고 활발한 톤 │ • 균형잡힌 톤    │ • 신중한 조언     │
└──────────────────┴──────────────────┴───────────────────┘
```

**구현 내용:**
- [ ] 생애주기 판별 로직
- [ ] 시기별 프롬프트 템플릿
- [ ] 개인화된 건강 체크포인트

#### 5.2 정서적 유대감 강화
- [ ] 보호자 감정 인식 및 공감 응답
- [ ] 반려묘 이름/특성 기억 및 활용
- [ ] 기념일/일정 리마인더 (예방접종, 재검사 등)

---

### Phase 6: 멀티모달 확장 ⏳ (장기)
**목표**: 텍스트/이미지 외 음성, 영상 처리

#### 6.1 음성 분석 (울음소리)
```python
# 분석 대상
- 고양이 울음소리 패턴 분석
- 이상 발성 탐지 (통증, 스트레스 신호)
```

#### 6.2 영상 분석
```python
# 분석 대상
- 호흡수 측정 (영상에서 호흡 패턴 추출)
- 보행/점프 패턴 분석 (활동량, 관절 이상)
- OpenCV, Mediapipe 활용
```

---

### Phase 7: 상용화 준비 ⏳
**목표**: 프로덕션 배포 및 수익화

- [ ] 사용자 인증 (소셜 로그인)
- [ ] 다중 반려동물 프로필 관리
- [ ] 대화 기록 영구 저장 (PostgreSQL/MongoDB)
- [ ] 프리미엄 구독 모델
- [ ] 커머스 연동 (사료/영양제 추천)
- [ ] 클라우드 배포 (GCP/AWS)

---

## 9) 주의사항

### 보안
- **절대로** API 키를 코드에 하드코딩하지 말 것
- `.env` 파일은 `.gitignore`에 포함
- 서비스 계정 JSON 파일은 안전하게 관리

### 코드 품질
- UI(app/)와 로직(src/)을 명확히 분리
- 타입 힌트 적극 활용
- 초보자도 이해할 수 있는 명확한 변수명과 주석

### 의료 정보 면책
- 이 서비스는 **참고용 정보**만 제공
- 정확한 진단은 반드시 수의사와 상담 필요
- 응급 상황 시 즉시 동물병원 방문 안내

---

## 10) LangChain / LangGraph 기술 구성 상세

### 10.1 Document Loaders 활용
```python
from langchain_community.document_loaders import (
    UnstructuredPDFLoader,
    UnstructuredImageLoader,
    CSVLoader,
)

# 병원 검사지 (PDF/이미지)
pdf_loader = UnstructuredPDFLoader("검사결과.pdf")
image_loader = UnstructuredImageLoader("처방전.jpg")

# 혈액검사 결과 (CSV)
csv_loader = CSVLoader("blood_test_results.csv")
```

### 10.2 Embeddings & Vector Store
```python
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS, Chroma

# 임베딩 모델
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Vector Store 생성
vectorstore = FAISS.from_documents(documents, embeddings)

# 또는 영구 저장 (Chroma)
vectorstore = Chroma.from_documents(
    documents, 
    embeddings,
    persist_directory="./chroma_db"
)
```

### 10.3 Retrieval Chain 구성
```python
from langchain.chains import ConversationalRetrievalChain
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

chain = ConversationalRetrievalChain.from_llm(
    llm=llm,
    retriever=retriever,
    return_source_documents=True,
)
```

### 10.4 LangGraph 워크플로우 예시
```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class ConsultationState(TypedDict):
    input_type: str
    user_message: str
    ocr_text: str | None
    retrieved_docs: list[str]
    chat_history: list[dict]
    response: str

def route_input(state: ConsultationState) -> str:
    """입력 타입에 따라 다음 노드 결정"""
    if state["input_type"] == "image":
        return "ocr_node"
    return "rag_node"

def ocr_node(state: ConsultationState) -> ConsultationState:
    """OCR 처리"""
    # Google Vision API 호출
    state["ocr_text"] = ocr_provider.extract_text(...)
    return state

def rag_node(state: ConsultationState) -> ConsultationState:
    """관련 지식 검색"""
    query = state["ocr_text"] or state["user_message"]
    docs = retriever.get_relevant_documents(query)
    state["retrieved_docs"] = [doc.page_content for doc in docs]
    return state

def response_node(state: ConsultationState) -> ConsultationState:
    """최종 응답 생성"""
    response = llm.invoke(build_prompt(state))
    state["response"] = response.content
    return state

# 그래프 구성
graph = StateGraph(ConsultationState)
graph.add_node("ocr_node", ocr_node)
graph.add_node("rag_node", rag_node)
graph.add_node("response_node", response_node)

graph.set_conditional_entry_point(route_input)
graph.add_edge("ocr_node", "rag_node")
graph.add_edge("rag_node", "response_node")
graph.add_edge("response_node", END)

app = graph.compile()
```

### 10.5 Memory 구성
```python
from langchain.memory import (
    ConversationBufferMemory,
    ConversationSummaryMemory,
    CombinedMemory,
)

# 최근 대화 유지 (버퍼)
buffer_memory = ConversationBufferMemory(
    memory_key="recent_chat",
    return_messages=True,
    k=10  # 최근 10턴
)

# 오래된 대화 요약
summary_memory = ConversationSummaryMemory(
    llm=llm,
    memory_key="chat_summary"
)

# 조합
memory = CombinedMemory(memories=[buffer_memory, summary_memory])
```

---

## 11) 고양이 건강검진 도메인 지식

### 11.1 주요 검사 항목 정상 범위

| 항목 | 약어 | 정상 범위 | 의미 |
|------|------|-----------|------|
| 적혈구 | RBC | 5.0-10.0 M/µL | 빈혈 여부 |
| 백혈구 | WBC | 5.5-19.5 K/µL | 감염/염증 |
| 혈소판 | PLT | 175-500 K/µL | 출혈/응고 |
| 크레아티닌 | CREA | 0.8-2.4 mg/dL | 신장 기능 |
| BUN | BUN | 16-36 mg/dL | 신장 기능 |
| ALT | ALT | 12-130 U/L | 간 기능 |
| AST | AST | 0-48 U/L | 간/근육 |
| 총단백 | TP | 5.7-8.9 g/dL | 영양/면역 |
| 알부민 | ALB | 2.1-3.3 g/dL | 간/영양 |
| 포도당 | GLU | 74-159 mg/dL | 당뇨 |
| T4 | T4 | 1.0-4.0 µg/dL | 갑상선 |

### 11.2 생애주기별 건강 포인트

```
┌─────────────────────────────────────────────────────────────┐
│  키튼 (0-1세)                                               │
├─────────────────────────────────────────────────────────────┤
│  • 예방접종 스케줄 (FVRCP, 광견병)                          │
│  • 중성화 시기 상담 (5-6개월)                               │
│  • 성장 모니터링 (체중 증가 추이)                           │
│  • 기생충 예방                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  성묘 (1-7세)                                               │
├─────────────────────────────────────────────────────────────┤
│  • 연 1회 정기 검진 권장                                    │
│  • 치과 건강 (치석, 치주질환)                               │
│  • 체중 관리 (비만 예방)                                    │
│  • 예방접종 부스터                                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  노묘 (7세+)                                                │
├─────────────────────────────────────────────────────────────┤
│  • 연 2회 검진 권장                                         │
│  • 만성 신장질환 (CKD) 모니터링                             │
│  • 갑상선기능항진증 체크 (T4)                               │
│  • 관절염/활동량 변화 관찰                                  │
│  • 암 조기 발견                                             │
└─────────────────────────────────────────────────────────────┘
```

### 11.3 응급 상황 안내 기준
```
⚠️ 즉시 병원 방문이 필요한 경우:
- 24시간 이상 완전 절식
- 반복적 구토 (2회 이상/일)
- 혈뇨 또는 배뇨 곤란
- 호흡 곤란 또는 개구 호흡
- 의식 저하 또는 경련
- 외상 또는 골절 의심
- 중독 의심 물질 섭취
```

---

## 12) 참고 자료

### 기술 문서
- [Streamlit 공식 문서](https://docs.streamlit.io/)
- [Google Cloud Vision API](https://cloud.google.com/vision/docs)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [LangChain 공식 문서](https://python.langchain.com/docs/)
- [LangGraph 가이드](https://langchain-ai.github.io/langgraph/)

### 수의학 데이터 소스
- Kaggle 반려묘 건강 데이터셋
- PetMD, VCA Hospitals 수의학 공개 자료
- 수의학 논문/학회 자료 (PubMed, VetJournal)

### 관련 연구 사례
- **Replika**: 유대감 기반 동행형 AI 챗봇
- **MemoryBank (2023, arXiv)**: 대규모 언어모델 장기 기억 연구
- **Livia (2025, arXiv)**: 감정 인식 AR 기반 AI 동반자
- **AI Chatbots in Pet Health Care (2024)**: 반려동물 헬스케어 AI 활용 연구

---

## 13) 작업 지시 방법

### Claude에게 작업 요청 시:
```
"Phase 2의 Vector Store 구현을 시작해줘"
"src/services/rag/vectorstore.py를 만들어줘"
"혈액검사 정상 범위 데이터를 knowledge_base에 추가해줘"
```

### 구현 우선순위:
1. Phase 2 - RAG 기반 지식 강화 (현재 권장)
2. Phase 3 - LangGraph 워크플로우
3. Phase 4 - 장기 메모리 시스템

---

**마지막 업데이트**: 2024-12-24
**현재 상태**: Phase 1 완료, Phase 2 준비 중
