# 아키텍처 개요 (meow-chat)

> **목적**: `docs/plan.md`는 진행/할 일 중심으로 유지하고, 이 문서는 아키텍처/설계 원칙을 한 곳에 모아 둡니다.

## 1) 설계 원칙

1. **레이어 분리**: UI(`app/`)와 로직(`src/`) 분리
2. **추상화 우선**: Provider 패턴으로 외부 의존성(OCR/LLM 등) 격리
3. **모듈 분리**: 책임 단위로 패키지 구성
   - `preprocessing/`: OCR 전 이미지 처리
   - `ocr/`: 이미지 → 텍스트
   - `lab_extraction/`: 텍스트 → 구조화 데이터
   - `llm/`: LLM 호출 및 프롬프트
   - `chat/`: 오케스트레이션
4. **의존성 주입**: 생성자 주입으로 테스트 용이성 확보
5. **설정 중앙화**: 환경변수는 `src/settings.py`에서 관리

## 2) 핵심 구성요소

### 2.1 OCR Provider
- 목적: 이미지/PDF에서 텍스트 추출
- 구현: PaddleOCR(주력), Google Vision, EasyOCR, Dummy

### 2.2 Lab Extraction Pipeline
- 목적: OCR 결과 텍스트를 “검사 항목/수치/단위/참조범위”로 구조화
- 구현(개념): 라인 전처리 → 표 추출 → 코드/단위 정규화 → 참조범위 분석

### 2.3 LLM Provider
- 목적: 구조화된 결과 + 사용자 질문을 바탕으로 안전한 상담 메시지 생성
- 구현: OpenAI, Anthropic, Dummy

### 2.4 Chat Service
- 목적: OCR → 구조화 → LLM을 하나의 사용 흐름으로 연결

## 3) 향후 확장 포인트

- **RAG**: 수의학 지식 기반 답변 강화
- **분리 배포**: Streamlit UI ↔ API(FastAPI 등) 분리
- **관측 가능성**: 로그/트레이싱/비용 모니터링
- **비동기 처리**: OCR/분석이 무거워질 경우 큐/백그라운드 작업 고려
