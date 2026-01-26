# 긴 텍스트를 고정 길이 기준으로 분할
import re

def chunk_text(text: str, max_len: int = 1200) -> list[str]:
    text = (text or "").strip()
    if len(text) <= max_len:
        return [text] if text else []

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = min(len(text), start + max_len)
        chunks.append(text[start:end].strip())
        start = end

    # 빈 문자열 제거
    return [c for c in chunks if c]

def clean_text(text: str) -> str:
    if not text:
        return ""

    # 제어 문자 제거
    text = re.sub(r"[\x00-\x1f\x7f]", " ", text)

    # 여러 공백 → 단일 공백
    text = re.sub(r"[ \t]+", " ", text)

    # 3줄 이상 개행 → 2줄
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()