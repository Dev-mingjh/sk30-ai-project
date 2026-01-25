# KISA PDF 파싱 및 청크 생성
from datetime import datetime, timezone

import fitz  # PyMuPDF

from ..configs.constants import LABEL_KEYWORDS
from ..utils.text import chunk_text

# PDF 페이지 단위로 순회하며 텍스트 추출
def extract_pdf_text_by_page(pdf_path: str) -> list[dict[str, object]]:
    doc = fitz.open(pdf_path)
    pages: list[dict[str, object]] = []

    for pno in range(len(doc)):
        text = doc[pno].get_text("text") or ""
        pages.append(
            {
                "page_no": pno + 1,
                "text": text,
            }
        )

    doc.close()
    return pages

# 페이지 텍스트를 문단 단위로 분리
def split_paragraphs(text: str) -> list[str]:
    parts = [p.strip() for p in (text or "").split("\n\n")]
    return [p for p in parts if len(p) >= 40]


def classify_paragraph(para: str) -> str | None:
    s = (para or "").lower()
    best_label: str | None = None
    best_score = 0

    for label, kws in LABEL_KEYWORDS.items():
        score = sum(1 for k in kws if k.lower() in s)
        if score > best_score:
            best_score = score
            best_label = label

    return best_label if best_score >= 1 else None

# KISA PDF 파일에서 라벨별 청크(JSONL) 생성
def build_kisa_chunks(pdf_path: str) -> list[dict[str, object]]:
    # 1. 페이지별 텍스트 추출
    pages = extract_pdf_text_by_page(pdf_path)

    # 2. 페이지 → 문단 단위로 변환
    paras: list[dict[str, object]] = []
    for p in pages:
        for para in split_paragraphs(str(p["text"])):
            paras.append(
                {
                    "page_no": p["page_no"],
                    "text": para,
                }
            )

    # 3. 문단 라벨 분류
    classified_paragraphs: list[dict[str, object]] = []
    for x in paras:
        lbl = classify_paragraph(str(x["text"]))
        if lbl:
            classified_paragraphs.append(
                {
                    "label": lbl,
                    "page_no": x["page_no"],
                    "text": x["text"],
                }
            )

    # 4. 청킹 및 JSONL 구성
    kisa_chunks: list[dict[str, object]] = []
    retrieved_at = datetime.now(timezone.utc).isoformat()

    for item in classified_paragraphs:
        chunks = chunk_text(str(item["text"]))
        for idx, ch in enumerate(chunks):
            kisa_chunks.append(
                {
                    "source": "KISA",
                    "source_doc": pdf_path,
                    "retrieved_at": retrieved_at,
                    "label": item["label"],
                    "section": "incident_response_guide",
                    "page_no": item["page_no"],
                    "chunk_id": f"KISA:{item['label']}:{item['page_no']}:{idx}",
                    "text": ch,
                }
            )

    return kisa_chunks