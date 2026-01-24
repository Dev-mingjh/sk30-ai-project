"""MITRE ATT&CK 크롤링 및 청크 생성.

JSONL 필드:
- source, retrieved_at, label, technique_id, technique_title, section, chunk_id, text, source_url
"""
# [날짜 수정: 2026-01-25 MITRE 크롤링 모듈 분리]
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup

from ..configs.constants import BASE_MITRE_URL
from ..utils.text import chunk_text


def fetch_technique_text(technique_id: str, base_url: str = BASE_MITRE_URL) -> Dict[str, Any]:
    """Technique 페이지에서 title/sections/URL을 수집."""
    url = f"{base_url}/techniques/{technique_id.replace('.', '/')}/"
    r = requests.get(url, timeout=20)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    title = soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else technique_id

    sections: Dict[str, str] = {}
    for h2 in soup.find_all("h2"):
        sec_title = h2.get_text(" ", strip=True)
        txt = []
        for sib in h2.find_all_next():
            if sib.name == "h2":
                break
            if sib.name in ("p", "li"):
                t = sib.get_text(" ", strip=True)
                if t:
                    txt.append(t)
        if txt:
            sections[sec_title] = "\n".join(txt)

    return {
        "technique_id": technique_id,
        "title": title,
        "url": url,
        "sections": sections,
    }


def build_mitre_chunks(
    label_map: Dict[str, Any],
    base_url: str = BASE_MITRE_URL,
) -> List[Dict[str, Any]]:
    """label_map(anchor_techniques) 기준으로 MITRE 청크 JSONL 항목 생성."""
    mitre_chunks: List[Dict[str, Any]] = []
    retrieved_at = datetime.now(timezone.utc).isoformat()

    for label, info in label_map.items():
        for tid in info.get("anchor_techniques", []):
            try:
                doc = fetch_technique_text(tid, base_url=base_url)
            except Exception as exc:
                print("fetch error:", tid, exc)
                continue

            for sec_title, sec_text in doc.get("sections", {}).items():
                for idx, ch in enumerate(chunk_text(sec_text)):
                    mitre_chunks.append(
                        {
                            "source": "MITRE_ATT&CK",
                            "retrieved_at": retrieved_at,
                            "label": label,
                            "technique_id": tid,
                            "technique_title": doc.get("title", ""),
                            "section": sec_title,
                            "chunk_id": f"MITRE:{tid}:{sec_title}:{idx}",
                            "text": ch,
                            "source_url": doc.get("url", ""),
                        }
                    )

    return mitre_chunks
