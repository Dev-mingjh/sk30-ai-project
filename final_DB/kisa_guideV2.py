# -*- coding: utf-8 -*-
"""
kisa_guide.pdf 전용 인제스트 로직.
- 목표: 대응 방안/초동 대응 블록만 추출해 청크로 저장
- 규칙:
  1) 시작 조건: 대응 방안/대응방법/대응 절차/초동 대응 등
  2) 종료 조건: PART, 제N장, 참고사항/신고/문의처 등
  3) 시작~종료 사이에서만 청크 생성
  4) 번호/불릿(1., ①, 가., -) 기준으로 먼저 분할 후 길이 분할
"""

import json
import re
from datetime import datetime, timezone
from typing import List

import fitz  # PyMuPDF

# final_DB는 패키지가 아닐 수 있어 상대경로 대신 V2 모듈명을 직접 사용
from final_DB.textV2 import clean_text
from final_DB.constantsV2 import CHUNK_SIZE, CHUNK_OVERLAP

# 시작/종료 조건은 정규식으로 관리 (문서 형식이 조금 달라도 견고하게 동작)
START_RE = re.compile(r"(대응\s*방안|대응\s*방법|대응\s*절차|초동\s*대응|초동대응)")
END_RE = re.compile(r"(PART\s*\d+|제\s*\d+\s*장|참고사항|침해사고\s*신고|신고방법|피해지원|문의처)")

# 조치 단위 분할에 쓰는 라인 시작 패턴
ACTION_LINE_RE = re.compile(r"^\s*(\d+\.|[①-⑳]|[가-하]\.|[-*•])\s+")


def extract_pdf_text_by_page(pdf_path: str) -> List[dict]:
    doc = fitz.open(pdf_path)
    pages = []
    for i in range(len(doc)):
        text = doc.load_page(i).get_text("text")
        pages.append({"page": i + 1, "text": clean_text(text)})
    doc.close()
    return pages


def split_paragraphs(text: str, min_len: int = 40) -> List[str]:
    parts = re.split(r"(?:\n{2,}|\r\n{2,})", text)
    paras = []
    for p in parts:
        p = clean_text(p)
        # 페이지 번호처럼 보이는 단독 숫자 줄은 제외
        if re.fullmatch(r"\d{1,3}", p):
            continue
        if len(p) >= min_len:
            paras.append(p)
    return paras


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
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


def split_by_action_markers(text: str) -> List[str]:
    """번호/불릿 라인 기준으로 먼저 분할해 조치 단위를 살린다."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []

    blocks: List[str] = []
    current: List[str] = []

    def flush():
        if current:
            blocks.append("\n".join(current).strip())
            current.clear()

    for ln in lines:
        if ACTION_LINE_RE.match(ln) and current:
            flush()
        current.append(ln)

    flush()
    return blocks


def build_kisa_guide_chunks(pdf_path: str, label: str, out_jsonl_path: str) -> List[dict]:
    pages = extract_pdf_text_by_page(pdf_path)
    retrieved_at = datetime.now(timezone.utc).isoformat()

    all_docs: List[dict] = []
    idx = 0
    in_guide_block = False

    for p in pages:
        page_no = p["page"]
        paras = split_paragraphs(p["text"])

        for para in paras:
            # 시작/종료 조건 체크로 "대응 방안" 구간만 선택
            if END_RE.search(para):
                in_guide_block = False
            if START_RE.search(para):
                in_guide_block = True

            if not in_guide_block:
                continue

            # 조치 단위로 먼저 나눈 뒤, 길면 추가 분할
            action_blocks = split_by_action_markers(para) or [para]
            for block in action_blocks:
                for ch in chunk_text(block):
                    chunk_id = f"KISA_GUIDE:{label}:{page_no}:{idx}"
                    all_docs.append(
                        {
                            "id": chunk_id,
                            "source": "KISA",
                            "source_doc": pdf_path,
                            "retrieved_at": retrieved_at,
                            "label": label,
                            "section": "kisa_guide_response",
                            "page_no": page_no,
                            "chunk_id": chunk_id,
                            "text": ch,
                            "page": page_no,
                        }
                    )
                    idx += 1

    save_jsonl(all_docs, out_jsonl_path)
    return all_docs


def save_jsonl(items: List[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
