from __future__ import annotations

import re

from configs.constants import LABEL_NORMALIZE_ALIASES


def normalize_label(label: str) -> str:
    """
    (ipynb에서 그대로 추출한 로직)
    입력 라벨 표기 흔들림을 최대한 흡수해서 정규화한다.

    동작:
    1) 문자열 strip
    2) 별칭(alias) 매핑이 있으면 치환
    3) 공백을 1칸으로 정규화한 뒤(alias 재조회), 없으면 정규화된 문자열 반환
    """
    s = (label or "").strip()
    if not s:
        return s

    # 1) alias 우선 치환
    if s in LABEL_NORMALIZE_ALIASES:
        return LABEL_NORMALIZE_ALIASES[s]

    # 2) 공백/대시 변형 흡수 (ipynb: re.sub(r"\s+", " ", s))
    s2 = re.sub(r"\s+", " ", s)

    return LABEL_NORMALIZE_ALIASES.get(s2, s2)
