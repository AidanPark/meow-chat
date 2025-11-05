# MCP 서버 조직화를 위한 권장 디렉토리 구조

meow-chat/
├── mcp_servers/                    # 새로 추가: MCP 서버 전용 디렉토리
│   ├── __init__.py
│   ├── config/                     # MCP 서버 설정
│   │   ├── server_registry.py     # 서버 등록/관리
│   │   └── transport_config.py    # 전송 방식 설정
│   ├── health/                     # 건강 분석 서버군(통합)
│   │   └── cat_health_server.py    # 건강 분석 도구(혈액/판정/요약 등)
│   ├── knowledge/                  # 지식베이스 서버군
│   │   ├── veterinary_kb_server.py
│   │   ├── medical_guidelines_server.py
│   │   └── reference_data_server.py
│   ├── communication/              # 대화/인터페이스 서버군
│   │   ├── chat_server.py
│   │   ├── llm_server.py
│   │   └── memory_server.py
│   └── shared/                     # 공통 유틸리티
│       ├── base_server.py          # MCP 서버 베이스 클래스
│       ├── error_handlers.py
│       └── logging_utils.py
├── app/                            # 기존 앱 로직 (MCP 클라이언트로 변환)
│   ├── mcp_clients/               # 새로 추가: MCP 클라이언트
│   │   ├── cat_health_client.py
│   │   └── app.py
│   └── web/                       # 웹 인터페이스
│       ├── streamlit_app.py
│       └── fastapi_app.py
├── data/                          # 기존 유지
└── tests/
    ├── mcp_servers/               # MCP 서버 테스트
    └── integration/               # 통합 테스트