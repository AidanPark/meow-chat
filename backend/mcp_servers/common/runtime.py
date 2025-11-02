"""
MCP 서버용 공통 런타임 유틸리티

- setup_logging(): config/logging.yml 로깅 설정을 불러오고, 없으면 기본 로깅으로 대체
- ensure_project_root_on_sys_path(): 프로젝트 루트를 sys.path에 추가하여 app.* 모듈 임포트 지원
"""
from __future__ import annotations

import os
import sys
import logging
import logging.config
from typing import Optional, Tuple, Any, Dict

try:
    from ruamel.yaml import YAML  # type: ignore
except Exception:  # pragma: no cover - 어떤 환경에서는 ruamel이 없을 수 있음
    YAML = None  # type: ignore


def get_project_root() -> str:
    """프로젝트 루트의 절대 경로를 반환합니다(mcp_servers의 상위 디렉터리)."""
    here = os.path.dirname(__file__)
    # .../mcp_servers/common → 프로젝트 루트는 mcp_servers의 부모 디렉터리
    return os.path.abspath(os.path.join(here, "..", ".."))


def setup_logging(config_rel_path: str = os.path.join("config", "logging.yml")) -> None:
    """로깅 설정을 초기화합니다.

    - 프로젝트 루트 기준 `config/logging.yml` 파일이 있으면 이를 로드해 로깅을 구성합니다.
    - 없거나 오류가 발생하면 기본 로깅 설정으로 대체합니다.

    Args:
        config_rel_path: 프로젝트 루트 기준 로깅 YAML 파일의 상대 경로.
    """
    project_root = get_project_root()
    cfg_path = os.path.join(project_root, config_rel_path)
    try:
        if YAML is not None and os.path.exists(cfg_path):
            yaml = YAML(typ="safe")
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = yaml.load(f) or {}
            if isinstance(data, dict) and data:
                logging.config.dictConfig(data)
                return
    except Exception:
        # 예외 시 기본 로깅 설정으로 폴백
        pass
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def ensure_project_root_on_sys_path() -> None:
    """`app.*`와 같은 절대 임포트를 위해 프로젝트 루트를 sys.path에 추가합니다."""
    project_root = get_project_root()
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


def _load_yaml(path: str) -> Dict[str, Any]:
    """YAML 파일을 안전하게 로드합니다. 실패 시 빈 dict 반환."""
    try:
        if YAML is None:
            return {}
        if not os.path.exists(path):
            return {}
        yaml = YAML(typ="safe")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_mcp_server_settings(server_key: str, default_port: int, default_host: str = "127.0.0.1") -> Tuple[str, int]:
    """MCP 서버의 호스트/포트를 환경변수 또는 설정 파일에서 로드합니다.

    우선순위(높음 → 낮음):
    1) 환경변수: MCP_{SERVER}_HOST, MCP_{SERVER}_PORT
    2) 환경변수: MCP_HOST, MCP_PORT (공통 기본값)
    3) 설정 파일: config/mcp_runtime.yml 의 mcp.defaults 및 mcp.servers.{server_key}
    4) 함수 인자의 기본값(default_host, default_port)

    Args:
        server_key: 서버 식별자(e.g., 'math_utility', 'weather_api', 'cat_health', 'ocr_core', 'extract_lab_report')
        default_port: 포트 기본값
        default_host: 호스트 기본값

    Returns:
        (host, port)
    """
    project_root = get_project_root()
    cfg_path = os.path.join(project_root, "config", "mcp_runtime.yml")
    data = _load_yaml(cfg_path)

    # 파일 값 불러오기
    file_defaults = (data.get("mcp", {}) or {}).get("defaults", {}) if isinstance(data, dict) else {}
    file_servers = (data.get("mcp", {}) or {}).get("servers", {}) if isinstance(data, dict) else {}
    file_host = None
    file_port = None
    if isinstance(file_defaults, dict):
        file_host = file_defaults.get("host")
        file_port = file_defaults.get("port")
    if isinstance(file_servers, dict) and isinstance(file_servers.get(server_key), dict):
        sk = file_servers[server_key]
        file_host = sk.get("host", file_host)
        file_port = sk.get("port", file_port)

    # 환경변수 우선
    key_upper = server_key.upper().replace("-", "_")
    env_host = os.getenv(f"MCP_{key_upper}_HOST") or os.getenv("MCP_HOST")
    env_port = os.getenv(f"MCP_{key_upper}_PORT") or os.getenv("MCP_PORT")

    host = env_host or file_host or default_host
    try:
        port = int(env_port) if env_port is not None else int(file_port) if file_port is not None else int(default_port)
    except Exception:
        port = int(default_port)

    return host, port
