"""JSONL 생성 → 스키마 변환 → Chroma 업서트 파이프라인.

입력 JSONL 필드 (MITRE/KISA): ingest 모듈 기준
출력 meta 스키마: schema.py 참고
"""
# [날짜 수정: 2026-01-25 DB 빌드 스크립트 분리]
import json
import os
from typing import Any, Dict, List, Tuple

from ..configs.constants import label_to_attack
from ..ingest.mitre_crawl import build_mitre_chunks
from ..ingest.kisa_pdf import build_kisa_chunks
from ..schema import normalize_mitre, normalize_kisa
from ..vectordb.chroma_store import init_chroma, upsert_to_chroma


def save_jsonl(items: List[Dict[str, Any]], path: str) -> str:
    """리스트를 JSONL로 저장."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for x in items:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    return path


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    """JSONL 파일을 리스트로 로드."""
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def dedup_docs_by_id(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """문서 ID 중복 제거(마지막 항목 유지)."""
    m: Dict[str, Dict[str, Any]] = {}
    for d in docs:
        m[d["id"]] = d
    return list(m.values())


def assert_unique_ids(docs: List[Dict[str, Any]], name: str = "docs") -> List[str]:
    """중복 ID 요약 및 목록 반환."""
    from collections import Counter

    ids = [d["id"] for d in docs]
    dup = [k for k, v in Counter(ids).items() if v > 1]
    print(f"[{name}] total={len(ids)} unique={len(set(ids))} dups={len(dup)}")
    if dup:
        print("예시 dup ids:", dup[:10])
    return dup


def build_vector_db(
    pdf_path: str,
    out_dir: str,
    chroma_path: str,
    mitre_jsonl: str = "mitre_chunks.jsonl",
    kisa_jsonl: str = "kisa_chunks.jsonl",
    mitre_collection: str = "mitre",
    kisa_collection: str = "kisa",
) -> Tuple[Any, Any, Any]:
    """수집 → 저장 → 정규화 → 업서트까지 전체 파이프라인 실행."""
    mitre_chunks = build_mitre_chunks(label_to_attack)
    kisa_chunks = build_kisa_chunks(pdf_path)

    mitre_jsonl_path = save_jsonl(mitre_chunks, os.path.join(out_dir, mitre_jsonl))
    kisa_jsonl_path = save_jsonl(kisa_chunks, os.path.join(out_dir, kisa_jsonl))

    mitre_items = load_jsonl(mitre_jsonl_path)
    kisa_items = load_jsonl(kisa_jsonl_path)

    docs_mitre = dedup_docs_by_id(normalize_mitre(mitre_items))
    docs_kisa = dedup_docs_by_id(normalize_kisa(kisa_items))

    client, col_mitre, col_kisa = init_chroma(chroma_path, mitre_collection, kisa_collection)
    upsert_to_chroma(col_mitre, docs_mitre)
    upsert_to_chroma(col_kisa, docs_kisa)

    return client, col_mitre, col_kisa
