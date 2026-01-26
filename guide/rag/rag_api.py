# RAG 기능을 한 곳에서 쉽게 사용할 수 있도록 함
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import os

from .retriever import ChromaRetriever
from .generator import (
    AnswerGenerator,
    build_kisa_report_system,
    build_mitre_system,
    build_kisa_guide_system,
    build_recent_cases_system,
    format_evidence,
)
from .rag_engine import RAGEngine
from .web_search.web_search import collect_web_evidence
from .configs.env import load_env
from .configs.constants import (
    DEFAULT_EMBED_MODEL,
    DEFAULT_LLM_MODEL,
    DEFAULT_TOP_K,
    COLLECTION_MITRE,
    COLLECTION_KISA_REPORT,
    COLLECTION_KISA_GUIDE,
    DEFAULT_OUT_DIR,
    DEFAULT_CHROMA_SUBDIR,
    ATTACK_LABELS,
    LABEL_TO_ATTACK,
    ATTACK_FAMILY_MAP,
)


@dataclass
class RagBundle:
    rag_mitre: RAGEngine
    rag_kisa_report: RAGEngine
    rag_kisa_guide: RAGEngine
    embed_model: str
    gen_model: str
    chroma_dir: str
    collection_mitre: str
    collection_kisa_report: str
    collection_kisa_guide: str


def create_rag_bundle(
    chroma_dir: Optional[str] = None,
    embed_model: Optional[str] = None,
    gen_model: Optional[str] = None,
    collection_mitre: Optional[str] = None,
    collection_kisa_report: Optional[str] = None,
    collection_kisa_guide: Optional[str] = None,
) -> RagBundle:
    load_env()

    chroma_dir = chroma_dir or str(Path(DEFAULT_OUT_DIR) / DEFAULT_CHROMA_SUBDIR)

    collection_mitre = collection_mitre or os.getenv("COLLECTION_MITRE", COLLECTION_MITRE)
    collection_kisa_report = collection_kisa_report or os.getenv(
        "COLLECTION_KISA_REPORT",
        os.getenv("COLLECTION_KISA", COLLECTION_KISA_REPORT),
    )
    collection_kisa_guide = collection_kisa_guide or os.getenv(
        "COLLECTION_KISA_GUIDE",
        COLLECTION_KISA_GUIDE,
    )

    embed_model = embed_model or os.getenv("OPENAI_EMBED_MODEL", DEFAULT_EMBED_MODEL)
    gen_model = gen_model or os.getenv("OPENAI_GEN_MODEL", DEFAULT_LLM_MODEL)

    retriever_mitre = ChromaRetriever(
        chroma_dir=chroma_dir,
        collection_name=collection_mitre,
        embed_model=embed_model,
    )
    retriever_kisa_report = ChromaRetriever(
        chroma_dir=chroma_dir,
        collection_name=collection_kisa_report,
        embed_model=embed_model,
    )
    retriever_kisa_guide = ChromaRetriever(
        chroma_dir=chroma_dir,
        collection_name=collection_kisa_guide,
        embed_model=embed_model,
    )

    generator = AnswerGenerator(gen_model=gen_model)

    rag_mitre = RAGEngine(retriever_mitre, generator)
    rag_kisa_report = RAGEngine(retriever_kisa_report, generator)
    rag_kisa_guide = RAGEngine(retriever_kisa_guide, generator)

    return RagBundle(
        rag_mitre=rag_mitre,
        rag_kisa_report=rag_kisa_report,
        rag_kisa_guide=rag_kisa_guide,
        embed_model=embed_model,
        gen_model=gen_model,
        chroma_dir=chroma_dir,
        collection_mitre=collection_mitre,
        collection_kisa_report=collection_kisa_report,
        collection_kisa_guide=collection_kisa_guide,
    )


def extract_attack_type(text: str) -> Optional[str]:
    t = (text or "").lower()
    for attack in ATTACK_LABELS:
        if attack.lower() in t:
            return attack
    return None


def map_attack_family(label: str) -> str:
    return ATTACK_FAMILY_MAP.get(label, label)


def answer_mitre_explain(
    bundle: RagBundle,
    attack_label: str,
    question: Optional[str] = None,
    top_k: Optional[int] = None,
) -> dict:
    if not attack_label:
        raise ValueError("attack_label is required")

    q = question or f"{attack_label} attack explanation"
    anchors = LABEL_TO_ATTACK.get(attack_label, {}).get("anchor_techniques", []) or []

    contexts = []
    if anchors:
        for tid in anchors:
            where = {
                "$and": [
                    {"technique_id": tid},
                    {
                        "$or": [
                            {"section": "Description"},
                            {"section": "Detection"},
                            {"section": "Mitigations"},
                            {"section": "Procedure Examples"},
                        ]
                    },
                ]
            }
            ctxs = bundle.rag_mitre.retrieve(
                query=f"{attack_label} {tid}",
                top_k=2,
                where=where,
                fallback=True,
            )
            contexts.extend(ctxs)

    if not contexts:
        contexts = bundle.rag_mitre.retrieve(
            q,
            top_k=(top_k or DEFAULT_TOP_K) + 2,
            where=None,
        )

    mitre_evidence = format_evidence(contexts)
    system = build_mitre_system(
        attack_label=attack_label,
        anchor_techniques=", ".join(anchors) if anchors else "",
        mitre_evidence=mitre_evidence,
    )

    answer = bundle.rag_mitre.generate(q, contexts, system=system) if contexts else "No evidence found."
    return {"answer": answer, "contexts": contexts, "question": q}


from typing import Optional

def answer_kisa_report(
    bundle: RagBundle,
    attack_label: str,
    question: Optional[str] = None,
    top_k: Optional[int] = None,
) -> dict:
    if not attack_label:
        raise ValueError("attack_label is required")

    if attack_label.lower() == "ddos":
        q = question or f"{attack_label} 상황에서 신고 절차를 단계별로 정리해줘."
        where = {"label": attack_label}

    else:
        q = question or "DDoS가 아닌 일반 침해사고 신고 절차 양식을 단계별로 정리해줘."
        where = {"section": "incident_response_guide"}

    contexts = bundle.rag_kisa_report.retrieve(
        q,
        top_k=(top_k or DEFAULT_TOP_K) + 1,
        where=where,
    )
    kisa_evidence = format_evidence(contexts) if contexts else ""
    system = build_kisa_report_system(attack_label=attack_label, kisa_evidence=kisa_evidence)

    answer = bundle.rag_kisa_report.generate(q, contexts, system=system) if contexts else "No evidence found."
    return {"answer": answer, "contexts": contexts, "question": q}


def answer_kisa_guide(
    bundle: RagBundle,
    attack_label: str,
    question: Optional[str] = None,
    top_k: int = 6,
) -> dict:
    if not attack_label:
        raise ValueError("attack_label is required")

    family = map_attack_family(attack_label)
    q = question or f"Summarize KISA guide actions for {family}."
    where = {"section": "kisa_guide_response"}

    contexts = bundle.rag_kisa_guide.retrieve(q, top_k=top_k, where=where)
    guide_evidence = format_evidence(contexts) if contexts else ""
    system = build_kisa_guide_system(family, guide_evidence)

    answer = bundle.rag_kisa_guide.generate(q, contexts, system=system) if contexts else "No evidence found."
    return {"answer": answer, "contexts": contexts, "question": q}


def answer_recent_cases(
    bundle: RagBundle,
    attack_label: str,
    question: Optional[str] = None,
    top_n: int = 2,
) -> dict:
    if not attack_label:
        raise ValueError("attack_label is required")

    q = question or f"Summarize recent cases related to {attack_label}."
    web_evidence = collect_web_evidence(attack_label, [], top_n=top_n)

    system = build_recent_cases_system(
        attack_label=attack_label,
        anchor_techniques="",
        web_evidence=web_evidence,
        top_n=top_n,
    )

    answer = bundle.rag_mitre.generate(q, [], system=system)
    return {"answer": answer, "contexts": [], "question": q}
