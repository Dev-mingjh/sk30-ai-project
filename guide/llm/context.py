from __future__ import annotations

from typing import Any, Dict, List

from configs.constants import (
    DEFAULT_TOP_K,
    LABEL_TO_KISA_CATEGORY,
    KISA_CATEGORY_KEYWORDS_KO,
)

from utils.normalize import normalize_label
from rag.mitre_rag import search_mitre
from rag.kisa_rag import search_kisa

try:
    from rag.evidence import build_mitre_evidence, build_kisa_evidence  # type: ignore
except Exception:
    build_mitre_evidence = None  # type: ignore
    build_kisa_evidence = None  # type: ignore

def _fallback_build_evidence(hits: List[dict], title_key: str = "title") -> str:
    """
    hits 리스트를 사람이 읽을 수 있는 evidence 텍스트로 변환.
    (hit 구조가 환경마다 조금씩 달라도 최대한 깨지지 않게 작성)
    """
    if not hits:
        return "- (검색 결과 없음)"

    lines: List[str] = []
    for i, h in enumerate(hits, start=1):
        tid = h.get("technique_id") or h.get("technique") or h.get("tid") or ""
        page = h.get("page") or ""
        title = h.get(title_key) or h.get("source_title") or ""
        text = h.get("text") or h.get("content") or h.get("chunk") or ""

        meta_bits = []
        if tid:
            meta_bits.append(str(tid))
        if page:
            meta_bits.append(f"p.{page}")
        if title:
            meta_bits.append(str(title))

        meta = " | ".join(meta_bits).strip()
        if meta:
            lines.append(f"- [{i}] {meta}\n  {text}")
        else:
            lines.append(f"- [{i}] {text}")

    return "\n".join(lines)


def _build_mitre_evidence(mitre_hits: List[dict]) -> str:
    if build_mitre_evidence is not None:
        return build_mitre_evidence(mitre_hits)  # type: ignore
    return _fallback_build_evidence(mitre_hits, title_key="title")

def _build_kisa_evidence(kisa_hits: List[dict]) -> str:
    if build_kisa_evidence is not None:
        return build_kisa_evidence(kisa_hits)  # type: ignore
    return _fallback_build_evidence(kisa_hits, title_key="title")


# 공식 문서 기반 RAG 컨텍스트 생성
def build_attack_context(
    label: str,
    anchors: List[str],
    user_query: str,
    k_mitre: int = DEFAULT_TOP_K,
    k_kisa: int = DEFAULT_TOP_K,
): # -> Dict[str, Any]:
    # 0) 라벨 정규화
    norm_label = normalize_label(label)

    # 1) KISA 상위 카테고리 + 키워드 확장
    category = LABEL_TO_KISA_CATEGORY.get(norm_label, "기타")
    kisa_keywords = KISA_CATEGORY_KEYWORDS_KO.get(category, [])

    # 2) MITRE 검색: anchor technique별로 검색 후 합치기
    mitre_hits: List[dict] = []
    for tid in sorted(set(anchors or [])):
        # 네 search_mitre 시그니처가 search_mitre(query=..., technique_id=..., k=...) 라면 그대로 동작
        # 만약 search_mitre(user_query, ...) 형태라면 여기서 에러가 날 수 있으니 그 경우 함수 시그니처에 맞춰 수정하면 됨
        try:
            mitre_hits.extend(search_mitre(query=user_query, technique_id=tid, k=k_mitre))
        except TypeError:
            mitre_hits.extend(search_mitre(user_query, technique_id=tid, k=k_mitre))  # type: ignore

    # 3) 결과 정렬/슬라이싱
    def _score(h: dict) -> float:
        # distance가 작을수록 유사도가 높은 경우가 일반적
        if "distance" in h:
            return float(h.get("distance") or 1e9)
        # score가 클수록 좋은 구현이면 -score로 정렬
        if "score" in h:
            return -float(h.get("score") or 0.0)
        return 1e9

    mitre_hits.sort(key=_score)
    mitre_hits = mitre_hits[:k_mitre]

    # 4) KISA 검색: 키워드로 쿼리 보강
    kisa_query = user_query
    if kisa_keywords:
        kisa_query = f"{user_query} " + " ".join(kisa_keywords[:6])

    try:
        kisa_hits = search_kisa(query=kisa_query, category=category, k=k_kisa)
    except TypeError:
        kisa_hits = search_kisa(kisa_query, label=norm_label, k=k_kisa)  # type: ignore

    # 5) evidence 문자열 생성
    mitre_evidence = _build_mitre_evidence(mitre_hits)
    kisa_evidence = _build_kisa_evidence(kisa_hits)

    return {
        "label": norm_label,
        "anchors": list(anchors or []),
        "user_query": user_query,
        "kisa_category": category,
        "mitre_hits": mitre_hits,
        "kisa_hits": kisa_hits,
        "mitre_evidence": mitre_evidence,
        "kisa_evidence": kisa_evidence,
    }

