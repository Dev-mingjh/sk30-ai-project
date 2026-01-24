from typing import Any, Dict, List, Optional

from vectordb.chroma_store import get_client, get_collections, search


def _get_kisa_collection(out_dir: Optional[str] = None):
    client = get_client(out_dir=out_dir)
    _, col_kisa = get_collections(client)
    return col_kisa


def search_kisa(
    query: str,
    category: Optional[str] = None,
    label: Optional[str] = None,
    k: int = 5,
    out_dir: Optional[str] = None,
    collection=None,
):
    col = collection or _get_kisa_collection(out_dir=out_dir)

    where = None
    if category:
        where = {"kisa_category": category}
    elif label:
        where = {"label": label}

    return search(col, query=query, where=where, k=k)
