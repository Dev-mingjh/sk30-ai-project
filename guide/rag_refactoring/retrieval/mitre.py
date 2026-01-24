"""MITRE 컬렉션 유사도 검색."""
# [날짜 수정: 2026-01-25 MITRE 검색 모듈 분리]
from typing import Any, Dict, List, Optional

from ..vectordb.embeddings import embed_texts


def search_mitre(collection, query: str, technique_id: Optional[str] = None, k: int = 5) -> List[Dict[str, Any]]:
    """MITRE 컬렉션에서 query 유사도 검색."""
    where = {"technique_id": technique_id} if technique_id else None
    q_emb = embed_texts([query])
    res = collection.query(query_embeddings=q_emb, n_results=k, where=where)

    out = []
    for i in range(len(res["ids"][0])):
        out.append(
            {
                "id": res["ids"][0][i],
                "text": res["documents"][0][i],
                "meta": res["metadatas"][0][i],
                "distance": res["distances"][0][i],
            }
        )
    return out
