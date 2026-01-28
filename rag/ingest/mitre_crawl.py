# MITRE ATT&CK 크롤링 및 청크 생성
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from ..configs.constants import BASE_MITRE_URL
from ..utils.text import chunk_text

# Technique 페이지에서 title/sections/URL을 수집
def fetch_technique_text(technique_id: str, base_url: str = BASE_MITRE_URL,) -> dict[str, object]:

    # Technique ID에 맞는 URL 구성
    url = f"{base_url}/techniques/{technique_id.replace('.', '/')}/"

    # HTTP 요청
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # 페이지 제목 (Technique 이름)
    h1 = soup.find("h1")
    title = h1.get_text(" ", strip=True) if h1 else technique_id

    # h2 기준으로 섹션 파싱
    sections: dict[str, str] = {}
    for h2 in soup.find_all("h2"):
        sec_title = h2.get_text(" ", strip=True)
        texts: list[str] = []

        for sib in h2.find_all_next():
            # 다음 섹션 시작 시 중단
            if sib.name == "h2":
                break

            # 본문 텍스트만 수집
            if sib.name in ("p", "li"):
                t = sib.get_text(" ", strip=True)
                if t:
                    texts.append(t)

        if texts:
            sections[sec_title] = "\n".join(texts)

    return {
        "technique_id": technique_id,
        "title": title,
        "url": url,
        "sections": sections,
    }


# label_map(anchor_techniques) 기준으로 MITRE 청크 JSONL 항목 생성
# MITRE 청크 규칙:
# - label_map의 anchor_techniques를 순회
# - Technique 페이지의 h2 섹션별 본문(p/li) 수집
# - 섹션 텍스트를 chunk_text로 고정 길이 분할(오버랩 없음)
# - 메타: label/technique_id/title/section/url 포함

def build_mitre_chunks(label_map: dict[str, object], base_url: str = BASE_MITRE_URL,) -> list[dict[str, object]]:
    mitre_chunks: list[dict[str, object]] = []
    retrieved_at = datetime.now(timezone.utc).isoformat()

    for label, info in label_map.items():
        # 각 라벨에 연결된 ATT&CK Technique 순회
        for tid in info.get("anchor_techniques", []):
            try:
                doc = fetch_technique_text(tid, base_url=base_url)
            except Exception as exc:
                # 개별 technique 실패는 전체 빌드를 중단하지 않음
                print("MITRE fetch error:", tid, exc)
                continue

            # 섹션별 텍스트를 chunk 단위로 분할
            for sec_title, sec_text in doc.get("sections", {}).items():
                chunks = chunk_text(sec_text)
                for idx, ch in enumerate(chunks):
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