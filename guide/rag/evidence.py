from typing import Any, Dict, List


def build_mitre_evidence(mitre_chunks: List[Dict[str, Any]], max_items: int = 8) -> str:
    if not mitre_chunks:
        return "- 관련 근거를 찾지 못했습니다."

    lines = []
    for c in mitre_chunks[:max_items]:
        meta = c.get("meta", {}) or {}
        tid = meta.get("technique_id", "") or meta.get("tid", "")
        sec = meta.get("section", "") or meta.get("title", "") or meta.get("technique_title", "")
        text = c.get("text", "")

        lines.append(f"- ({tid} / {sec}) {text}".strip())

    return "\n".join(lines) if lines else "- 관련 근거를 찾지 못했습니다."


def build_kisa_evidence(kisa_chunks: List[Dict[str, Any]], max_items: int = 8) :
    if not kisa_chunks:
        return "- 관련 근거를 찾지 못했습니다."

    lines = []
    for c in kisa_chunks[:max_items]:
        meta = c.get("meta", {}) or {}
        pno = meta.get("page_no", "")
        if pno == "":
            pno = meta.get("page", "")
        if pno == "":
            pno = meta.get("pageno", "")

        text = c.get("text", "")
        lines.append(f"- (p.{pno}) {text}".strip())

    return "\n".join(lines) if lines else "- 관련 근거를 찾지 못했습니다."
