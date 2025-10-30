from __future__ import annotations

import os
from typing import Dict, Any

from dotenv import load_dotenv, find_dotenv
from ruamel.yaml import YAML


def load_mcp_server_config() -> Dict[str, Dict[str, str]]:
    """Load MCP server endpoints from config/mcp_servers.yml if present, else defaults.

    Also loads .env first so environment variables are available.
    """
    # Ensure environment is loaded
    load_dotenv(find_dotenv())

    here = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(here, ".."))
    cfg_path = os.path.join(project_root, "config", "mcp_servers.yml")

    default = {
        "math_utility": {"url": "http://localhost:8000/sse", "transport": "sse"},
        "weather_api": {"url": "http://localhost:8001/sse", "transport": "sse"},
        "cat_health": {"url": "http://localhost:8002/sse", "transport": "sse"},
    }

    if os.path.exists(cfg_path):
        try:
            yaml = YAML(typ="safe")
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = yaml.load(f) or {}
            servers = data.get("servers") or {}
            cleaned: Dict[str, Dict[str, str]] = {}
            for name, info in servers.items():
                if not isinstance(info, dict):
                    continue
                url = info.get("url")
                transport = info.get("transport", "sse")
                if url:
                    cleaned[name] = {"url": url, "transport": transport}
            return cleaned or default
        except Exception:
            return default
    return default
