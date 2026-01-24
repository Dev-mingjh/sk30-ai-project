# Chroma DB에서 임베딩 검색을 수행하는 Retriever 모듈
import os
from typing import Any, Dict, List, Optional

import chromadb
from openai import OpenAI


def _normalize_where(where: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not where:
        return None
    # 이미 연산자 형태면 그대로
    if any(k.startswith("$") for k in where.keys()):
        return where
    # 단일 키면 그대로
    if len(where) == 1:
        return where
    # 다중 키면 $and로 감싸기
    return {"$and": [{k: v} for k, v in where.items()]}

class ChromaRetriever:
    """
    - 역할: query -> 임베딩 -> Chroma 검색 -> contexts 반환
    - contexts 형태:
      [{"text": "...", "metadata": {...}, "distance": 0.12}, ...]
    """

    def __init__(
        self,
        chroma_dir: str,
        collection_name: str,
        embed_model: str = "text-embedding-3-small",
        api_key_envs: tuple[str, ...] = ("OPENAI_API_KEY", "OPEN_API_KEY"),
    ):
        self.chroma_dir = chroma_dir
        self.collection_name = collection_name
        self.embed_model = embed_model

        api_key = None
        for k in api_key_envs:
            api_key = os.getenv(k)
            if api_key:
                break
        if not api_key:
            raise ValueError("OPENAI_API_KEY(또는 OPEN_API_KEY)가 설정되어 있지 않습니다.")

        self.oai = OpenAI(api_key=api_key)
        self.client = chromadb.PersistentClient(path=chroma_dir)
        self.col = self.client.get_collection(collection_name)

    def embed_query(self, query: str) -> List[float]:
        return self.oai.embeddings.create(model=self.embed_model, input=query).data[0].embedding

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        where: Optional[Dict[str, Any]] = None,
        fallback: bool = True,
    ) -> List[Dict[str, Any]]:
        q_emb = self.embed_query(query)

        def _query(w: Dict[str, Any]) -> dict:
            return self.col.query(
                query_embeddings=[q_emb],
                n_results=top_k,
                where=_normalize_where(w),
                include=["documents", "metadatas", "distances"],
            )

        where = where or {}
        res = _query(where)

        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]

        # fallback: 결과가 비어있으면 where를 완화
        if fallback and len(docs) == 0 and where:
            # 1) section 제거
            w2 = dict(where)
            w2.pop("section", None)
            res = _query(w2)
            docs = res.get("documents", [[]])[0]
            metas = res.get("metadatas", [[]])[0]
            dists = res.get("distances", [[]])[0]

        contexts = []
        for d, m, dist in zip(docs, metas, dists):
            contexts.append({"text": d, "metadata": m or {}, "distance": dist})
        return contexts
