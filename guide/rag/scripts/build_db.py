# JSONL 생성 → 스키마 변환 → Chroma 업서트 파이프라인
import json
import os

from ..configs.constants import LABEL_TO_ATTACK, COLLECTION_KISA_REPORT, COLLECTION_MITRE, COLLECTION_KISA_GUIDE
from ..ingest.mitre_crawl import build_mitre_chunks
from ..ingest.kisa_report import build_kisa_chunks
from ..ingest.kisa_guide import build_kisa_guide_chunks
from ..schema import normalize_mitre, normalize_kisa, normalize_kisa_guide
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
    pdf_path2: str | None = None,
    mitre_jsonl: str = "mitre_chunks.jsonl",
    kisa_report_jsonl: str = "kisa_report_chunks.jsonl",
    kisa_guide_jsonl: str = "kisa_guide_chunks.jsonl",
    mitre_collection: str = COLLECTION_MITRE,
    # NOTE: 기존 코드 호환을 위해 kisa_collection 별칭을 유지
    kisa_report_collection: str = COLLECTION_KISA_REPORT,
    kisa_guide_collection: str = COLLECTION_KISA_GUIDE,
):

    # pdf_path  : KISA "신고절차"(report) PDF
    # pdf_path2 : KISA "대응가이드"(guide) PDF (미지정 시 report PDF로 대체)
    pdf_path2 = pdf_path2 or pdf_path

    # 1) 수집 / 청킹
    mitre_chunks = build_mitre_chunks(LABEL_TO_ATTACK)
    kisa_report_chunks = build_kisa_chunks(pdf_path)
    kisa_guide_chunks = build_kisa_guide_chunks(
        pdf_path=pdf_path2,
        label="DDoS",  
    )

    # 2) JSONL 저장
    mitre_path = save_jsonl(mitre_chunks, os.path.join(out_dir, mitre_jsonl))
    report_path = save_jsonl(kisa_report_chunks, os.path.join(out_dir, kisa_report_jsonl))
    guide_path = save_jsonl(kisa_guide_chunks, os.path.join(out_dir, kisa_guide_jsonl))

    # 3) JSONL 로드
    mitre_items = load_jsonl(mitre_path)
    report_items = load_jsonl(report_path)
    guide_items = load_jsonl(guide_path)

    # 4) 스키마 정규화 + 중복 제거
    docs_mitre = dedup_docs_by_id(normalize_mitre(mitre_items))
    docs_kisa_report = dedup_docs_by_id(normalize_kisa(report_items))
    docs_kisa_guide = dedup_docs_by_id(normalize_kisa_guide(guide_items))

    assert_unique_ids(docs_mitre, "MITRE docs")
    assert_unique_ids(docs_kisa_report, "KISA report docs")
    assert_unique_ids(docs_kisa_guide, "KISA guide docs")

    # 5) Chroma 초기화 + 업서트
    client, col_mitre, col_kisa_report, col_kisa_guide = init_chroma(
        chroma_path,
        mitre_collection=mitre_collection,
        kisa_report_collection=kisa_report_collection,
        kisa_guide_collection=kisa_guide_collection,
    )

    upsert_to_chroma(col_mitre, docs_mitre)
    upsert_to_chroma(col_kisa_report, docs_kisa_report)
    upsert_to_chroma(col_kisa_guide, docs_kisa_guide)

    return client, col_mitre, col_kisa_report, col_kisa_guide
