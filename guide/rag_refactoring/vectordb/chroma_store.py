"""Chroma DB 클라이언트 및 업서트 유틸."""
# [날짜 수정: 2026-01-25 Chroma 모듈 분리]
from typing import Any, Dict, List, Tuple

import chromadb

from .embeddings import embed_texts


def init_chroma(
    chroma_path: str,
    mitre_collection: str = "mitre",
    kisa_collection: str = "kisa",
) -> Tuple[Any, Any, Any]:
    """Chroma 클라이언트/컬렉션 초기화."""
    client = chromadb.PersistentClient(path=chroma_path)
    col_mitre = client.get_or_create_collection(mitre_collection)
    col_kisa = client.get_or_create_collection(kisa_collection)
    return client, col_mitre, col_kisa


def upsert_to_chroma(collection, docs: List[Dict[str, Any]], batch_size: int = 128) -> None:
    """문서를 배치로 임베딩 후 Chroma에 업서트."""
    for i in range(0, len(docs), batch_size):
        b = docs[i : i + batch_size]
        ids = [d["id"] for d in b]
        texts = [d["text"] for d in b]
        metas = [d["meta"] for d in b]
        embs = embed_texts(texts)
        collection.upsert(ids=ids, documents=texts, metadatas=metas, embeddings=embs)
