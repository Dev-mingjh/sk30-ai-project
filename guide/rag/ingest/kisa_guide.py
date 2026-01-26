# KISA 대응가이드 PDF 파싱 및 청크 생성
import json
import re
from datetime import datetime, timezone

import fitz  # PyMuPDF

from ..configs.constants import CHUNK_SIZE, CHUNK_OVERLAP
from ..utils.text import clean_text

# 시작/종료 조건 정규식 (문서 형식이 조금 달라도 견고하게)
START_RE = re.compile(r"(대응\s*방안|대응\s*방법|대응\s*절차|초동\s*대응|초동대응)")
END_RE = re.compile(r"(PART\s*\d+|제\s*\d+\s*장|참고사항|침해사고\s*신고|신고방법|피해지원|문의처)")

# 조치 단위 분할(번호/불릿) 라인 시작 패턴
ACTION_LINE_RE = re.compile(r"^\s*(\d+\.|[①-⑳]|[가-하]\.|[-*•])\s+")

# PDF를 페이지 단위로 텍스트 추출
def extract_pdf_text_by_page(pdf_path: str) -> list[dict]:
    doc = fitz.open(pdf_path)
    pages: list[dict] = []
    try:
        for i in range(len(doc)):
            text = doc.load_page(i).get_text("text") or ""
            pages.append({"page_no": i + 1, "text": clean_text(text)})
    finally:
        doc.close()
    return pages

# 페이지 텍스트를 문단 단위로 분리
def split_paragraphs(text: str, min_len: int = 40) -> list[str]:
    parts = re.split(r"(?:\n{2,}|\r\n{2,})", text or "")
    paras: list[str] = []
    for p in parts:
        p = clean_text(p)
        # 페이지 번호처럼 보이는 단독 숫자 줄은 제외
        if re.fullmatch(r"\d{1,3}", p):
            continue
        if len(p) >= min_len:
            paras.append(p)
    return paras

# 고정 길이 기준 청크 분할
def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    t = (text or "").strip()
    if not t:
        return []

    chunks: list[str] = []
    start = 0
    n = len(t)
    while start < n:
        end = min(start + chunk_size, n)
        ch = t[start:end].strip()
        if ch:
            chunks.append(ch)
        if end == n:
            break
        start = max(0, end - overlap)
    return chunks

# 번호/불릿 라인 기준으로 분할해 조치 단위를 살린다
def split_by_action_markers(text: str) -> list[str]:
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    if not lines:
        return []

    blocks: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            blocks.append("\n".join(current).strip())
            current.clear()

    for ln in lines:
        # 새 조치 시작(번호/불릿) 발견 시 이전 블록 flush
        if ACTION_LINE_RE.match(ln) and current:
            flush()
        current.append(ln)

    flush()
    return blocks


def save_jsonl(items: list[dict], path: str) -> None:
    """리스트를 JSONL로 저장."""
    with open(path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

# KISA 가이드 PDF에서 '대응 방안/초동 대응' 구간만 추출하여 청크 JSONL 항목 생성
def build_kisa_guide_chunks(
    pdf_path: str,
    label: str,
    out_jsonl_path: str | None = None,
    section: str = "kisa_guide_response",
) -> list[dict]:
    pages = extract_pdf_text_by_page(pdf_path)
    retrieved_at = datetime.now(timezone.utc).isoformat()

    all_items: list[dict] = []
    idx = 0
    in_guide_block = False

    for p in pages:
        page_no = int(p.get("page_no", -1))
        paras = split_paragraphs(p.get("text", ""))

        for para in paras:
            # 종료 조건이 먼저 나오면 블록 종료
            if END_RE.search(para):
                in_guide_block = False

            # 시작 조건이 나오면 블록 시작
            if START_RE.search(para):
                in_guide_block = True

            if not in_guide_block:
                continue

            # 조치 단위로 먼저 나눈 뒤, 길면 추가 분할
            action_blocks = split_by_action_markers(para) or [para]
            for block in action_blocks:
                for ch in chunk_text(block):
                    chunk_id = f"KISA_GUIDE:{label}:{page_no}:{idx}"
                    all_items.append(
                        {
                            "source": "KISA",
                            "source_doc": pdf_path,
                            "retrieved_at": retrieved_at,
                            "label": label,
                            "section": section,
                            "page_no": page_no,
                            "chunk_id": chunk_id,
                            "text": ch,
                        }
                    )
                    idx += 1

    if out_jsonl_path:
        save_jsonl(all_items, out_jsonl_path)

    return all_items
