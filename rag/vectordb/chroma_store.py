# Chroma DB 클라이언트 및 업서트 유틸
import chromadb

from .embeddings import embed_texts
from ..configs.constants import COLLECTION_MITRE, COLLECTION_KISA_REPORT, COLLECTION_KISA_GUIDE

# Chroma 클라이언트/컬렉션 초기화
def init_chroma(
    chroma_path: str,
    mitre_collection: str = COLLECTION_MITRE,
    kisa_report_collection: str = COLLECTION_KISA_REPORT,
    kisa_guide_collection : str = COLLECTION_KISA_GUIDE
) -> tuple[object, object, object, object]:
    client = chromadb.PersistentClient(path=chroma_path)
    col_mitre = client.get_or_create_collection(mitre_collection)
    col_kisa_report = client.get_or_create_collection(kisa_report_collection)
    col_kisa_guide = client.get_or_create_collection(kisa_guide_collection)
    return client, col_mitre, col_kisa_report, col_kisa_guide

# 문서를 배치로 임베딩 후 Chroma에 업서트
def upsert_to_chroma(collection: object, docs: list[dict[str, object]], batch_size: int = 128) -> None:
    for i in range(0, len(docs), batch_size):
        b = docs[i : i + batch_size]

        # 업서트 기본 구성요소 추출
        ids = [str(d["id"]) for d in b]
        texts = [str(d.get("text", "")) for d in b]
        metas = [d.get("meta", {}) for d in b]

        # 텍스트 임베딩 (OpenAI embeddings)
        embs = embed_texts(texts)

        # Chroma 업서트
        # collection 타입 힌트를 구체화하려면 chromadb Collection 타입을 직접 import해서 적어도 됨
        collection.upsert(ids=ids, documents=texts, metadatas=metas, embeddings=embs)

