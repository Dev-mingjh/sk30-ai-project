"""OpenAI 임베딩 호출 모듈."""
# [날짜 수정: 2026-01-25 임베딩 모듈 분리]
from typing import List, Optional

from openai import OpenAI

from ..configs.env import get_openai_key


def embed_texts(texts: List[str], model: Optional[str] = None) -> List[List[float]]:
    """텍스트 리스트를 임베딩 벡터 리스트로 변환."""
    model = model or "text-embedding-3-small"
    api_key = get_openai_key()

    if not api_key:
        raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

    client = OpenAI(api_key=api_key)
    resp = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in resp.data]
