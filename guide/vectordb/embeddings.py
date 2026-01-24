from __future__ import annotations

from typing import List
from openai import OpenAI

from configs.env import get_openai_api_key
from configs.constants import DEFAULT_EMBED_MODEL

# 텍스트 리스트를 OpenAI Embedding 벡터로 변환
def embed_texts(
    texts: List[str],
    model: str | None = None,
) :
    use_model = model or DEFAULT_EMBED_MODEL
    client = OpenAI(api_key=get_openai_api_key())

    resp = client.embeddings.create(
        model=use_model,
        input=texts,
    )

    return [item.embedding for item in resp.data]
