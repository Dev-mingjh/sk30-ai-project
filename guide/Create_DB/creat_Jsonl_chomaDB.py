
## jsonl,chromaDB 생성코드

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import chromadb
from dotenv import load_dotenv
from openai import OpenAI


ROOT = Path(__file__).resolve().parent
RAG2_DIR = ROOT / "rag2"
sys.path.insert(0, str(RAG2_DIR))

try:
    import constants as rag2_constants  # type: ignore
except Exception:
    rag2_constants = None  # type: ignore

try:
    from normalize import normalize_label  # type: ignore
except Exception:
    normalize_label = None  # type: ignore


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def _require_fields(item: Dict[str, Any], required: List[str], source: str) -> None:
    missing = [k for k in required if not item.get(k)]
    if missing:
        raise ValueError(f"{source} JSONL missing fields: {missing} in item keys={list(item.keys())}")


def build_mitre_docs(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    docs: List[Dict[str, Any]] = []
    for x in items:
        # [날짜 수정: 2026-01-24 rag JSONL 필드 기준으로 필수 키 검증]
        _require_fields(
            x,
            ["chunk_id", "label", "technique_id", "technique_title", "section", "text", "source_url"],
            "MITRE",
        )
        chunk_id = x["chunk_id"]
        label = x["label"]
        docs.append(
            {
                "id": chunk_id,
                "text": x.get("text", ""),
                "meta": {
                    # [날짜 수정: 2026-01-24 rag 메타 필드에 맞춤]
                    "source": x.get("source", "MITRE_ATT&CK"),
                    "technique_id": x["technique_id"],
                    "technique_title": x["technique_title"],
                    "section": x["section"],
                    "label": label,
                    "attack_type": label,
                    "source_url": x["source_url"],
                },
            }
        )
    return docs


def _normalize_label(label: str) -> str:
    if normalize_label is None:
        return label
    return normalize_label(label)


def build_kisa_docs(
    items: Iterable[Dict[str, Any]],
    label_to_kisa_category: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    docs: List[Dict[str, Any]] = []
    for x in items:
        # [날짜 수정: 2026-01-24 rag JSONL 필드 기준으로 필수 키 검증]
        _require_fields(x, ["chunk_id", "label", "page_no", "text", "source_doc"], "KISA")
        chunk_id = x["chunk_id"]
        raw_label = x["label"]
        norm_label = _normalize_label(raw_label) if raw_label else raw_label
        # [날짜 수정: 2026-01-24 KISA 기본 카테고리 값 통일]
        category = "기타"
        if label_to_kisa_category:
            category = label_to_kisa_category.get(norm_label, "기타")
        page_no = x["page_no"]
        docs.append(
            {
                "id": chunk_id,
                "text": x.get("text", ""),
                "meta": {
                    # [날짜 수정: 2026-01-24 rag 메타 필드에 맞춤]
                    "source": x.get("source", "KISA"),
                    "label": norm_label,
                    "attack_type": norm_label,
                    "kisa_category": category,
                    "section": x.get("section", "incident_response_guide"),
                    "page_no": page_no,
                    "page": page_no,
                    "source_doc": x["source_doc"],
                },
            }
        )
    return docs


def dedup_docs_by_id(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # [날짜 수정: 2026-01-24 중복 ID 제거로 Chroma 업서트 오류 방지]
    deduped: Dict[str, Dict[str, Any]] = {}
    for d in docs:
        deduped[d["id"]] = d
    return list(deduped.values())


def generate_jsonl(
    mitre_path: Path,
    kisa_path: Path,
    kisa_pdf_path: Optional[Path],
    kisa_label: Optional[str],
    skip_mitre: bool,
    skip_kisa: bool,
) -> None:
    if rag2_constants is None:
        raise RuntimeError("rag2/constants.py is required for JSONL generation.")

    mitre_path.parent.mkdir(parents=True, exist_ok=True)
    kisa_path.parent.mkdir(parents=True, exist_ok=True)

    if not skip_mitre:
        # [날짜 수정: 2026-01-24 rag2 mitre_crawl로 MITRE JSONL 생성]
        from mitre_crawl import build_mitre_chunks  # type: ignore

        build_mitre_chunks(
            label_to_attack=rag2_constants.LABEL_TO_ATTACK,
            out_jsonl_path=str(mitre_path),
        )

    if not skip_kisa:
        if not kisa_pdf_path or not kisa_label:
            raise RuntimeError("KISA JSONL generation requires --kisa-pdf and --kisa-label.")
        # [날짜 수정: 2026-01-24 rag2 kisa_pdf로 KISA JSONL 생성]
        from kisa_pdf import build_kisa_chunks  # type: ignore

        build_kisa_chunks(
            pdf_path=str(kisa_pdf_path),
            label=kisa_label,
            label_to_kisa_category=rag2_constants.LABEL_TO_KISA_CATEGORY,
            kisa_category_keywords_ko=rag2_constants.KISA_CATEGORY_KEYWORDS_KO,
            out_jsonl_path=str(kisa_path),
        )


def get_openai_client() -> OpenAI:
    # [날짜 수정: 2026-01-24 OPENAI_API_KEY 우선 사용, OPEN_API_KEY fallback]
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")
    return OpenAI(api_key=api_key)


def embed_texts(texts: List[str], model: str) -> List[List[float]]:
    client = get_openai_client()
    resp = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in resp.data]


def upsert_documents(collection, docs: List[Dict[str, Any]], model: str, batch_size: int = 128) -> None:
    for i in range(0, len(docs), batch_size):
        batch = docs[i : i + batch_size]
        ids = [d["id"] for d in batch]
        texts = [d["text"] for d in batch]
        metas = [d["meta"] for d in batch]
        embs = embed_texts(texts, model=model)
        collection.upsert(ids=ids, documents=texts, metadatas=metas, embeddings=embs)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Chroma DB from JSONL files.")
    parser.add_argument(
        "--mitre",
        default=str(ROOT / "rag_data" / "mitre_chunks.jsonl"),
        help="Path to MITRE JSONL.",
    )
    parser.add_argument(
        "--kisa",
        default=str(ROOT / "rag_data" / "kisa_chunks.jsonl"),
        help="Path to KISA JSONL.",
    )
    # [날짜 수정: 2026-01-24 JSONL 생성용 CLI 옵션 추가]
    parser.add_argument(
        "--generate-jsonl",
        action="store_true",
        help="Generate MITRE/KISA JSONL before building the DB.",
    )
    # [날짜 수정: 2026-01-24 KISA JSONL 기본 입력값 설정]
    parser.add_argument(
        "--kisa-pdf",
        default=str(ROOT / "module_p" / "0124" / "kisa.pdf"),
        help="Path to KISA PDF for JSONL generation.",
    )
    parser.add_argument(
        "--kisa-label",
        default="DDoS",
        help="Label to tag KISA chunks (required when generating KISA JSONL).",
    )
    parser.add_argument(
        "--skip-mitre",
        action="store_true",
        help="Skip MITRE JSONL generation when --generate-jsonl is used.",
    )
    parser.add_argument(
        "--skip-kisa",
        action="store_true",
        help="Skip KISA JSONL generation when --generate-jsonl is used.",
    )
    parser.add_argument(
        "--no-generate-jsonl",
        action="store_true",
        help="Disable JSONL generation step.",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Base output directory for Chroma DB.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=128,
        help="Embedding/upsert batch size.",
    )
    args = parser.parse_args()

    load_dotenv(dotenv_path=ROOT / ".env", override=False)

    mitre_path = Path(args.mitre)
    kisa_path = Path(args.kisa)

    # [날짜 수정: 2026-01-24 기본값으로 JSONL 생성 수행]
    if args.generate_jsonl or not args.no_generate_jsonl:
        generate_jsonl(
            mitre_path=mitre_path,
            kisa_path=kisa_path,
            kisa_pdf_path=Path(args.kisa_pdf) if args.kisa_pdf else None,
            kisa_label=args.kisa_label,
            skip_mitre=args.skip_mitre,
            skip_kisa=args.skip_kisa,
        )
    if not mitre_path.exists():
        raise FileNotFoundError(f"MITRE JSONL not found: {mitre_path}")
    if not kisa_path.exists():
        raise FileNotFoundError(f"KISA JSONL not found: {kisa_path}")

    if rag2_constants is None:
        collection_mitre = "mitre"
        collection_kisa = "kisa"
        default_out_dir = "."
        chroma_subdir = "chroma_db"
        embed_model = "text-embedding-3-small"
        label_to_kisa_category = None
    else:
        collection_mitre = rag2_constants.COLLECTION_MITRE
        collection_kisa = rag2_constants.COLLECTION_KISA
        default_out_dir = rag2_constants.DEFAULT_OUT_DIR or "."
        chroma_subdir = rag2_constants.DEFAULT_CHROMA_SUBDIR
        embed_model = rag2_constants.DEFAULT_EMBED_MODEL
        label_to_kisa_category = rag2_constants.LABEL_TO_KISA_CATEGORY

    base_dir = args.out_dir or default_out_dir
    chroma_dir = os.path.join(base_dir, chroma_subdir)
    os.makedirs(chroma_dir, exist_ok=True)

    mitre_items = load_jsonl(mitre_path)
    kisa_items = load_jsonl(kisa_path)

    mitre_docs = dedup_docs_by_id(build_mitre_docs(mitre_items))
    kisa_docs = dedup_docs_by_id(build_kisa_docs(kisa_items, label_to_kisa_category=label_to_kisa_category))

    client = chromadb.PersistentClient(path=chroma_dir)
    col_mitre = client.get_or_create_collection(collection_mitre)
    col_kisa = client.get_or_create_collection(collection_kisa)

    upsert_documents(col_mitre, mitre_docs, model=embed_model, batch_size=args.batch_size)
    upsert_documents(col_kisa, kisa_docs, model=embed_model, batch_size=args.batch_size)

    print(f"Chroma DB created at: {chroma_dir}")
    print(f"MITRE docs: {len(mitre_docs)} -> {collection_mitre}")
    print(f"KISA docs: {len(kisa_docs)} -> {collection_kisa}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
