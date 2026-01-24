"""텍스트 유틸 (chunk 분할)."""
# [날짜 수정: 2026-01-25 텍스트 유틸 분리]
from typing import List


def chunk_text(text: str, max_len: int = 1200) -> List[str]:
    """긴 텍스트를 고정 길이 기준으로 분할."""
    text = (text or "").strip()
    if len(text) <= max_len:
        return [text] if text else []
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_len)
        chunks.append(text[start:end].strip())
        start = end
    return [c for c in chunks if c]
