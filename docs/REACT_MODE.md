# ReAct 전용 모드와 스트리밍

프론트엔드는 ReAct 전용 모드로 동작하며, 응답을 토큰 단위로 스트리밍합니다.

- Planner 모드는 사용자 경험 단순화와 실패 지점 감소를 위해 제거되었습니다.
- 스트리밍은 메시지 본문(content)만 출력하며, 메타데이터 노이즈를 제거했습니다.
- MCP 서버는 선택사항이지만 도구 사용을 위해 로컬 실행을 권장합니다: 수학, 날씨, 건강, 검사표 OCR(내부 OCR 포함), 메모리.
- 로컬 서버 시작: `bash backend/mcp_servers/start_servers.sh` (source 하지 말고 bash로 실행). 중지: `bash backend/mcp_servers/stop_servers.sh`.
- 엔드포인트 설정: `frontend/config/mcp_servers.yml`.
- OPENAI_API_KEY는 환경변수 또는 레포 루트의 `.env`로 설정해야 합니다.
- 스트리밍 중 발생하는 오류(중첩 ExceptionGroup 포함)는 `frontend/logs/streaming.log`에 기록됩니다.

기본 엔드포인트
- http://localhost:8000/sse math_utility
- http://localhost:8001/sse weather_api
- http://localhost:8002/sse cat_health
- http://localhost:8004/sse extract_lab_report
- http://localhost:8005/sse memory
