
from typing import Dict, List, Any

from utils.normalize import normalize_label
from configs.constants import LABEL_TO_KISA_CATEGORY

# MITRE JSONL -> Chroma upsert용 schema로 변환 
def mitre_schema(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    docs = []
    for x in items:
        docs.append(
            {
                "id": x["id"],
                "text": x.get("text", ""),
                "meta": {
                    "source": "MITRE",
                    "technique_id": x.get("technique_id", ""),
                    "label": x.get("label", ""),
                    "title": x.get("title", ""),
                },
            }
        )
    return docs

# KISA JSONL -> Chroma upsert용 schema 변환
def kisa_schema(items: List[Dict[str, Any]]):
    docs = []
    for x in items:
        raw_label = x.get("label", "")
        norm_label = normalize_label(raw_label) if raw_label else raw_label
        category = LABEL_TO_KISA_CATEGORY.get(norm_label, "기타")

        docs.append(
            {
                "id": x["id"],
                "text": x.get("text", ""),
                "meta": {
                    "source": "KISA",
                    "label": norm_label,
                    "kisa_category": category,
                    "page": x.get("page", -1),
                },
            }
        )
    return docs
