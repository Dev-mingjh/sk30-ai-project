# JSONL 생성 → 스키마 변환 → Chroma 업서트 파이프라인
import json
import os

from ..configs.constants import LABEL_TO_ATTACK, COLLECTION_KISA, COLLECTION_MITRE
from ..ingest.mitre_crawl import build_mitre_chunks
from ..ingest.kisa_pdf import build_kisa_chunks
from ..schema import normalize_mitre, normalize_kisa
from ..vectordb.chroma_store import init_chroma, upsert_to_chroma

# 리스트(dict)를 JSONL 파일로 저장
def save_jsonl(items: list[dict[str, object]], path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for x in items:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    return path

# JSONL 파일을 리스트(dict)로 로드
def load_jsonl(path: str) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items

# 문서 ID 중복 제거(마지막 항목 유지
def dedup_docs_by_id(docs: list[dict[str, object]]) -> list[dict[str, object]]:
    m: dict[str, dict[str, object]] = {}
    for d in docs:
        m[str(d["id"])] = d
    return list(m.values())

# 중복 ID 요약 및 목록 반환
def assert_unique_ids(docs: list[dict[str, object]], name: str = "docs") -> list[str]:
    from collections import Counter

    ids = [str(d["id"]) for d in docs]
    dup = [k for k, v in Counter(ids).items() if v > 1]
    print(f"[{name}] total={len(ids)} unique={len(set(ids))} dups={len(dup)}")
    if dup:
        print("예시 dup ids:", dup[:10])
    return dup

# 수집 → JSONL 저장 → JSONL 로드 → 스키마 정규화 → Chroma 업서트까지 전체 파이프라인 실행
def build_vector_db(
    pdf_path: str,
    out_dir: str,
    chroma_path: str,
    mitre_jsonl: str = "mitre_chunks.jsonl",
    kisa_jsonl: str = "kisa_chunks.jsonl",
    mitre_collection: str = COLLECTION_MITRE,  
    kisa_collection: str = COLLECTION_KISA,    
) -> tuple[object, object, object]:
    # 1) 수집/청킹
    mitre_chunks = build_mitre_chunks(LABEL_TO_ATTACK)
    kisa_chunks = build_kisa_chunks(pdf_path)

    # 2) JSONL 저장
    mitre_jsonl_path = save_jsonl(mitre_chunks, os.path.join(out_dir, mitre_jsonl))
    kisa_jsonl_path = save_jsonl(kisa_chunks, os.path.join(out_dir, kisa_jsonl))

    # 3) JSONL 로드
    mitre_items = load_jsonl(mitre_jsonl_path)
    kisa_items = load_jsonl(kisa_jsonl_path)

    # 4) 스키마 정규화 + 중복 제거
    docs_mitre = dedup_docs_by_id(normalize_mitre(mitre_items))
    docs_kisa = dedup_docs_by_id(normalize_kisa(kisa_items))

    # (선택) 중복 ID 체크 로그
    assert_unique_ids(docs_mitre, name="MITRE docs")
    assert_unique_ids(docs_kisa, name="KISA docs")

    # 5) Chroma 초기화 + 업서트
    client, col_mitre, col_kisa = init_chroma(
        chroma_path,
        mitre_collection=mitre_collection,
        kisa_collection=kisa_collection,
    )
    upsert_to_chroma(col_mitre, docs_mitre)
    upsert_to_chroma(col_kisa, docs_kisa)

    return client, col_mitre, col_kisa
