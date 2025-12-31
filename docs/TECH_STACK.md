# 기술 스택 (meow-chat)

> **목적**: 이 문서는 기술 선택/의존성을 기록합니다. `docs/plan.md`는 진행 순서/결정 사항 중심으로 유지합니다.

## 1) 런타임
- Python 3.12+
- Poetry

## 2) UI
- Streamlit

## 3) OCR
- PaddleOCR (주력)
- PaddlePaddle (CPU, 필요 시 GPU 전환)
- Google Cloud Vision (옵션)
- EasyOCR (옵션)

## 4) 이미지/문서 처리
- Pillow
- OpenCV (headless)
- pdf2image, PyMuPDF

## 5) LLM
- OpenAI
- Anthropic

## 6) 품질/테스트
- pytest, pytest-cov
- ruff
- mypy

## 7) 개발환경
- WSL Ubuntu 24.04
- PyCharm 2025.3.1

> 참고: 실제 버전/제약은 `pyproject.toml`이 단일 소스입니다.

