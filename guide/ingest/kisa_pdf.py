import json
import re
from typing import Dict, List, Optional

import fitz  # PyMuPDF

from utils.text import clean_text
from configs.constants import CHUNK_SIZE, CHUNK_OVERLAP

# PDF 파일을 '페이지'단위로 텍스트 추출
def extract_pdf_text_by_page(pdf_path: str): # -> List[dict]:
    doc = fitz.open(pdf_path)
    pages = []
    for i in range(len(doc)):
        text = doc.load_page(i).get_text(" ")
        pages.append({"page": i + 1, "text": _clean_text(text)})
    doc.close()
    return pages

# 한 페이지 내 텍스트를 문단 단위로 1차 분리
# 분리 기준:
# 1) 연속된 줄바꿈 2개 이상 (\n\n)
# 2) 글머리 기호(•, ●)를 기준으로 분리하며, 기호는 제거
def split_paragraphs(text: str, min_len: int = 40): # -> List[str]:
    parts = re.split(r"(?:\n{2,}|\r\n{2,}|[•●]\s+)", text)
    paras = []
    for p in parts:
        p = clean_text(p)
        
        # 너무 짧은 조각(ex.제목만 있는 경우)은 의미 정보가 부족하므로 제외
        if len(p) >= min_len: 
            paras.append(p)
    return paras

# 문단도 길 수 있기 때문에 
# 최종적으로 RAG에 적합한 'chunk' 단위로 분할
def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP): # -> List[str]:
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        ch = text[start:end].strip()
        if ch:
            chunks.append(ch)
        if end == n:
            break
        start = max(0, end - overlap)
    return chunks

# 카테고리 키워드 기반 분류
# 1) 가장 많이 매칭되는 카테고리를 반환
# 2) 매칭이 없으면 None
def classify_paragraph(paragraph: str, category_keywords: Dict[str, List[str]]): #-> Optional[str]:
    scores = {}
    p_lower = paragraph.lower()

    for category, kws in category_keywords.items():
        score = 0
        for kw in kws:
            if kw.lower() in p_lower:
                score += 1
        scores[category] = score

    best_cat = max(scores, key=scores.get) if scores else None
    if best_cat and scores[best_cat] > 0:
        return best_cat
    return None

# PDF에서 VectorDB에 넣을 'Chunk 문서' 생성 후 JSONL로 저장
def build_kisa_chunks(
    pdf_path: str,
    label: str,
    label_to_kisa_category: Dict[str, str],
    kisa_category_keywords_ko: Dict[str, List[str]],
    out_jsonl_path: str,
): # -> List[dict]:
    pages = extract_pdf_text_by_page(pdf_path)

    target_category = label_to_kisa_category.get(label)
    if not target_category:
        target_category = "기타"

    all_docs: List[dict] = []
    idx = 0

    for p in pages:
        page_no = p["page"]
        paras = split_paragraphs(p["text"])

        for para in paras:
            # 문단이 어떤 카테고리인지
            cat = classify_paragraph(para, kisa_category_keywords_ko) or "기타"

            chunks = chunk_text(para)
            for ch in chunks:
                all_docs.append(
                    {
                        "id": f"kisa::{label}::p{page_no}::{idx}",
                        "source": "kisa",
                        "label": label,
                        "kisa_category": cat,
                        "page": page_no,
                        "text": ch,
                    }
                )
                idx += 1

    save_jsonl(all_docs, out_jsonl_path)
    return all_docs

# 생성된 chunk 문서를 JSONL로 저장
def save_jsonl(items: List[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
