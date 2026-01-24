"""검색 결과를 기반으로 LLM 응답 생성."""
# [날짜 수정: 2026-01-25 LLM 응답 모듈 분리]
from typing import Optional

from openai import OpenAI

from ..configs.env import get_openai_key
from ..retrieval.mitre import search_mitre
from ..retrieval.kisa import search_kisa
from .evidence import build_mitre_evidence, build_kisa_evidence


def rag_answer(
    query: str,
    col_mitre,
    col_kisa,
    category: Optional[str] = None,
    label: Optional[str] = None,
    k_mitre: int = 3,
    k_kisa: int = 3,
    model: str = "gpt-4o-mini",
) -> str:
    """MITRE/KISA 검색 결과를 근거로 LLM 응답 생성."""
    mitre_hits = search_mitre(col_mitre, query, k=k_mitre)
    kisa_hits = search_kisa(col_kisa, query, category=category, label=label, k=k_kisa)

    context = (
        "[MITRE]\n"
        + build_mitre_evidence(mitre_hits)
        + "\n\n[KISA]\n"
        + build_kisa_evidence(kisa_hits)
    )

    api_key = get_openai_key()
    if not api_key:
        raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "너는 사이버 보안 분석가다. 제공된 근거를 바탕으로 한국어로 간결하게 답하라.",
            },
            {"role": "user", "content": f"질문: {query}\n\n근거:\n{context}"},
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content
