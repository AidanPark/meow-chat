# syntax=docker/dockerfile:1

# Streamlit on Cloud Run (CPU)
# - Keeps layers stable for Poetry
# - Runs as non-root

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System deps:
# - build-essential: some python wheels may need compilation
# - poppler-utils: pdf2image for PDF support
# - tesseract-ocr: pytesseract fallback
# - libgl1, libglib2.0-0: opencv headless runtime deps sometimes required
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    poppler-utils \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Poetry (pinned) and deps
RUN pip install --no-cache-dir poetry==1.8.5

# Copy dependency files first to leverage Docker cache
COPY pyproject.toml poetry.lock ./

# Install deps into the global env (no venv inside container)
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi --no-root

# Copy app code
COPY app ./app
COPY src ./src
COPY scripts ./scripts
COPY docs ./docs
COPY .env.example ./.env.example

# Streamlit listens on 8501 by default
ENV PORT=8501
EXPOSE 8501

# Cloud Run requires binding to 0.0.0.0 and respecting $PORT
CMD ["streamlit", "run", "app/Home.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true", "--browser.gatherUsageStats=false"]
