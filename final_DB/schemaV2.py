# -*- coding: utf-8 -*-
"""
schemaV2.py는 "JSONL 한 줄(청크 1개)"을
ChromaDB에 넣기 좋은 형태({id, text, meta})로 바꿔주는 파일입니다.

- mitre_schema: MITRE 청크 변환
- kisa_schema: 신고절차(KISA report process) 청크 변환
- kisa_guide_schema: 대응 가이드(KISA guide) 청크 변환

핵심 포인트:
1) 여기서는 "청크 내용(text)"은 그대로 두고
2) 검색/필터링에 쓸 메타(meta)만 보기 좋게 정리합니다.
"""

from typing import Any, Dict, List

from final_DB.normalizeV2 import normalize_label
from final_DB.constantsV2 import LABEL_TO_KISA_CATEGORY


def mitre_schema(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """MITRE JSONL -> Chroma upsert용 schema로 변환"""
    docs: List[Dict[str, Any]] = []
    for x in items:
        docs.append(
            {
                "id": x["id"],
                "text": x.get("text", ""),
                "meta": {
                    "source": "MITRE",
                    "technique_id": x.get("technique_id", ""),
                    "label": x.get("label", ""),
                    "title": x.get("technique_title", x.get("title", "")),
                    "section": x.get("section", ""),
                },
            }
        )
    return docs


def kisa_schema(items: List[Dict[str, Any]]):
    """KISA 신고절차 JSONL -> Chroma upsert용 schema로 변환"""
    docs: List[Dict[str, Any]] = []
    for x in items:
        raw_label = x.get("label", "")
        norm_label = normalize_label(raw_label) if raw_label else raw_label
        category = LABEL_TO_KISA_CATEGORY.get(norm_label, "기타")

        docs.append(
            {
                "id": x["id"],
                "text": x.get("text", ""),
                "meta": {
                    "source": "KISA_REPORT",
                    "label": norm_label,
                    "kisa_category": category,
                    "section": x.get("section", "incident_response_guide"),
                    "page": x.get("page", x.get("page_no", -1)),
                },
            }
        )
    return docs


def kisa_guide_schema(items: List[Dict[str, Any]]):
    """KISA 대응가이드 JSONL -> Chroma upsert용 schema로 변환"""
    docs: List[Dict[str, Any]] = []
    for x in items:
        raw_label = x.get("label", "")
        norm_label = normalize_label(raw_label) if raw_label else raw_label

        docs.append(
            {
                "id": x["id"],
                "text": x.get("text", ""),
                "meta": {
                    "source": "KISA_GUIDE",
                    "label": norm_label,
                    "section": x.get("section", "kisa_guide_response"),
                    "page": x.get("page", x.get("page_no", -1)),
                },
            }
        )
    return docs
