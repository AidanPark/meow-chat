# Google Cloud Run 배포 가이드 (meow-chat)

형님 환경(Windows + WSL + Poetry + Streamlit)에서 **Google Cloud Run(컨테이너)** 로 가장 단순하게 배포하는 방법입니다.

> 핵심 아이디어: Streamlit 앱을 Docker 이미지로 빌드해서 Cloud Run에 올립니다.

---

## 0) 전제

- `app/Home.py`가 Streamlit 엔트리입니다.
- 환경변수는 `.env.example`에 정의된 것들을 Cloud Run 환경변수로 주입합니다.
- OCR/LLM provider는 MVP에선 `dummy`로도 배포 가능(키 없이 UI/플로우 확인 용도).

---

## 1) GCP 프로젝트/권한 준비

1) Google Cloud Console에서 프로젝트 생성
2) 결제(Billing) 연결
3) 아래 API 활성화
   - Cloud Run
   - Artifact Registry
   - Cloud Build (선택: 클라우드 빌드 쓸 때)

---

## 2) 로컬에서 Docker 빌드 테스트(선택이지만 강력 추천)

WSL 쉘(bash)에서 실행:

```bash
cd /home/aidan/projects/meow-chat

docker build -t meow-chat:local .

docker run --rm -p 8501:8501 \
  -e OCR_PROVIDER=dummy \
  -e LLM_PROVIDER=dummy \
  meow-chat:local
```

브라우저에서 `http://localhost:8501` 접속.

> 만약 Docker가 WSL에서 동작하지 않으면(Windows Docker Desktop 연동 이슈), 아래 3번(Cloud Build)로 바로 가도 됩니다.

---

## 3) (권장) Cloud Build로 빌드 + Artifact Registry에 저장

### 3.1 gcloud 로그인/프로젝트 설정

```bash
gcloud auth login

gcloud config set project YOUR_PROJECT_ID

gcloud config set run/region asia-northeast3
```

### 3.2 Artifact Registry 리포지토리 생성(1회)

```bash
gcloud services enable artifactregistry.googleapis.com

gcloud artifacts repositories create meow-chat \
  --repository-format=docker \
  --location=asia-northeast3
```

### 3.3 이미지 빌드/푸시(Cloud Build)

```bash
gcloud services enable cloudbuild.googleapis.com

gcloud builds submit \
  --tag asia-northeast3-docker.pkg.dev/YOUR_PROJECT_ID/meow-chat/meow-chat:latest \
  .
```

---

## 4) Cloud Run 배포

```bash
gcloud services enable run.googleapis.com

gcloud run deploy meow-chat \
  --image asia-northeast3-docker.pkg.dev/YOUR_PROJECT_ID/meow-chat/meow-chat:latest \
  --platform managed \
  --allow-unauthenticated \
  --port 8501 \
  --cpu 1 \
  --memory 2Gi \
  --set-env-vars OCR_PROVIDER=dummy,LLM_PROVIDER=dummy,APP_DEBUG=false,LOG_LEVEL=INFO
```

배포 후 출력되는 URL로 접속하면 됩니다.

---

## 5) 실제 LLM/OCR Provider 연결

### 5.1 OpenAI/Anthropic API 키

Cloud Run에 환경변수로 넣습니다.

- 예: OpenAI
  - `LLM_PROVIDER=openai`
  - `OPENAI_API_KEY=...`

> 권장: Secret Manager에 저장 후 Cloud Run에 secret env로 연결.

### 5.2 Google Vision OCR

- `OCR_PROVIDER=google`
- 서비스 계정 키(JSON) 파일을 그대로 컨테이너에 넣기보다는
  - Cloud Run 서비스 계정에 권한을 부여하고
  - Application Default Credentials(ADC) 방식으로 쓰는 걸 권장합니다.

필요 권한(예):
- roles/visionai.user (조직 정책에 따라 다를 수 있음)
- 또는 Vision API 호출 가능한 최소 권한

---

## 6) 자주 터지는 이슈

### 6.1 PDF 처리 실패(pdf2image)
- 컨테이너에 `poppler-utils`가 필요합니다.
- 본 repo의 `Dockerfile`에는 포함되어 있습니다.

### 6.2 pytesseract 오류
- 컨테이너에 `tesseract-ocr`가 필요합니다.
- 본 repo의 `Dockerfile`에는 포함되어 있습니다.

### 6.3 메모리 부족
- PaddleOCR/이미지 처리로 메모리 사용량이 늘 수 있습니다.
- Cloud Run 메모리를 `2Gi` 또는 `4Gi`로 올려보세요.

---

## 7) 배포 모드 추천

- 1차 배포(연결 확인):
  - `OCR_PROVIDER=dummy`
  - `LLM_PROVIDER=dummy`

- 2차 배포(LLM만 연결):
  - `LLM_PROVIDER=openai` + `OPENAI_API_KEY`
  - OCR은 dummy 또는 google

- 3차 배포(실전):
  - `OCR_PROVIDER=google` 또는 `paddle`(CPU)
  - LLM 실Key 연결

---

## 8) 다음 단계(플랫폼化)

형님이 목표로 한 "고양이 생애주기 플랫폼"으로 확장하면,
Cloud Run은 다음을 위해서도 의미가 커집니다.

- 파일 업로드/비동기 처리(Cloud Tasks, Pub/Sub)
- 장기 저장(Cloud SQL / Firestore)
- 이미지/음성 저장(GCS)
- 개인화 컨텍스트 검색(Vector DB)

---

## 0.1) 배포 방식 선택 (빠르게 올리고, CI/CD는 최소로)

형님 상황처럼 **지금 프로젝트 형태가 오래 가지 않을 예정**이고,
"일단 Cloud Run에 올려서 URL로 확인"이 목표라면 **대부분 Docker(Cloud Build) 방식이 더 단순**합니다.

### A) GitHub 연결(자동 배포)
- 장점:
  - `main` 브랜치에 push만 하면 보통 **자동 빌드 + 자동 배포**까지 이어짐
  - 콘솔에서 이력/리비전 관리가 편함
- 단점(지금 단계에서 비용):
  - 최초 1회 연결/권한 설정이 필요
  - 트리거 브랜치/빌드 방식(Dockerfile vs Buildpacks) 선택 등 설정 항목이 많음
  - 장기적으로는 편하지만, 단기 MVP엔 "설정 노력"이 상대적으로 큼

### B) Docker 컨테이너 배포(Cloud Build + gcloud run deploy) ✅ 추천(단기 MVP)
- 장점:
  - 명령어 몇 줄로 끝(가장 예측 가능)
  - 현재 repo에 `Dockerfile`이 이미 있으므로 삐끗할 지점이 적음
  - CI/CD를 거의 안 해도, 필요할 때만 수동으로 다시 배포 가능
- 단점:
  - push만으로 자동 배포되진 않음(대신 `gcloud builds submit` 한 번이면 됨)

**결론(형님 상황 기준)**
- "지금 형태가 오래 안 간다" + "빨리 올려서 확인"이면 → **B(Docker/Cloud Build) 방식이 더 낫습니다.**
- GitHub 자동 배포는 나중에 구조가 안정화될 때(Phase 2 이후) 붙여도 늦지 않습니다.

---

## 0.2) GitHub 연결 배포는 진짜 push만 하면 되나?

"저장소 연결"을 사용하면, 설정에 따라 다음이 자동으로 됩니다.

- `push`(특정 브랜치) → Cloud Build 자동 실행 → 이미지 빌드/저장 → Cloud Run 새 리비전 배포

다만, 이 자동화를 위해 최초에 아래를 정해야 합니다.
- 트리거 브랜치(예: `main`)
- 빌드 방식(권장: **Dockerfile 기반**)
- 환경변수/시크릿(Secret Manager 권장)

"그냥 연결만"으로 모든 게 끝나진 않지만,
한 번 세팅되면 이후에는 push로 자동 배포가 맞습니다.
