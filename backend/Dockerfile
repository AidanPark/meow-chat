# Backend multi-MCP servers image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DOCKER=1

# Toggle OCR extras (OpenCV/PaddleOCR). Build with: --build-arg INSTALL_OCR_EXTRAS=true
ARG INSTALL_OCR_EXTRAS=false

# System dependencies (opencv, curl, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Copy only dependency lists first for better caching
COPY backend/requirements.txt backend/requirements-dev.txt* backend/requirements-ocr.txt* ./backend/

# Install Python dependencies
RUN pip install --upgrade pip && \
        pip install -r backend/requirements.txt || true && \
        if [ -f backend/requirements-dev.txt ]; then pip install -r backend/requirements-dev.txt || true; fi && \
        if [ "${INSTALL_OCR_EXTRAS}" = "true" ]; then \
            apt-get update && apt-get install -y --no-install-recommends \
                libxext6 libsm6 libxrender1 libgomp1 && \
            rm -rf /var/lib/apt/lists/* && \
            pip install -r backend/requirements-ocr.txt || true; \
        fi

# Copy the whole repo (frontend kept for convenience; main runtime is backend)
COPY . .

# Expose MCP server ports
EXPOSE 8000 8001 8002 8003

# Start all MCP servers (script backgrounds them) and keep container alive
CMD ["bash", "-lc", "bash backend/mcp_servers/start_servers.sh && tail -f /dev/null"]
