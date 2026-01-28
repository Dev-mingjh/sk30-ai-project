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

# 여러 컬렉션(MITRE/KISA Report/KISA Guide)용 RAGEngine과
# 공통 모델/경로 정보를 한 번에 들고 다니기 위한 묶음 객체
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


# env 로드 -> 컬렉션/모델 결정 -> Retriever/Generator/RAGEngine 생성
# - 컬렉션 이름/모델은 환경변수 우선, 없으면 constants 기본값 사용
# - chroma_dir 기본값: DEFAULT_OUT_DIR/DEFAULT_CHROMA_SUBDIR
# 반환: RagBundle (3개 RAGEngine + 모델/경로 메타 포함)
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

# 입력 문장에서 ATTACK_LABELS 중 첫 매칭 라벨을 반환
# 단순 포함 검사(정규식/우선순위 없음)라 오탐 가능
def extract_attack_type(text: str) -> Optional[str]:
    t = (text or "").lower()
    for attack in ATTACK_LABELS:
        if attack.lower() in t:
            return attack
    return None

# 라벨을 가이드 문서에 작성된 3가지 공격 유형으로으로 매핑 (디도스, 웹 침해, 서버 취학점 침해)
# 매핑이 없으면 원본 라벨 그대로 반환
def map_attack_family(label: str) -> str:
    return ATTACK_FAMILY_MAP.get(label, label)

# MITRE 기반 설명 생성
# 1) LABEL_TO_ATTACK의 anchor_techniques 우선 검색(섹션 필터 적용)
# 2) 결과가 비면 일반 질의로 fallback 검색
# 3) 증거(format_evidence)로 시스템 프롬프트 구성 후 생성
# 반환: {"answer", "contexts", "question"}
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

# KISA 신고 절차 요약
# - DDoS일 때: label 필터(특정 라벨 문단)
# - 그 외: section="incident_response_guide" (일반 신고 절차)
# 증거 기반 시스템 프롬프트(build_kisa_report_system)로 답변 생성
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

# KISA 가이드 대응 요약
# - 가이드에 작성된 3가지 공격 유형(디도스, 웹 침해, 서버 취약점 침해) 라벨로 질문 구성
# - section="kisa_guide_response" 필터만 사용
# 반환: {"answer", "contexts", "question"}
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


# 최신 사례 요약(웹 서칭)
# - collect_web_evidence로 웹 증거 수집
# - Chroma 검색 없이 시스템 프롬프트만으로 생성
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
