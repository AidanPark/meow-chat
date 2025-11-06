# Backend

This folder contains the backend application and MCP servers.

Structure:

- app/: Python package with core, services, models, utils (imports start with `app.*`)
- mcp_servers/: Independent MCP servers (math, weather, health, ocr)
- config/: Logging and server configs
- data/: Runtime data (uploads, vectors, knowledge base, etc.)
- tests/: Unit, integration, and notebooks
- requirements*.txt, environment.yml

## Local development

- Start Jupyter (runs with backend as working directory):

```bash
bash backend/start_jupyter.sh
```

- Start MCP servers (math/weather/health/ocr):

```bash
bash backend/mcp_servers/start_servers.sh
```

Ports: 8000 (math), 8001 (weather), 8002 (health), 8003 (ocr)
 
### OCR (OpenCV/PaddleOCR)

OCR는 기본 런타임에서 동작합니다. 필요한 시스템 라이브러리와 Python 의존성은 `backend/requirements.txt`에 정의되어 있습니다.

빠른 점검:

```bash
python -c "import paddleocr; print('paddleocr import OK')"
```
