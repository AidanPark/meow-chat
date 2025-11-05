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

## Docker

Build and run all MCP servers with Docker Compose:

```bash
docker compose up --build -d
```

Logs:

```bash
docker compose logs -f backend-mcp
```

Stop:

```bash
docker compose down
```

### OCR (OpenCV/PaddleOCR)

OCR is now included by default in the base runtime. The backend image installs required system libraries (libgl1, libglib2.0-0, libxext6, libsm6, libxrender1, libgomp1) and Python dependencies from `backend/requirements.txt` (opencv-python-headless, paddleocr, paddlepaddle for Linux x86_64).

Quick check after build/run:

```bash
docker compose up --build -d
docker exec -it meowchat-backend-mcp bash -lc "paddleocr --version || python -c 'import paddleocr; print(\"paddleocr import OK\")'"
```

If your platform lacks compatible wheels (e.g., Apple Silicon), use the Conda-based image below.

### Conda-based image

An alternative Dockerfile is available at `backend/Dockerfile.conda` which builds a Conda environment from `backend/environment.yml`.

```bash
docker build -f backend/Dockerfile.conda -t meowchat-backend-conda .
docker run --rm -it -p 8000-8003:8000-8003 meowchat-backend-conda
```
