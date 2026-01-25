# -*- coding: utf-8 -*-

"""
0125 DB 3개 생성 코드 / 모듈은 final_DB dir의 모듈들 사용
build_dbV2.py: final_DB 기준으로 ChromaDB를 빌드하는 실행 스크립트.
- MITRE / KISA 신고절차 / KISA 대응가이드 JSONL 생성
- JSONL -> schema 변환 -> Chroma upsert 연결
DB 3개(mitre, report, guide DB 생성함)
"""

import argparse
import json
import os
from typing import Any, Dict, List

from final_DB.constantsV2 import (
    DEFAULT_OUT_DIR,
    LABEL_TO_ATTACK,
    LABEL_TO_KISA_CATEGORY,
    KISA_CATEGORY_KEYWORDS_KO,
)
from final_DB.chroma_storeV2 import get_client, get_collections, upsert_documents
from final_DB.mitre_crawlV2 import build_mitre_chunks
from final_DB.kisa_pdfV2 import build_kisa_chunks
from final_DB.kisa_guideV2 import build_kisa_guide_chunks
from final_DB.schemaV2 import mitre_schema, kisa_schema, kisa_guide_schema


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def dedup_docs_by_id(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: Dict[str, Dict[str, Any]] = {}
    for d in docs:
        deduped[d["id"]] = d
    return list(deduped.values())


def resolve_pdf_paths(report_pdf: str | None, guide_pdf: str | None) -> tuple[str, str]:
    base = "final_DB"
    guide = guide_pdf or os.path.join(base, "kisa_guide.pdf")

    if not os.path.exists(guide):
        raise FileNotFoundError(f"KISA guide PDF not found: {guide}")

    if report_pdf and os.path.exists(report_pdf):
        return report_pdf, guide

    # ???? PDF? guide? ?? ?? PDF? ?? ??
    candidates = [p for p in sorted(os.listdir(base)) if p.lower().endswith(".pdf")]
    candidates = [os.path.join(base, p) for p in candidates if p != os.path.basename(guide)]
    if not candidates:
        raise FileNotFoundError("KISA report PDF not found. Pass --kisa-report-pdf explicitly.")
    return candidates[0], guide


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ChromaDB with final_DB V2 modules")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR or ".", help="output directory for JSONL")
    parser.add_argument("--mitre-jsonl", default="mitre_chunksV2.jsonl")
    parser.add_argument("--kisa-report-pdf", default=None)
    parser.add_argument("--kisa-report-jsonl", default="kisa_report_chunksV2.jsonl")
    parser.add_argument("--kisa-guide-pdf", default=None)
    parser.add_argument("--kisa-guide-jsonl", default="kisa_guide_chunksV2.jsonl")
    parser.add_argument("--label", default="DDoS", help="label for KISA PDFs")
    args = parser.parse_args()

    args.kisa_report_pdf, args.kisa_guide_pdf = resolve_pdf_paths(args.kisa_report_pdf, args.kisa_guide_pdf)

    ensure_dir(args.out_dir)

    mitre_jsonl_path = os.path.join(args.out_dir, args.mitre_jsonl)
    kisa_report_jsonl_path = os.path.join(args.out_dir, args.kisa_report_jsonl)
    kisa_guide_jsonl_path = os.path.join(args.out_dir, args.kisa_guide_jsonl)

    # 1) JSONL 생성
    build_mitre_chunks(LABEL_TO_ATTACK, mitre_jsonl_path)
    build_kisa_chunks(
        pdf_path=args.kisa_report_pdf,
        label=args.label,
        label_to_kisa_category=LABEL_TO_KISA_CATEGORY,
        kisa_category_keywords_ko=KISA_CATEGORY_KEYWORDS_KO,
        out_jsonl_path=kisa_report_jsonl_path,
    )
    build_kisa_guide_chunks(
        pdf_path=args.kisa_guide_pdf,
        label=args.label,
        out_jsonl_path=kisa_guide_jsonl_path,
    )

    # 2) JSONL 로드 -> schema 변환
    mitre_docs = dedup_docs_by_id(mitre_schema(load_jsonl(mitre_jsonl_path)))
    kisa_report_docs = dedup_docs_by_id(kisa_schema(load_jsonl(kisa_report_jsonl_path)))
    kisa_guide_docs = dedup_docs_by_id(kisa_guide_schema(load_jsonl(kisa_guide_jsonl_path)))

    # 3) Chroma upsert
    client = get_client(out_dir=args.out_dir)
    col_mitre, col_kisa_report, col_kisa_guide = get_collections(client)
    upsert_documents(col_mitre, mitre_docs)
    upsert_documents(col_kisa_report, kisa_report_docs)
    upsert_documents(col_kisa_guide, kisa_guide_docs)

    print(f"[DONE] mitre={len(mitre_docs)} report={len(kisa_report_docs)} guide={len(kisa_guide_docs)}")


if __name__ == "__main__":
    main()
