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
from typing import Optional

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
