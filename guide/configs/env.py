import os
from dotenv import load_dotenv

_ENV_LOADED = False

def load_env(dotenv_path=None):
    global _ENV_LOADED
    if _ENV_LOADED:
        return

    if dotenv_path:
        load_dotenv(dotenv_path)
    else:
        load_dotenv()

    _ENV_LOADED = True


def get_openai_api_key():
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")
    return key