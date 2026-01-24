"""KISA PDF 파싱 및 청크 생성.

JSONL 필드:
- source, source_doc, retrieved_at, label, section, page_no, chunk_id, text
"""
# [날짜 수정: 2026-01-25 KISA PDF 파서 모듈 분리]
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF

from ..configs.constants import LABEL_KEYWORDS
from ..utils.text import chunk_text


def extract_pdf_text_by_page(pdf_path: str) -> List[Dict[str, Any]]:
    """PDF 페이지별 텍스트 추출."""
    doc = fitz.open(pdf_path)
    pages = []
    for pno in range(len(doc)):
        text = doc[pno].get_text("text") or ""
        pages.append({"page_no": pno + 1, "text": text})
    doc.close()
    return pages


def split_paragraphs(text: str) -> List[str]:
    """페이지 텍스트를 문단 단위로 분리."""
    parts = [p.strip() for p in (text or "").split("\n\n")]
    return [p for p in parts if len(p) >= 40]


def classify_paragraph(para: str) -> Optional[str]:
    """문단 내 키워드로 라벨을 간단 분류."""
    s = (para or "").lower()
    best_label = None
    best_score = 0
    for label, kws in LABEL_KEYWORDS.items():
        score = sum(1 for k in kws if k.lower() in s)
        if score > best_score:
            best_score = score
            best_label = label
    return best_label if best_score >= 1 else None


def build_kisa_chunks(pdf_path: str) -> List[Dict[str, Any]]:
    """KISA PDF에서 라벨별 청크 JSONL 항목 생성."""
    pages = extract_pdf_text_by_page(pdf_path)
    paras = []
    for p in pages:
        for para in split_paragraphs(p["text"]):
            paras.append({"page_no": p["page_no"], "text": para})

    classified_paragraphs = []
    for x in paras:
        lbl = classify_paragraph(x["text"])
        if lbl:
            classified_paragraphs.append({"label": lbl, "page_no": x["page_no"], "text": x["text"]})

    kisa_chunks: List[Dict[str, Any]] = []
    retrieved_at = datetime.now(timezone.utc).isoformat()
    for item in classified_paragraphs:
        chunks = chunk_text(item["text"])
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
