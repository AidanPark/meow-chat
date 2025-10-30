# Config directory

This folder is intended for runtime configuration files that can be changed per environment without modifying source code.

Recommended usage:

- mcp_servers.yml — Endpoints and transports for MCP servers used by the Streamlit client
- app.yml — Application-level settings (feature flags, service URLs)
- logging.yml — Logging formatters/handlers and levels
- secrets templates — e.g., .env.example (but do not commit real secrets)

## Example structure

```
config/
  mcp_servers.yml            # MCP endpoints for local/dev/prod
  app.yml                    # Optional app settings
  logging.yml                # Optional logging config
  .env.example               # Document required env vars (do not include secrets)
```

## How it's used in this repo

- `frontend/app.py` reads `frontend/config/mcp_servers.yml` if present. Otherwise it falls back to localhost defaults:
  - math_utility: http://localhost:8000/sse
  - weather_api: http://localhost:8001/sse
  - cat_health:  http://localhost:8002/sse
- MCP servers (`math_utility_server.py`, `weather_api_server.py`, `cat_health_server.py`) will load `config/logging.yml` for structured logging if it exists; otherwise they fall back to a simple `basicConfig`.

## Tips

- Keep environment secrets in `.env` at the project root. Use `config/.env.example` as a template to document required variables.
- For production, prefer environment variables or a secrets manager over committing live credentials.
