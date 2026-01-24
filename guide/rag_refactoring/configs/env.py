"""환경변수(.env) 로드 및 OpenAI API 키 조회 모듈.

- 사용 키: OPENAI_API_KEY (우선), OPEN_API_KEY (fallback)
"""
# [날짜 수정: 2026-01-25 환경변수 로딩 모듈 분리]
from pathlib import Path
from typing import Optional
import os

from dotenv import load_dotenv


def load_env() -> None:
    """프로젝트 루트의 .env를 로드하고 OPEN_API_KEY를 OPENAI_API_KEY로 보정."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"

    load_dotenv(dotenv_path=env_path, override=True)

    if os.getenv("OPEN_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = os.environ["OPEN_API_KEY"]


def get_openai_key() -> Optional[str]:
    """OPENAI_API_KEY 또는 OPEN_API_KEY를 반환 (없으면 None)."""
    load_env()
    return os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_API_KEY")
