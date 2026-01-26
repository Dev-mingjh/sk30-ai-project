# 환경변수(.env) 로드 및 OpenAI API 키 조회 모듈
from pathlib import Path
from typing import Optional
import os

from dotenv import load_dotenv


def load_env() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"

    load_dotenv(dotenv_path=env_path, override=True)

    if os.getenv("OPEN_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = os.environ["OPEN_API_KEY"]


def get_openai_api_key() -> Optional[str]:
    load_env()
    return os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_API_KEY")
