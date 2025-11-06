Cloud Run(CPU) + GitHub Actions를 적용하고 싶은 경우의 방향성을 한국어로 정리합니다.

요약
- Kubernetes는 굳이 필요 없음: Cloud Run은 “서버리스 컨테이너”로, GKE를 직접 운영하지 않아도 됩니다. 하루 100장 수준의 트래픽과 저비용/간편 CI/CD 목표라면, Cloud Run 단독이 가장 단순하고 경제적입니다.
- 본 레포는 로컬 실행/개발 환경에 집중합니다. 배포용 컨테이너 구성은 별도 레포/파이프라인에서 관리하는 것을 권장합니다.

왜 Kubernetes까지 붙이는 게 과한가?
- 운영 복잡도/비용: GKE는 클러스터 관리/업데이트/노드 비용이 발생합니다. 트래픽이 적을수록 고정비 비효율이 커집니다.
- Cloud Run이 이미 해결: 오토스케일, 롤링 배포, 리비전/트래픽 스플릿, 비밀/환경변수 관리, 로깅/모니터링.

추천 구성(현재 요구 기준)
- Cloud Run(완전관리형, CPU) + GitHub Actions CI/CD
- Cloud Run 설정 예시: min-instances=1, max-instances=2~4, concurrency=10~20, CPU/RAM은 워크로드에 맞춰 조정
- FastAPI 엔드포인트: POST /ocr, POST /ocr/batch
- 처리량 최적화: 소규모 마이크로배칭(예: 1초 내 윈도우), 경량 OCR 모델 사용

GitHub Actions
- main 브랜치 푸시 → 아티팩트 레지스트리 푸시 → Cloud Run 배포
- 시크릿: OIDC 워크로드 아이덴티티 또는 서비스 계정 키

관측
- Cloud Logging/Monitoring으로 지연/에러/스루풋 추적, 필요 시 알람

미래 확장 대비
- IaC(Terraform)로 Cloud Run/네트워크/레지스트리 정의
- 필요 시 GKE로의 마이그레이션을 고려할 수 있으나, 현 요구사항에선 과함

비용/응답성 관점 요약
- Cloud Run CPU + min-instances=1 → 항상 빠른 응답, 하루 100장 수준에서 월 수 달러대
- Kubernetes(GKE)는 idle 비용과 관리 오버헤드가 커져 현재 요구와 상충