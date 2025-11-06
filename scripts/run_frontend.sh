#!/usr/bin/env bash

# Run Streamlit frontend using the project conda environment.
# Usage: bash scripts/run_frontend.sh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$ROOT_DIR/frontend"

ENV_NAME="meow-chat"

echo "[run_frontend] Using conda env: $ENV_NAME"
echo "[run_frontend] Working dir: $(pwd)"

# Run Streamlit in headless mode by default when on a server; remove flags if you want local browser auto-open.
# Use `python -m streamlit` to avoid PATH issues with user-level scripts overshadowing the env binary.
conda run -n "$ENV_NAME" python -m streamlit run app.py --server.headless true
