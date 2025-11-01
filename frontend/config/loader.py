from __future__ import annotations

import os
from typing import Dict, Any

from dotenv import load_dotenv, find_dotenv
from ruamel.yaml import YAML


def load_mcp_server_config() -> Dict[str, Dict[str, str]]:
    """
    MCP 서버 엔드포인트 설정을 로드합니다.
    - config/mcp_servers.yml 파일이 있으면 해당 YAML에서 서버 목록을 읽어옴
    - 없거나 오류가 발생하면 기본값(default) 사용
    - .env 파일을 먼저 로드하여 환경변수도 활용 가능
    반환값: 각 서버 이름별로 URL과 transport(sse) 정보를 담은 딕셔너리
    """
    # Ensure environment is loaded
    load_dotenv(find_dotenv())

    here = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(here, ".."))
    cfg_path = os.path.join(project_root, "config", "mcp_servers.yml")

    if not os.path.exists(cfg_path):
        raise FileNotFoundError(
            f"필수 설정 파일이 없습니다: {cfg_path}\n"
            "MCP 서버 엔드포인트를 정의한 YAML 파일을 생성한 후 다시 실행하세요."
        )

    try:
        yaml = YAML(typ="safe")
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = yaml.load(f) or {}
        servers = data.get("servers") or {}
        if not isinstance(servers, dict) or not servers:
            raise ValueError("servers 항목이 비어있거나 잘못되었습니다.")
        cleaned: Dict[str, Dict[str, str]] = {}
        for name, info in servers.items():
            if not isinstance(info, dict):
                continue
            url = info.get("url")
            transport = info.get("transport", "sse")
            if not url:
                raise ValueError(f"{name} 항목에 url이 정의되지 않았습니다.")
            cleaned[name] = {"url": url, "transport": transport}
        if not cleaned:
            raise ValueError("유효한 MCP 서버 설정을 찾을 수 없습니다.")
        return cleaned
    except Exception as exc:
        raise RuntimeError(
            f"MCP 서버 설정을 로드하지 못했습니다 ({cfg_path}).\n"
            "YAML 형식을 확인하거나 파일 내용을 검토하세요."
        ) from exc
