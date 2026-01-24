# llm/guide.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from configs.constants import DEFAULT_LLM_MODEL, DEFAULT_TOP_K
from llm.client import get_openai_client
from llm.context import build_attack_context
from llm.sections import (
    generate_section_overview,
    generate_section_technical,
    generate_section_kisa,
    generate_section_reference,
)

def generate_final_guide(
    label: str,
    anchors: List[str],
    user_query: str,
    k_mitre: int = DEFAULT_TOP_K,
    k_kisa: int = DEFAULT_TOP_K,
    web_evidence: Optional[str] = None,
    model: str = DEFAULT_LLM_MODEL,
    auto_web: bool = True,
    web_top_n: int = 3,
): 
    context = build_attack_context(
        label=label,
        anchors=anchors,
        user_query=user_query,
        k_mitre=k_mitre,
        k_kisa=k_kisa,
        web_evidence=web_evidence,
        auto_web=auto_web,
        web_top_n=web_top_n,
    )

    client = get_openai_client()
    sec1 = generate_section_overview(context, client=client, model=model)
    sec2 = generate_section_technical(context, client=client, model=model)
    sec3 = generate_section_kisa(context, client=client, model=model)
    sec4 = generate_section_reference(context, client=client, model=model)

    final_text = "\n\n".join([sec1["text"], sec2["text"], sec3["text"], sec4["text"]]).strip()

    return {
        "context": context,
        "sections": {"overview": sec1, "technical": sec2, "kisa": sec3, "reference": sec4},
        "final_text": final_text,
    }