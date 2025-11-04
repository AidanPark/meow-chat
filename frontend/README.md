# Streamlit 프론트엔드 (Meow Chat)

이 디렉터리는 Streamlit 기반 채팅 프론트엔드를 포함합니다. 현재 앱은 ReAct 전용 모드로 동작하며 응답을 토큰 단위로 스트리밍합니다.

실행 방법 (레포 루트 기준):

- 옵션 A: 디렉터리로 이동 후 실행
  - cd frontend
  - streamlit run app.py

- 옵션 B: 경로를 명시해 실행
  - streamlit run frontend/app.py

요구사항:
- 프로젝트 Python 의존성(예: backend/requirements.txt)
- 환경변수에 OPENAI_API_KEY 존재 또는 레포 루트의 .env 파일
- 선택사항: MCP 서버를 기본 포트(8000/8001/8002/8004/8005 등)로 실행하거나 `frontend/config/mcp_servers.yml`에서 엔드포인트 설정

참고:
- 장기 기억은 `frontend/data/vectors/` 등에 저장되며, 재실행 시에도 유지할 수 있습니다.
- 사이드바에서 메모리/토큰 설정을 조절할 수 있습니다.
- 프로필(Profile)은 사용자/페르소나별 메모리 네임스페이스를 분리합니다.

## MCP 서버 (로컬 권장)

- 시작: `bash backend/mcp_servers/start_servers.sh`
- 중지: `bash backend/mcp_servers/stop_servers.sh`
- 주의: 시작 스크립트는 source로 실행하지 말고 bash로 실행하세요(경로 계산 오류 방지).

## 기본 엔드포인트(`frontend/config/mcp_servers.yml` 참고)

- math_utility: http://localhost:8000/sse
- weather_api:   http://localhost:8001/sse
- cat_health:    http://localhost:8002/sse
- extract_lab_report: http://localhost:8004/sse
- memory:        http://localhost:8005/sse

## 트러블슈팅

- “unhandled errors in a TaskGroup …”처럼 보이면 `frontend/logs/streaming.log`에서 중첩 스택을 확인하세요.
- MCP 서버가 실제로 설정된 포트에서 동작 중인지 확인하세요(시작 스크립트 사용 또는 `frontend/config/mcp_servers.yml` 업데이트).
- `OPENAI_API_KEY`가 환경 또는 `.env`에 올바르게 설정되었는지 점검하세요.
