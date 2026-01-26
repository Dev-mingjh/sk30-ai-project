# Chroma DB에서 임베딩 검색을 수행하는 Retriever 모듈
import chromadb
from openai import OpenAI

from rag.configs.constants import DEFAULT_EMBED_MODEL, DEFAULT_TOP_K
from rag.configs.env import get_openai_api_key

# Chroma where 필터 정규화
def normalize_where(where: dict[str, object] | None) -> dict[str, object] | None:
    if not where:
        return None
    if any(isinstance(k, str) and k.startswith("$") for k in where.keys()):
        return where
    if len(where) == 1:
        return where
    return {"$and": [{k: v} for k, v in where.items()]}

# query -> 임베딩 -> Chroma 검색 -> contexts 반환
class ChromaRetriever:
    def __init__(
        self,
        chroma_dir: str,
        collection_name: str,
        embed_model: str = DEFAULT_EMBED_MODEL,
    ):
        self.chroma_dir = chroma_dir
        self.collection_name = collection_name
        self.embed_model = embed_model

        api_key = get_openai_api_key()
        if not api_key:
            raise ValueError("OPENAI_API_KEY(또는 OPEN_API_KEY)가 .env에 설정되어 있지 않습니다.")

        self.openai = OpenAI(api_key=api_key)
        self.client = chromadb.PersistentClient(path=chroma_dir)
        # 컬렉션이 아직 없을 수 있으므로 get_or_create를 사용해 NotFoundError 방지
        self.col = self.client.get_or_create_collection(collection_name)

    def embed_query(self, query: str) -> list[float]:
        emb = self.openai.embeddings.create(model=self.embed_model, input=query)
        return emb.data[0].embedding

    def retrieve(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        where: dict[str, object] | None = None,
        fallback: bool = True,
    ) -> list[dict[str, object]]:
        q_emb = self.embed_query(query)

        def _query(w: dict[str, object] | None) -> dict:
            return self.col.query(
                query_embeddings=[q_emb],
                n_results=top_k,
                where=normalize_where(w),
                include=["documents", "metadatas", "distances"],
            )

        res = _query(where)

        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]

        # fallback: 결과가 비어있으면 where를 완화
        if fallback and len(docs) == 0 and where:
            # 1) section 제거
            w2 = dict(where)
            w2.pop("section", None)
            res = _query(w2)

            docs = (res.get("documents") or [[]])[0]
            metas = (res.get("metadatas") or [[]])[0]
            dists = (res.get("distances") or [[]])[0]

        contexts: list[dict[str, object]] = []
        for d, m, dist in zip(docs, metas, dists):
            contexts.append({"text": d, "metadata": m or {}, "distance": dist})
        return contexts
