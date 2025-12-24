# API 키 발급 가이드

냥닥터 서비스를 사용하기 위해 필요한 API 키 발급 방법을 안내합니다.

## 📋 필요한 API 키

### 1. **Google Cloud Vision API** (OCR용)

#### 발급 절차:

1. **Google Cloud Console 접속**
   - https://console.cloud.google.com/

2. **프로젝트 생성**
   - 새 프로젝트 생성 또는 기존 프로젝트 선택

3. **Vision API 활성화**
   - "API 및 서비스" > "라이브러리"
   - "Cloud Vision API" 검색 후 활성화

4. **서비스 계정 생성**
   - "API 및 서비스" > "사용자 인증 정보"
   - "사용자 인증 정보 만들기" > "서비스 계정"
   - 서비스 계정 이름 입력 후 생성
   - 역할: "Cloud Vision API 사용자" 부여

5. **JSON 키 다운로드**
   - 생성된 서비스 계정 클릭
   - "키" 탭 > "키 추가" > "새 키 만들기"
   - JSON 형식 선택 후 다운로드

6. **프로젝트에 안전하게 저장**
   ```bash
   # 프로젝트 루트에 .credentials 폴더 생성 (이미 있다면 생략)
   mkdir -p .credentials
   
   # 다운로드한 JSON 파일을 .credentials 폴더로 이동 및 이름 변경
   mv ~/Downloads/your-long-filename.json .credentials/google-vision-key.json
   
   # 파일 권한 설정 (본인만 읽기 가능)
   chmod 600 .credentials/google-vision-key.json
   ```

7. **환경변수 설정**
   ```bash
   # .env 파일에 추가 (상대 경로 사용 권장)
   OCR_PROVIDER=google
   GOOGLE_APPLICATION_CREDENTIALS=.credentials/google-vision-key.json
   ```

   ⚠️ **보안 주의:**
   - `.credentials/` 폴더는 `.gitignore`에 포함되어 Git에 커밋되지 않습니다
   - 절대 프로젝트 루트에 JSON 파일을 직접 두지 마세요!

#### 💰 비용:
- 무료 할당량: 매월 1,000건
- 초과 시: 이미지당 $1.50 / 1,000건

---

### 2. **OpenAI API** (LLM용)

#### 발급 절차:

1. **OpenAI 계정 생성**
   - https://platform.openai.com/signup

2. **API 키 생성**
   - 로그인 후 https://platform.openai.com/api-keys
   - "Create new secret key" 클릭
   - 키 이름 입력 후 생성
   - ⚠️ **즉시 복사하세요! 다시 볼 수 없습니다**

3. **환경변수 설정**
   ```bash
   # .env 파일에 추가
   LLM_PROVIDER=openai
   OPENAI_API_KEY=sk-proj-...
   ```

#### 💰 비용:
- **GPT-4o** (권장):
  - Input: $2.50 / 1M tokens
  - Output: $10.00 / 1M tokens
- **GPT-4o-mini** (저렴):
  - Input: $0.15 / 1M tokens
  - Output: $0.60 / 1M tokens

#### 💡 팁:
- 처음 가입 시 $5 무료 크레딧 제공
- 사용량 제한(Usage limits) 설정 권장

---

### 3. **Anthropic API** (대안 LLM용, 선택사항)

#### 발급 절차:

1. **Anthropic Console 접속**
   - https://console.anthropic.com/

2. **API 키 생성**
   - "API Keys" 메뉴
   - "Create Key" 클릭
   - 키 이름 입력 후 생성

3. **환경변수 설정**
   ```bash
   # .env 파일에 추가
   LLM_PROVIDER=anthropic
   ANTHROPIC_API_KEY=sk-ant-...
   ```

#### 💰 비용:
- **Claude 3.5 Sonnet** (권장):
  - Input: $3.00 / 1M tokens
  - Output: $15.00 / 1M tokens
- **Claude 3.5 Haiku** (저렴):
  - Input: $0.80 / 1M tokens
  - Output: $4.00 / 1M tokens

---

## 🧪 테스트용 더미 모드

API 키 없이 테스트하고 싶다면 **더미 모드**를 사용하세요:

```bash
# .env 파일 설정
OCR_PROVIDER=dummy
LLM_PROVIDER=dummy
```

더미 모드에서는:
- ✅ 앱의 모든 기능 테스트 가능
- ✅ 실제 API 호출 없음 (비용 없음)
- ⚠️ 고정된 샘플 응답만 제공

---

## 🔒 보안 주의사항

### ⚠️ 절대 공개하지 마세요!

- API 키를 GitHub 등 공개 저장소에 커밋하지 마세요
- `.env` 파일은 `.gitignore`에 포함되어 있습니다
- 키가 노출되었다면 즉시 재발급하세요

### ✅ 안전한 관리 방법:

```bash
# .env 파일 권한 설정 (Linux/Mac)
chmod 600 .env

# 환경변수로 직접 설정
export OPENAI_API_KEY="sk-..."
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
```

---

## 📊 예상 비용 계산

### 시나리오: 월 100명 사용자, 각 5회 분석

**OCR (Google Vision):**
- 500 이미지 분석
- 비용: 무료 (1,000건 이내)

**LLM (OpenAI GPT-4o):**
- 평균 입력: 1,000 tokens/요청
- 평균 출력: 500 tokens/요청
- 총 요청: 500회
- 비용: 약 $6.25

**월 예상 총 비용: ~$6-10**

---

## 🆘 문제 해결

### "API 키가 유효하지 않습니다"
- API 키를 정확히 복사했는지 확인
- 공백이나 줄바꿈이 포함되지 않았는지 확인
- OpenAI: 프로젝트 API 키인지 확인

### "할당량 초과"
- Google Cloud: 청구 계정 연결 필요
- OpenAI: 사용량 제한 확인 또는 결제 수단 추가

### "권한 오류"
- Google Cloud: 서비스 계정 역할 확인
- 서비스 계정 키 파일 경로 확인

---

## 📚 참고 링크

- [Google Cloud Vision API 문서](https://cloud.google.com/vision/docs)
- [OpenAI API 문서](https://platform.openai.com/docs)
- [Anthropic API 문서](https://docs.anthropic.com/)

