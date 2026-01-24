import re

# PDF에서 추출한, 크롤링으로 수집한 원본 텍스트를
# 임베딩/검색에 적합하도록 한 줄의 정제된 텍스트로 변환
def clean_text(text):
    if text is None:
        return ""

    # 문자열 보장
    text = str(text)

    # 제어문자(탭/줄바꿈 제외) 제거
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)

    # 줄바꿈 정리: 너무 많은 줄바꿈은 2개로 축소
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 공백 정리
    text = re.sub(r"[ \t]{2,}", " ", text)

    return text.strip()
