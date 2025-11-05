FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DOCKER=1

WORKDIR /workspace

# System deps (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps (reuse backend requirements for consistency)
COPY backend/requirements.txt ./backend/
RUN pip install --upgrade pip && pip install -r backend/requirements.txt || true

# Copy repo
COPY . .

EXPOSE 8501

CMD ["bash", "-lc", "streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0"]
