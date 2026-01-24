# vectordb/chroma_store.py
from __future__ import annotations

import os
from typing import List, Dict, Any, Optional

import chromadb

from configs.constants import (
    DEFAULT_OUT_DIR,
    DEFAULT_CHROMA_SUBDIR,
    COLLECTION_MITRE,
    COLLECTION_KISA,
)

from vectordb.embeddings import embed_texts


# Chroma 생성
def get_client(out_dir: Optional[str] = None) -> chromadb.PersistentClient:
    base = out_dir or DEFAULT_OUT_DIR
    chroma_dir = os.path.join(base, DEFAULT_CHROMA_SUBDIR)
    os.makedirs(chroma_dir, exist_ok=True)
    return chromadb.PersistentClient(path=chroma_dir)

# MITRE / KISA 컬렉션 생성 or 기존 컬렉션 로드
def get_collections(client: chromadb.PersistentClient):
    col_mitre = client.get_or_create_collection(COLLECTION_MITRE)
    col_kisa = client.get_or_create_collection(COLLECTION_KISA)
    return col_mitre, col_kisa


# schema.py에서 만든 docs를 Chroma에 업서트
def upsert_documents(
    collection,
    docs: List[Dict[str, Any]],
    batch_size: int = 128,
):
    for i in range(0, len(docs), batch_size):
        batch = docs[i : i + batch_size]
        ids = [d["id"] for d in batch]
        texts = [d["text"] for d in batch]
        metas = [d["meta"] for d in batch]
        embs = embed_texts(texts)

        collection.upsert(
            ids=ids,
            documents=texts,
            metadatas=metas,
            embeddings=embs,
        )


# Chroma 검색
def search(
    collection,
    query: str,
    where: Optional[Dict[str, Any]] = None,
    k: int = 5,
):

    q_emb = embed_texts([query])

    res = collection.query(
        query_embeddings=q_emb,
        n_results=k,
        where=where,
    )

    results = []
    for i in range(len(res["ids"][0])):
        results.append(
            {
                "id": res["ids"][0][i],
                "text": res["documents"][0][i],
                "meta": res["metadatas"][0][i],
                "distance": res["distances"][0][i],
            }
        )
    return results