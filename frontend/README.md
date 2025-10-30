# Streamlit Frontend (Meow Chat)

This directory contains the Streamlit chat frontend.

How to run (from repo root):

- Option A: change into the app directory then run
  - cd frontend
  - streamlit run app.py

- Option B: run with an explicit path
  - streamlit run frontend/app.py

Requirements:
- Python deps from the project (see requirements.txt)
- OPENAI_API_KEY in your environment or .env in repo root
- Optional MCP servers running at defaults (8000/8001/8002) or configure frontend/config/mcp_servers.yml

Notes:
- Long-term memory persists under data/vectors/. Safe to keep across runs.
- You can adjust memory/token settings in the sidebar.
- Profiles act as namespaces for memory separation.
