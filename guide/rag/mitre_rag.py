from typing import Any, Dict, List, Optional, Tuple

from vectordb.chroma_store import get_client, get_collections, search


def _get_mitre_collection(out_dir: Optional[str] = None):
    client = get_client(out_dir=out_dir)
    col_mitre, _ = get_collections(client)
    return col_mitre

def search_mitre(
    query: str,
    technique_id: Optional[str] = None,
    k: int = 5,
    out_dir: Optional[str] = None,
    collection=None,
) :
    col = collection or _get_mitre_collection(out_dir=out_dir)
    where = {"technique_id": technique_id} if technique_id else None
    return search(col, query=query, where=where, k=k)