# 라벨 표기 흔들림을 표준 라벨로 정규화
import re

from ..configs.constants import LABEL_NORMALIZE_ALIASES


def normalize_label(label: str) -> str:
    s = (label or "").strip()
    if not s:
        return s

    if s in LABEL_NORMALIZE_ALIASES:
        return LABEL_NORMALIZE_ALIASES[s]

    s2 = re.sub(r"\s+", " ", s)
    return LABEL_NORMALIZE_ALIASES.get(s2, s2)
