"""JSONL → Chroma 업서트 스키마 변환.

MITRE meta 필드:
- source, technique_id, technique_title, section, labels_csv, mitigation_id, mitigation_name, source_url

KISA meta 필드:
- source, label, kisa_category, section, page_no, source_doc
"""
# [날짜 수정: 2026-01-25 스키마 변환 모듈 분리]
from typing import Any, Dict, List

from .configs.constants import LABEL_TO_KISA_CATEGORY
from .utils.normalize import normalize_label


def normalize_mitre(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """MITRE JSONL을 Chroma 업서트용 docs로 변환."""
    docs = []
    for x in items:
        labels = x.get("labels")
        if labels is None:
            labels = x.get("label")
        if isinstance(labels, list):
            labels_csv = ",".join(labels)
        elif labels:
            labels_csv = str(labels)
        else:
            labels_csv = ""

        docs.append(
            {
                "id": x["chunk_id"],
                "text": x.get("text", ""),
                "meta": {
                    "source": "MITRE_ATT&CK",
                    "technique_id": x.get("technique_id", ""),
                    "technique_title": x.get("technique_title", ""),
                    "section": x.get("section", ""),
                    "labels_csv": labels_csv,
                    "mitigation_id": x.get("mitigation_id", ""),
                    "mitigation_name": x.get("mitigation_name", ""),
                    "source_url": x.get("source_url", ""),
                },
            }
        )
    return docs


def normalize_kisa(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """KISA JSONL을 Chroma 업서트용 docs로 변환."""
    docs = []
    for x in items:
        raw_label = x.get("label", "")
        norm_label = normalize_label(raw_label) if raw_label else raw_label
        kisa_category = LABEL_TO_KISA_CATEGORY.get(norm_label, "기타")
        docs.append(
            {
                "id": x["chunk_id"],
                "text": x.get("text", ""),
                "meta": {
                    "source": "KISA",
                    "label": norm_label,
                    "kisa_category": kisa_category,
                    "section": x.get("section", ""),
                    "page_no": int(x.get("page_no", -1)) if str(x.get("page_no", "-1")).isdigit() else -1,
                    "source_doc": x.get("source_doc", ""),
                },
            }
        )
    return docs
