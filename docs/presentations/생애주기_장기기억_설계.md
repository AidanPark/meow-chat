# RAG 기반 장기 메모리 아키텍처

이 문서는 장기간(수년)에 걸친 대화를 안정적으로 유지하기 위해, 단기 대화 컨텍스트와 RAG(Retrieval-Augmented Generation) 기반 장기 메모리를 결합한 하이브리드 설계를 제안합니다. 현재 Meow Chat 스택(Streamlit UI + LangGraph + MCP 도구 + OpenAI 모델)에 최소 변경으로 적용 가능하며, 점진적으로 고도화할 수 있습니다.

## 목표

- 토큰/지연/비용 폭증 없이 다년간의 대화 연속성과 관련성을 보장
- 최근 대화는 원문 그대로 유지(단기 정확성), 오래된 지식은 검색 가능한 사실로 관리(장기 메모리)
- 드리프트에 강함: 시간에 따라 통합/중복 제거/정정 가능
- 프라이버시·거버넌스 지원: PII 처리, 보존/삭제 정책, 테넌트 격리, 감사 가능성

## 상위 설계(하이브리드)

- 단기 작업 메모리
  - 최근 N턴의 원문 대화(예: 최근 6–10턴)
  - 더 이전 컨텍스트의 롤링 요약(Conversation Summary Buffer)
- 장기(에피소드/의미) 메모리 = RAG
  - 기억할 가치가 있는 사실/결정/선호/제약/타임라인을 메모리 청크로 벡터 DB에 저장
  - 쿼리마다 의미 유사도 + 시간 감쇠 + 중요도 가중을 혼합한 점수로 Top-K 검색
- 선택적 프로필/타임라인/정책 문서
  - 항상 포함하거나 높은 가중치로 검색되는 안정적 컨텍스트: 사용자 프로필, 장기 목표, 제약, 주요 이정표

턴당 LLM 컨텍스트 구성:
1) System: 현재까지의 간결 요약(+ 고정 정책)
2) Retrieved memories: Top-K 장기 메모리 항목(필요 시 추상적 병합)
3) Recent raw turns: 최근 N턴 원문 + 현재 사용자 입력

## 데이터 모델

메모리 레코드(벡터 스토어 + 메타데이터 스토어):
- id: string(UUID)
- user_id: string(테넌트 분리)
- type: enum ["fact", "preference", "constraint", "decision", "todo", "timeline", "profile", "note"]
- content: string(정규화된 간결 텍스트; 필요 시 핵심 필드는 구조화 JSON)
- embedding: vector(선택한 임베딩 모델)
- importance: float(0–1) — 스코어링 및 보존 정책에 사용
- timestamp: iso8601 또는 epoch
- source_turn_ids: list[string](추적성)
- topic/tags: list[string]
- version: int
- pii_flags: list[string](비식별화 힌트)

요약 문서(주기적 통합 산출물):
- id, user_id, span(시간 범위), topics, summary_text, linked_source_ids

## 쓰기 파이프라인(각 턴 이후)

1) 후보 추출
   - 입력: 최근 턴 + 어시스턴트 응답
   - 경량 LLM 프롬프트 또는 휴리스틱으로 메모리 후보 추출(사실/결정/선호/마감/반복 이슈 등)
2) 스코어링/정규화
   - 중요도 점수(0.0–1.0): 현저성, 안정성, 미래 유용성에 기반
   - 텍스트 정규화: 간결, 자체완결, 최소한의 참조
   - 가능하면 PII 마스킹/축소
3) 업서트
   - 의미 유사도 임계치 + 주제 그룹핑으로 중복 제거
   - 벡터 스토어 + 메타 스토어에 메모리 청크 업서트
4) 거버넌스 훅
   - source_turn_ids와 함께 생성 로그
   - 보존 라벨, 영구 저장 시 암호화 적용

## 검색 파이프라인(각 턴 이전)

1) 쿼리 빌딩
   - 현재 사용자 입력 + 추출 엔티티 + summary_text로 쿼리 구성
   - 선택적으로 사용자 프로필/태그나 최근 도구 출력으로 확장
2) 후보 검색
   - 코사인 유사도 기반 Top-K 벡터 검색(토큰 예산에 따라 K ≈ 6–12)
   - 혼합 점수: sim_score*w_sim + time_decay*w_time + importance*w_imp
     - time_decay: exp(-lambda*age_days) 또는 구간(piecewise) 모델
3) 재정렬/병합
   - 근접 중복 제거, 주제별 클러스터링, 다양성 유지
   - 필요 시 LLM으로 압축 병합(추상적 요약)하여 짧은 메모리 컨텍스트 생성
4) 출력
   - LLM 맥락에 주입할 소량의 깔끔하고 관련성 높은 메모리 스니펫

## 컨텍스트 조립

- system: summary_text(롤링 요약) + 고정 정책/프로필 헤더
- memory: 병합된 Top-K 메모리 스니펫(RAG 결과)
- messages: 최근 N턴 원문 + 신규 사용자 메시지
- 토큰 가드레일: 우선순위에 따라 적응적으로 잘라냄(원문 > 메모리 > 요약)

## 요약/통합

- 롤링 요약 트리거: 최근 턴 윈도우가 N 초과 또는 토큰 한계 근접 시
  - 오래된 턴을 summary_text로 요약, 최근 N턴만 원문 유지
- 주기적 통합(일/주 단위)
  - 오래된 메모리를 주제/시간 창으로 묶어 상위 수준 요약 생성, 대체된 항목의 중요도 낮춤
  - 보존/삭제 정책 적용(낮은 중요도의 오래된 항목 제거 등)

## 저장소 선택

- 벡터 DB
  - 개발: Chroma/FAISS(내장, 간편)
  - 운영: Qdrant/Weaviate/Milvus/pgvector(관리형 또는 클러스터링)
- 임베딩
  - OpenAI text-embedding-3-large(높은 재현) 또는 small(비용 효율) — 프라이버시 요구 시 로컬(bge-m3 등)
  - 백엔드 기본값에 맞춘 차원/정규화/인덱스 파라미터
- 메타데이터 스토어
  - 경량: SQLite/Postgres(메타/감사)
  - 대안: 벡터 DB payload에 메타 전부 저장(백엔드 지원 시)

## 프라이버시/컴플라이언스

- 쓰기 단계의 PII 분류/마스킹, 저장 시 암호화(DB/KMS)
- 테넌트 격리: user_id별 인덱스/네임스페이스 분리
- 보존 정책: 삭제 요청 처리, 타입별 TTL 구성 가능
- 감사: 누가/언제/왜 메모리를 생성/수정/요약했는지 기록

## 가시성/평가

- 메트릭: 검색 지연, Top-K 적중률, 커버리지(관련 사실 포함 비율), 토큰 사용량
- 트레이스: 턴별로 어떤 메모리가 주입되었는지, 답변 품질에 미친 영향
- 오프라인 평가: 합성/실데이터 기반 Q/A로 검색 정밀도/재현율 및 과업 성공 측정

## 현 코드베이스와 통합

`frontend/services/memory/` 하위 신규 모듈 제안:

- memory_store.py
  - 벡터 DB + 메타 스토어 인터페이스
  - 최소 API:
    - upsert_memories(user_id: str, memories: list[Memory]) -> list[str]
    - retrieve(user_id: str, query: str, k: int, filters: dict | None = None) -> list[Memory]
    - consolidate(user_id: str, policy: dict) -> list[SummaryDoc]
    - delete(user_id: str, ids: list[str]) -> None

- memory_writer.py
  - extract_candidates(recent_turns, assistant_reply) -> list[MemoryCandidate]
  - score_and_normalize(candidates) -> list[Memory]

- memory_retriever.py
  - rewrite_query(recent_turns, summary_text) -> str
  - retrieve_memories(user_id, query, now, k) -> list[Memory](혼합 스코어링)

에이전트 러너 연동(`services/agent_runner.py`):
- build_context_messages(summary_text, recent_turns, retrieved_memories, new_user)
- run_agent_streaming(messages, model, tools) (기존 제너레이터 유지)
- post_turn_write(recent_turns, assistant_reply) → memory_writer

Streamlit 상태(`state/session.py`, 추후):
- session_state["messages"], session_state["summary_text"]
- 메시지 추가/요약 업데이트용 헬퍼(getter/setter)

데이터 폴더(개발):
- `data/vectors/` 로컬 벡터 DB 파일
- `data/docs/` 통합 요약 및 메타데이터 백업

## 구성 파라미터(기본값)

- recent_turn_window: 8
- retrieval_top_k: 8
- time_decay_lambda: 0.002(튜닝)
- importance_weights: {sim: 0.7, time: 0.2, imp: 0.1}
- summarize_trigger: turns > 12 또는 추정 토큰 > 6k
- consolidation_schedule: weekly
- embedding_model: text-embedding-3-small
- pii_masking: enabled

## 단계적 롤아웃

1) 1단계: 단기 요약 버퍼
   - summary_text + 최근 N턴 추가, 아직 벡터 DB는 사용하지 않음
2) 2단계: 메모리 저장/검색(로컬 Chroma)
   - 각 턴 후 쓰기, 각 턴 전 Top-K 검색
3) 3단계: 통합/거버넌스
   - 주기적 주제 묶기/요약, 보존/삭제 워크플로
4) 4단계: 운영 벡터 DB/스케일링
   - Qdrant/Weaviate/Milvus/pgvector로 이전, 멀티 테넌트 네임스페이스
5) 5단계: 고급 랭킹/평가
   - 혼합 스코어 튜닝, 재랭킹, 오프라인/온라인 평가 계측

## 리스크와 완화책

- 드리프트/오기억: 주기적 통합 + 수정 UI/툴 제공
- 비용/지연: 임베딩 배치, Top-K 조정, 적응적 토큰 예산
- 프라이버시: 엄격한 PII 파이프라인, 암호화, 접근 제어, 삭제 요청 처리
- 복잡도: 모듈형 서비스로 분리, UI는 슬림하게, 메모리 컴포넌트 중심 테스트

## 우선순위 작업 계획

다음 순서로 구현하면 즉각적인 품질 개선과 운영 안정성을 균형 있게 확보할 수 있습니다.

 - P0: 즉시 가치 창출(완료)
   - 상세는 아래 ‘현재 구현 상태(MVP)’ 및 ‘현재 구현된 항목(우선순위 계획 기준)’ 참고

 - P1: 안정성/품질 강화(바로 후속)
  1) 테스트(단위/통합)
     - store/retriever/writer/utils 유닛 테스트와 프롬프트 주입 흐름 통합 테스트 추가

- P2: 운영/확장(중기)
  7) 백업·암호화·보존정책
     - data/vectors 백업/복구, 선택 암호화, 보존 주기 정책 문서화
  8) Retrieval 평가 하니스
     - 소규모 라벨셋과 Recall@K/MRR, Top‑K/재랭킹 AB 튜닝
  9) 플러그형 벡터 스토어
     - Chroma 외 Qdrant/pgvector 선택 가능, 마이그레이션 스크립트 제공
  10) 가시성/비용 로깅
     - 토큰/메모리 히트/도구 사용/비용 추정 로깅, 사이드바 진단 토글

## 현재 구현 상태(MVP)

본 저장소에는 장기기억 기능의 MVP가 구현되어 바로 사용 가능합니다.

- 컨텍스트 주입 파이프라인
   - 프리턴:
      - 롤링 요약 업데이트 + 최근 N턴 유지
      - 고정 코어 사실 슬롯(pinned core-facts) 생성 후 system 블록으로 항상 주입(별도 토큰 예산)
      - 장기 메모리 Top‑K 검색 → 토큰 예산(블록/항목) 내로 트리밍 → system 블록으로 주입
      - 타임라인/검색 UI에서 사용자가 선택한 항목은 우선순위로 병합 주입
   - 포스트턴:
      - 대화로부터 기억 후보 추출 → 정규화/타입 추정/중요도 가중 → 간단 디듀프 후 저장

- 토큰 예산 관리
   - tiktoken이 있으면 정확 토큰 카운팅, 없으면 1 token ≈ 4 chars 근사 폴백
   - 사이드바에서 블록 상한/항목 상한/핵심 슬롯 상한 슬라이더로 즉시 제어

- 프로필/네임스페이스 분리
   - 사이드바에서 프로필 추가/전환
   - 프로필 전환 시 user_id 네임스페이스 변경 및 대화/검색/주입 상태 초기화

- 타임라인 · 메모리 검색 UI
   - 키워드 + 연도 범위 + 유형 필터로 검색 → 결과 선택 → “컨텍스트에 넣기”로 다음 턴 주입

- 저장소/의존성
   - 설치 시 Chroma + OpenAI 임베딩 사용, 미설치 시 JSON 폴백 저장소로 동작

- 휴리스틱 기반 타입/중요도
   - allergy/chronic/contraindication/medication/diet/profile 등 안전·의료 관련 항목에 높은 우선순위 부여

### 현재 구현된 항목(우선순위 계획 기준)

- P0-1: 고정 코어 사실 슬롯(Pinned core-facts slot) — 항상 포함되는 핵심 사실 블록 주입(전용 토큰 예산)
- P0-2: 타임라인 + 메모리 검색 UI — 연도/유형/키워드로 검색하고 선택 항목을 컨텍스트에 주입
- P0-3: 정확 토큰 카운팅(tiktoken) — 가용 시 정밀 카운트, 미가용 시 문자 기반 근사
- P0-4: 정규화/디듀프 + 중요도 스코어링 — 저장 시 포맷 정리/중복 방지/우선순위 부여
- P1-5: 사용자 프로필/네임스페이스 — 프로필 생성/전환으로 user_id 네임스페이스 분리

### 현재 앱 기본 설정(가변)

- recent_turn_window: 10
- summarize_trigger_turns: 10
- retrieval_top_k: 8
- memory_token_budget: 1200
- memory_item_token_cap: 150
- pinned_token_budget: 400
- 핵심 슬롯/장기 메모리 사용 여부, 예산 파라미터는 사이드바에서 즉시 변경 가능

### 구현 구조 개요(파일 맵)

- `frontend/app.py`: Streamlit 메인 UI/흐름, 컨텍스트 조립/스트리밍/사이드바 설정/검색 UI
- `frontend/services/context_builder.py`: system 요약 + pinned core + retrieved memories + 최근 N턴 조립
- `frontend/services/summarizer.py`: 롤링 요약 및 오래된 히스토리 프루닝
- `frontend/services/memory/memory_store.py`: Chroma/JSON 저장소 추상화
- `frontend/services/memory/memory_retriever.py`: 검색/쓰기(간이 디듀프 포함)
- `frontend/services/memory/memory_writer.py`: 후처리 추출(정규화/타입 추정/중요도)
- `frontend/services/memory/memory_utils.py`: 토큰 예산 트리밍(tiktoken 연동)
- `frontend/services/memory/core_facts.py`: pinned core-facts 블록 생성
- `frontend/services/memory/memory_search.py`: 타임라인/유형/키워드 검색 API

## 서비스 관점: 왜 장기기억인가?

- 생애주기 케어의 연속성: 고양이의 10년에 걸친 병력/백신/식단/금기/선호를 잃지 않고 이어받아 안전성과 품질을 보장합니다.
- 안전·규제 준수: 알레르기/금기/만성질환 같은 안전 임계 정보를 항상 포함시켜 오류 위험을 낮춥니다.
- 개인화·신뢰: 프로필/선호/과거 결정의 맥락을 반영한 일관된 제안으로 사용자 신뢰와 재방문율을 높입니다.
- 운영 효율·비용: 최근 대화는 원문, 오래된 기록은 검색형 스니펫으로 관리하여 토큰/비용을 제어합니다.
- 옴니채널 일관성: 프로필 네임스페이스로 다중 고양이/사용자, 채널 간 이력을 통합하고 선별적으로 주입합니다.

## 상용 수준으로 가기 위한 과제

1) 검색 품질/랭킹 고도화
- 혼합 점수(simi × recency × importance) 정식화 및 가중치 튜닝
- 중복/주제 클러스터링 → 압축 병합(LLM 리라이팅 가이드 강화)
- 재현성 평가 하니스(Recall@K/MRR), AB 구성(Top‑K/재랭킹/요약 강도)

2) 데이터 모델/정규화
- 핵심 사실 스키마화(알레르기/금기/진단/약/식단/프로필)와 버전·유효기간 관리
- 충돌/정정 워크플로(사용자/운영자 수정 UI, 출처 추적 및 롤백)

3) 보안/프라이버시/컴플라이언스
- 저장 시 암호화(KMS), 전송 암호화, 접근 제어(RBAC)
- 삭제 요청/보존 정책(유형별 TTL), 지역별 규제 대응
- 감사 로그(누가/언제/왜 생성/수정/요약했는지)

4) 신뢰성/운영성
- 백업/복구, 마이그레이션, 스키마 버전관리, 스토어 전환(Qdrant/pgvector 등) 경로
- 장애/타임아웃/재시도/멱등 처리, 레이트리밋/쿼타 방어
- 관측/비용 로그(토큰/메모리 히트/도구 사용/추정 비용), 캐시 전략

5) 테스트/품질 보증
- 유닛/통합/E2E 테스트, 부하/스트레스/카오스 테스트
- 프롬프트 주입 경로, 디듀프/정규화, 토큰 예산, 프로필 전환 등의 회귀 방지

6) UX 개선
- 메모리 인스펙터(출처/중요도/타입/시간)와 수정 UI
- 타임라인 뷰(연/월/이벤트)와 빠른 필터, 컨텍스트 사전보기/길이 미터

---

이 설계는 단기 컨텍스트로 즉각적인 반응성을, 장기 RAG로 정밀한 회상을, 통합/거버넌스로 관리 가능한 성장을 제공합니다. 기존 LangGraph + MCP 도구 체인과 자연스럽게 결합되며, 단계적으로 구축할 수 있습니다.
