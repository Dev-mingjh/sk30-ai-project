"""리팩터링된 모듈을 기존 rag_v1 API처럼 노출하는 facade."""
# [날짜 수정: 2026-01-25 rag_v1 기능을 모듈별로 분리한 facade]
from .configs.constants import (
    Attack_LABELS,
    label_to_attack,
    LABEL_TO_KISA_CATEGORY,
    KISA_CATEGORY_KEYWORDS_KO,
    LABEL_KEYWORDS,
    BASE_MITRE_URL,
    LABEL_NORMALIZE_ALIASES,
)
from .configs.env import load_env, get_openai_key
from .utils.normalize import normalize_label
from .ingest.mitre_crawl import fetch_technique_text, build_mitre_chunks
from .ingest.kisa_pdf import extract_pdf_text_by_page, split_paragraphs, classify_paragraph, build_kisa_chunks
from .schema import normalize_mitre, normalize_kisa
from .vectordb.embeddings import embed_texts
from .vectordb.chroma_store import init_chroma, upsert_to_chroma
from .retrieval.mitre import search_mitre
from .retrieval.kisa import search_kisa
from .llm.evidence import build_mitre_evidence, build_kisa_evidence
from .llm.answer import rag_answer
from .scripts.build_db import (
    save_jsonl,
    load_jsonl,
    dedup_docs_by_id,
    assert_unique_ids,
    build_vector_db,
)

__all__ = [
    "Attack_LABELS",
    "label_to_attack",
    "LABEL_TO_KISA_CATEGORY",
    "KISA_CATEGORY_KEYWORDS_KO",
    "LABEL_KEYWORDS",
    "BASE_MITRE_URL",
    "LABEL_NORMALIZE_ALIASES",
    "normalize_label",
    "fetch_technique_text",
    "build_mitre_chunks",
    "extract_pdf_text_by_page",
    "split_paragraphs",
    "classify_paragraph",
    "build_kisa_chunks",
    "save_jsonl",
    "load_jsonl",
    "normalize_mitre",
    "normalize_kisa",
    "load_env",
    "get_openai_key",
    "embed_texts",
    "dedup_docs_by_id",
    "assert_unique_ids",
    "init_chroma",
    "upsert_to_chroma",
    "search_mitre",
    "search_kisa",
    "build_mitre_evidence",
    "build_kisa_evidence",
    "rag_answer",
    "build_vector_db",
]


if __name__ == "__main__":
    print("rag_v1.py: import해서 사용하세요. 예시:")
    print("  from rag_v1 import build_vector_db, rag_answer")
