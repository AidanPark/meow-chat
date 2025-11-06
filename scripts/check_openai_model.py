#!/usr/bin/env python
from __future__ import annotations

import os
import sys


def main() -> int:
    # Load .env if present
    try:
        from dotenv import load_dotenv, find_dotenv  # type: ignore
        load_dotenv(find_dotenv())
    except Exception:
        pass

    model = sys.argv[1] if len(sys.argv) > 1 else os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini")

    # Quick probe using LangChain ChatOpenAI
    try:
        from langchain_openai import ChatOpenAI  # type: ignore
    except Exception as e:
        print(f"ERROR: langchain_openai import failed: {e}")
        return 2

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set")
        return 3

    try:
        llm = ChatOpenAI(model=model, temperature=0, timeout=12)  # type: ignore[arg-type]
        _ = llm.invoke("Reply with a single word: OK")
        print(f"AVAILABLE: {model}")
        return 0
    except Exception as e:
        print(f"UNAVAILABLE: {model} -> {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
