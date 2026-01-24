from __future__ import annotations

from openai import OpenAI
from configs.env import get_openai_api_key


def get_openai_client() -> OpenAI:
    return OpenAI(api_key=get_openai_api_key())


def call_llm(
    client: OpenAI,
    model: str,
    prompt: str,
    temperature: float = 0.2,
): # -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return (response.choices[0].message.content or "").strip()