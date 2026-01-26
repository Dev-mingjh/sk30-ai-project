# 긴 텍스트를 고정 길이 기준으로 분할
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
