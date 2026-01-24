"""검색 결과를 evidence 문자열로 구성."""
# [날짜 수정: 2026-01-25 evidence 생성 모듈 분리]
from typing import Any, Dict, List


def build_mitre_evidence(mitre_chunks: List[Dict[str, Any]], max_items: int = 8) -> str:
    """MITRE 검색 결과를 근거 문자열로 변환."""
    lines = []
    for c in mitre_chunks[:max_items]:
        meta = c.get("meta", {})
        tid = meta.get("technique_id", "")
        sec = meta.get("section", "")
        lines.append(f"- ({tid} / {sec}) {c.get('text', '')}")
    return "\n".join(lines) if lines else "- 관련 근거를 찾지 못했습니다."


def build_kisa_evidence(kisa_chunks: List[Dict[str, Any]], max_items: int = 8) -> str:
    """KISA 검색 결과를 근거 문자열로 변환."""
    lines = []
    for c in kisa_chunks[:max_items]:
        meta = c.get("meta", {})
        pno = meta.get("page_no", "")
        lines.append(f"- (p.{pno}) {c.get('text', '')}")
    return "\n".join(lines) if lines else "- 관련 근거를 찾지 못했습니다."
