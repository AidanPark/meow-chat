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

### Enable OCR extras (OpenCV/PaddleOCR)

By default, the image builds without heavy OCR dependencies. To include them:

1) Using compose build arg:

```bash
INSTALL_OCR_EXTRAS=true docker compose build backend-mcp
docker compose up -d
```

2) Or edit `docker-compose.yml` and set:

```yaml
args:
	INSTALL_OCR_EXTRAS: "true"
```

This installs system libraries (libxext6, libsm6, libxrender1, libgomp1) and pip dependencies from `backend/requirements-ocr.txt` (opencv-python-headless, paddleocr, paddlepaddle for Linux x86_64).

If your platform lacks compatible wheels (e.g., Apple Silicon), prefer the Conda-based image below.

### Conda-based image

An alternative Dockerfile is available at `backend/Dockerfile.conda` which builds a Conda environment from `backend/environment.yml`.

```bash
docker build -f backend/Dockerfile.conda -t meowchat-backend-conda .
docker run --rm -it -p 8000-8003:8000-8003 meowchat-backend-conda
```
