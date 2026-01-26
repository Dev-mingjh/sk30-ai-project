# OpenAI 임베딩 호출 모듈
from openai import OpenAI

from ..configs.constants import DEFAULT_EMBED_MODEL
from ..configs.env import get_openai_api_key

# 텍스트 리스트를 임베딩 벡터 리스트로 변환
def embed_texts(texts: list[str], model: str | None = None) -> list[list[float]]:
    # 기본 모델은 constants에서 통일
    model = model or DEFAULT_EMBED_MODEL

    # .env 로드 + 키 보정(OPEN_API_KEY -> OPENAI_API_KEY)은 env 모듈이 담당
    api_key = get_openai_api_key()
    if not api_key:
        raise ValueError("OPENAI_API_KEY(또는 OPEN_API_KEY)가 .env에 설정되지 않았습니다.")

    client = OpenAI(api_key=api_key)

    # OpenAI Embeddings 호출
    response = client.embeddings.create(model=model, input=texts)

    # embeddings만 리스트로 추출
    return [item.embedding for item in response.data]