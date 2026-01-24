# .env 로딩과 OpenAI API 키 주입을 담당하는 유틸 모듈
from typing import Optional
import os
from pathlib import Path
from dotenv import load_dotenv

def load_env() -> None:
    # 프로젝트 루트(.env 위치) = rag 폴더의 parent
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_path, override=True)

    # .env에 OPEN_API_KEY만 있어도 SDK 표준 키로 복사
    if os.getenv("OPEN_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = os.environ["OPEN_API_KEY"]

def get_openai_key() -> Optional[str]:
    load_env()
    return os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_API_KEY")
