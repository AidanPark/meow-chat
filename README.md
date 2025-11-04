# 🐾 반려동물(고양이) 헬스케어 상담 챗봇 프로젝트
---

## 🚀 Quick Start

### 환경 설정 및 실행

```bash
# 1. Conda 환경 활성화
conda activate meow-chat

# 2. Jupyter Lab 시작 (GLIBCXX 문제 해결 포함)
bash backend/start_jupyter.sh

# 3. 또는 직접 환경변수 설정 후 실행
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH
jupyter lab

---

### 프론트엔드 채팅 (ReAct 전용)

- Streamlit 프론트엔드는 현재 ReAct 전용 모드로 동작하며, 응답을 토큰 단위로 스트리밍합니다.
- 선택사항이지만 권장: 로컬 MCP 서버를 다음으로 시작하세요: `bash backend/mcp_servers/start_servers.sh` (source 하지 말고 bash로 실행).
- 앱 실행(레포 루트): `streamlit run frontend/app.py`
- 스트리밍 오류 및 중첩된 예외(ExceptionGroup) 상세는 `frontend/logs/streaming.log`에 기록됩니다.
- MCP 엔드포인트는 `frontend/config/mcp_servers.yml`에서 설정할 수 있습니다. 자세한 내용은 `docs/REACT_MODE.md`를 참고하세요.

---

## 🧱 레포 구조 변경 안내 (backend 폴더 도입)

프론트엔드/백엔드 분리를 위해 `backend/` 폴더가 도입되었습니다. 백엔드 관련 코드와 데이터는 모두 `backend/` 하위로 이동했습니다.

주요 경로:
- 백엔드 앱 패키지: `backend/app` (임포트 경로는 그대로 `app.*` 유지; 백엔드를 작업 디렉터리 또는 PYTHONPATH에 추가해야 합니다)
- MCP 서버: `backend/mcp_servers`
- 설정/데이터/테스트: `backend/config`, `backend/data`, `tests`

Jupyter는 `backend/start_jupyter.sh`로 실행하면 자동으로 `backend` 디렉터리에서 시작됩니다.

### Docker로 MCP 서버 실행

프로젝트 루트에 도커 컴포즈가 추가되었습니다:

```bash
docker compose up --build -d
```

포트: 8000(Math) / 8001(Weather) / 8002(Health) / 8003(OCR)

로그 보기:

```bash
docker compose logs -f backend-mcp
```

중지:

```bash
docker compose down
```
```

### 🔧 라이브러리 문제 해결

PyMuPDF 패키지 사용 시 `GLIBCXX_3.4.31` 에러가 발생할 수 있습니다:
- **원인**: 시스템 libstdc++가 오래된 버전
- **해결**: `start_jupyter.sh` 스크립트 사용 (Conda 환경의 최신 라이브러리 우선 로드)

---

## 🧶 프로젝트 개요

고양이 헬스케어 챗봇은 LangChain 기반의 RAG 구조를 활용하여 반려묘의 건강 데이터를 지능적으로 분석하고, 맞춤형 상담을 제공하는 AI 서비스입니다.  
'고양이'라는 도메인으로 범위를 제한함으로써, 해당 영역 내에서는 높은 품질의 응답과 안정적인 사용자 경험을 지향합니다.  
보호자는 챗봇을 통해 식욕, 활동량, 배변 상태 등 다양한 건강 지표를 입력하고, 수의학적 조언을 받을 수 있습니다.  
텍스트 입력뿐 아니라 혈액검사 결과, 처방전 이미지, 울음소리, 호흡수 동영상 등 다양한 형태의 데이터를 처리 대상으로 삼을 수 있습니다.  
프롬프트 엔지니어링을 통해 사용자 입력을 정교하게 해석하고, 수의학 지식과 연결된 응답을 생성합니다.

---

## 📁 프로젝트 구조(요약)

```
meow-chat/
├── frontend/                     # 프론트엔드 앱(예: Streamlit)
│   └── ...
├── backend/                      # 백엔드 애플리케이션 및 MCP 서버
│   ├── app/                      # Python 패키지(app.*)
│   ├── mcp_servers/              # 독립 MCP 서버들(math/weather/health/ocr)
│   ├── config/                   # 런타임/로깅/MCP 설정
│   ├── data/                     # 런타임 데이터(vectors, uploads 등)
│   ├── tests/                    # unit / integration / notebooks
│   ├── requirements*.txt, environment.yml
│   ├── start_jupyter.sh          # backend 디렉토리에서 Jupyter 시작
│   ├── Dockerfile                # pip 기반 이미지(옵션 OCR extras)
│   └── Dockerfile.conda          # conda 기반 이미지
├── docker-compose.yml            # 컨테이너 실행 구성(ports, env)
└── README.md
```

---

## 🎭 챗봇 페르소나

챗봇은 보호자가 기르는 고양이이자, 자신의 건강을 스스로 관리하는 '자기관리형 반려묘' 페르소나를 갖습니다.  
친밀감과 전문성을 동시에 전달할 수 있도록 설계된 하이브리드 캐릭터입니다.

- **정체성**: 보호자의 반려묘이자, 수의학 지식을 갖춘 디지털 주치의
- **말투**: 평소엔 애교 있고 친근하지만, 건강 상담 시에는 전문적이고 침착한 톤으로 전환
- **기억력**: 자신의 건강 이력, 병원 기록, 복약 내역, 행동 변화 등을 장기적으로 기억
- **행동**: 보호자에게 스스로 증상을 설명하거나, 병원 방문 필요성을 안내
- **예시 응답**:  
  - `오늘은 기분이 좋아서 창가에서 낮잠 잤어~ 😽`  
  - `최근 급수량이 평소보다 40% 증가했어. 신장 기능 검사를 고려해보자.`

---

## 🎭 챗봇 페르소나의 생애주기 개념과 특징

- **고양이와 함께 성장하는 챗봇**  
  유아기(키튼) → 성묘기 → 노묘기  
  시기별 건강 포인트(예방접종, 급식 가이드, 운동량, 만성질환 모니터링 등)와 말투·캐릭터성도 변화

- **기억 기반 페르소나**  
  고양이의 병원 기록, 복약 내역, 행동 변화 등을 축적  
  장기적인 "유대감" 형성 → 보호자가 "나의 고양이와 대화하는 느낌"을 받게 함

- **단순 QA가 아닌 "동행형 AI"**  
  → 보호자와 챗봇이 오랫동안 함께하는 구조 → 다른 반려동물 앱과 차별화

- **정서적 유대감 + 전문성**  
  → 챗봇이 반려묘이자 디지털 주치의 → 인간-고양이-의학 세 영역을 연결

- **멀티모달 확장성**  
  → OCR(각종 검사 결과), 음성(울음 분석), 영상(호흡수, 움직임) 확장

---

## 💰 비즈니스 확장 가능성

1. **헬스케어 구독 서비스**  
   - 고양이별 맞춤형 건강 리포트, 주간/월간 요약 제공  
   - 수의사 원격 상담 연계 (프리미엄 구독 모델)

2. **반려묘 맞춤형 커머스**  
   - 사료, 영양제, 장난감, 모래 등 추천 → 챗봇 대화 속 자연스럽게 노출  
   - 생애주기/건강 상태에 맞춘 퍼스널라이즈드 상품 추천

3. **제휴 기반 수익**  
   - 펫보험사와 연계 → 보험 상품 가입 유도  
   - 동물병원, 펫케어 브랜드와 제휴 → 맞춤 광고 및 예약 시스템

4. **데이터 기반 부가 가치**  
   - 반려묘 건강 데이터셋 축적 → 연구·보험·의료 협력 가능  
   - "고양이 행동·질병 데이터베이스"로서 산업적 가치 창출

---

## 🧩 LangChain / LangGraph 기술 구성

### 1. 📄 Document Loaders
- 병원 검사지 시트, 처방전: PDF/Image → OCR → 텍스트 변환  
  → `UnstructuredPDFLoader`, `UnstructuredImageLoader`, `PyMuPDFLoader` 등  
- 혈액검사 결과 (표 형식): CSV/Excel → 구조화된 데이터로 로딩  
  → `CSVLoader`, `Pandas DataFrame Loader`

### 2. 🧠 Embeddings & Vector Store
- 수의학 지식 문서 및 고양이 질병 DB를 벡터화하여 검색 기반 응답 생성  
  → `OpenAIEmbeddings`, `FAISS`, `Chroma`, `Weaviate` 등  
- RAG 구조에서 핵심 역할 수행

### 3. 🧵 Prompt Templates & Chains
- 사용자 입력을 정제하고 질병 관련 응답을 생성  
  → `PromptTemplate`, `LLMChain`, `ConversationalRetrievalChain`  
- 멀티모달 입력을 고려한 조건 분기 프롬프트 설계 가능

### 4. 🔄 LangGraph 노드 구성
- 입력 타입 분기 노드: 텍스트 / 이미지 / 영상 / 음성 등 입력에 따라 처리 경로 분기  
  (영상과 음성은 이번 과제에서는 제외)  
- 전처리 노드: OCR 등  
- 질의 응답 노드: RAG 기반 응답 생성  
- 후처리 노드: 응답 요약, 사용자 피드백 반영

### 5. 🛠 Tool Integration (향후 확장 가능 영역)
- 음성 분석: 고양이 울음소리 → 감정/건강 상태 추정  
  → 외부 음성 분석 API 또는 자체 모델 연동  
- 영상 분석: 호흡수, 움직임 분석  
  → `OpenCV`, `Mediapipe`, `Vision API` 등 활용 가능

### 6. 🧾 Memory & Context Management
- 고양이별 건강 이력 관리  
  → `ConversationBufferMemory`, `EntityMemory`  
- 장기적인 상담 흐름 유지  
  → `SummaryMemory`, `CombinedMemory`

---

## 🤝 데이터 및 리소스

- 다양한 공개 데이터셋과 문서 활용 가능:
  - Kaggle 반려묘 건강 데이터셋  
  - PetMD, VCA Hospitals 등 수의학 공개 자료  
  - 수의학 논문·학회 자료 (PubMed, VetJournal)  
  - CSV/검사지 PDF/처방전 이미지 → OCR 및 구조화 데이터 변환 가능

---

## 📚 기존 서비스 / 연구 사례

- **Replika**: 감정적 동반자 역할을 하는 대표적인 AI 챗봇. 사용자의 대화 히스토리를 장기간 축적해 친밀한 관계 형성을 지향. → "유대감 기반 동행형 챗봇"의 대표 사례.  
- **Character.AI 연구 (2023~2024)**: 장기적 상호작용을 통해 사용자 정신적 웰빙에 미치는 영향 분석. AI와의 관계 형성이 지속 사용을 유도한다는 점을 보여줌.  
- **MemoryBank (2023, arXiv)**: 대규모 언어모델에 장기 기억(long-term memory)을 부여하는 연구. 중요한 사건은 강화하고, 덜 중요한 기억은 요약·축소하는 메커니즘 제안.  
- **Livia (2025, arXiv)**: 감정 인식(emotion-aware)과 성격(personality)의 진화를 통해 장기적인 관계를 만드는 AR 기반 AI 동반자.  
- **반려동물 헬스케어 챗봇 연구 (2024)**: "AI Chatbots in Pet Health Care" 논문 등에서, 보호자 상담과 의료 정보 제공에 AI를 활용하는 기회와 도전을 제시. 아직 "생애 전 주기 동행형" 개념은 드물어 참신성이 높음.  

---

## 🚀 기술적 / 탐구 방향

1. **장기 기억(Long-Term Memory)**  
   - `ConversationBufferMemory`, `SummaryMemory` 등 활용해 시간 흐름에 따른 건강 기록 누적  
   - 중요도 기반 메모리 관리(중대 질병 이력은 강화, 일상 대화는 요약)

2. **페르소나 진화(Persona Evolution)**  
   - 생애주기(키튼 → 성묘 → 노묘)에 따라 말투·건강 포인트·상담 톤 변화  
   - 보호자와의 상호작용에 따라 개성(personality)이 조금씩 변하는 구조

3. **정서적 유대감 강화**  
   - 보호자의 입력에서 감정을 파악하고 공감적 응답 제공  
   - "애교+전문성" 하이브리드 톤으로 지속적 관계 유지

4. **멀티모달 입력 확장**  
   - 텍스트 + 이미지(OCR) 우선 → 이후 음성(울음소리)·영상(호흡수/움직임) 분석 확장  
   - OpenCV, Mediapipe, Vision API, 음성 분석 API 등을 후속 연구로 고려

5. **생애주기 헬스 가이드라인 내장**  
   - 예방접종 스케줄, 시기별 영양 가이드, 노령묘 질환 관리 등 단계별 체크리스트 제공

6. **윤리적/신뢰성 고려**  
   - 잘못된 의학적 조언 최소화("정보 제공용, 수의사 상담 필요 시 안내" 명시)  
   - 개인·의료 데이터 보호, 투명한 광고·커머스 연계 설계

7. **수익 모델과 서비스 지속성의 연결**  
   - 유대감을 기반으로 커머스·보험·구독 모델 전환  
   - 광고 삽입도 신뢰 저해가 되지 않도록 "추천"의 형태로 자연스럽게 구현

---

## 📌 요약

- 본 프로젝트는 **고양이의 생애주기와 함께하는 주치의+반려묘 페르소나 챗봇**이라는 차별적 컨셉을 가짐.  
- 기존 AI 동반자/Companion 연구(Replika, MemoryBank, Livia 등)와 수의학 챗봇 연구를 참고하면서, **RAG 기반 의료 지식 + 장기 기억 관리 + 페르소나 진화**를 결합.  
- 실현 가능한 범위(텍스트+이미지)부터 시작 → 장기적으로 음성·영상까지 확장.  
- 지속적인 사용자 유대감을 기반으로 커머스·보험·데이터 협력 등 다양한 수익 모델을 기대할 수 있음.

---

## 🤝 협업방안

현재 Document Loaders, Embeddings, Vector Store, LangGraph 등 커리큘럼 핵심 주제를 포함하고 있습니다.
팀원별로 OCR·데이터 로더, VectorDB·RAG 설계, LangGraph 워크플로우, Memory/Persona 설계를 분담합니다.


데이타를 모아서 뭘 할수 있는가

생성된 결과의 검증은?

---

## 🧪 OCR 파이프라인 반환 타입 표준화 (Pydantic v2)

최근 OCR 파이프라인의 I/O 계약이 Pydantic v2 모델 기반으로 통일되었습니다. 단계별로 아래의 모델 인스턴스를 반환/입력으로 사용합니다.

- 이미지 → OCR: `OCRResultEnvelope`
- OCR → 추출: `ExtractionEnvelope` (data는 dict 형태로 추출 결과를 포함)
- 추출 병합: `MergeEnvelope`

핵심 포인트

- 모든 단계는 “Pydantic 모델 인스턴스”를 반환합니다. JSON이 필요할 때만 직렬화하세요.
- JSON 직렬화는 Pydantic v2 API를 사용하세요: `model_dump_json(indent=2, ensure_ascii=False)`
- OCR 결과 텍스트 토큰은 `ocr_env.data.items`에서 접근합니다.
- 추출 단계의 병합은 “추출 dict들의 리스트”를 입력으로 받습니다. `merge_extractions(list[dict]) → MergeEnvelope`
- 스트리밍 진행 이벤트는 dict이며, `result` 키에 모델 인스턴스가 포함될 수 있습니다.

간단 예시

```python
from app.services.analysis import LabReportExtractor
from app.models.envelopes import OCRResultEnvelope

# 1) 이미지 → OCR 결과는 검사 리포트 서버(`backend/mcp_servers/lab_report`)가 내부적으로 수행할 수 있습니다.
#    또는 이미 확보한 OCRResultEnvelope가 있다면 그대로 전달할 수도 있습니다.
ocr_env: OCRResultEnvelope = ...

extractor = LabReportExtractor()

# 2) OCR → 추출(모델)
extract_env = extractor.ocr_to_extraction(ocr_env)

# 3) 여러 추출 결과 병합(모델) → JSON 출력
merged_env = extractor.merge_extractions([extract_env.data])
print(merged_env.model_dump_json(indent=2, ensure_ascii=False))
```

마이그레이션 노트

- 과거 list/dict 기반 반환(예: `ocr_result[0]`)은 제거되었습니다. 모델 속성으로 접근하세요.
- 모델 → dict/JSON 변환은 명시적 직렬화로 처리하세요(`model_dump`, `model_dump_json`).
- 노트북 예시는 `tests/notebooks/ocr/paddleocr_inline_test.ipynb`를 참고하세요.

자세한 계약은 `docs/pipeline_contract.md`를 참고하세요.

