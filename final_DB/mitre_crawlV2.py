from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

# [날짜 수정: 2026-01-25 rag2 패키지 기준 상대 import로 변경]
from final_DB.textV2 import clean_text
from final_DB.constantsV2 import CHUNK_SIZE, CHUNK_OVERLAP


ATTACK_BASE = "https://attack.mitre.org"

# 슬라이딩 윈도우 방식으로 일정 길이의 청크로 분할
def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP): # -> List[str]:
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    n = len(text)

    while start < n:
        end = min(start + chunk_size, n)
        chunk = text[start:end]
        chunk = chunk.strip()
        if chunk:
            chunks.append(chunk)
        if end == n:
            break
        start = max(0, end - overlap)

    return chunks


# MITRE ATT&CK Technique 페이지 HTML 가져오기
def fetch_technique_page(technique_id: str, timeout: int = 20): # -> str:
    # [날짜 수정: 2026-01-24 technique_id 점 표기를 URL 경로에 맞춤]
    tid_path = technique_id.replace(".", "/")
    url = f"{ATTACK_BASE}/techniques/{tid_path}/"
    r = requests.get(url, timeout=timeout)
    try:
        r.raise_for_status()
    except requests.HTTPError as exc:
        # [날짜 수정: 2026-01-24 존재하지 않는 Technique ID는 스킵]
        if r.status_code == 404:
            return None, url
        raise exc
    return r.text, url

# MITRE ATT&CK 페이지에서 제목, 전체 설명 텍스트 추출
def parse_technique_text(html: str): # -> Dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")

    title = soup.find("h1")
    title_text = clean_text(title.get_text(" ")) if title else ""

    content = soup.get_text(" ")
    content = clean_text(content)

    return {
        "title": title_text,
        "text": content,
    }

# Technique ID 하나에 대해
# MITRE 페이지 fetch, 텍스트 파싱, chunking, chunk 문서 리스트 반환
def build_mitre_chunks_for_technique(
    technique_id: str,
    label: str,
    timeout: int = 20,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
): # -> List[dict]:

    # [날짜 수정: 2026-01-24 source_url/retrieved_at 필드 추가]
    html, source_url = fetch_technique_page(technique_id, timeout=timeout)
    if html is None:
        return []
    parsed = parse_technique_text(html)
    retrieved_at = datetime.now(timezone.utc).isoformat()

    raw_text = f"{parsed.get('title','')}\n{parsed.get('text','')}".strip()
    chunks = chunk_text(raw_text, chunk_size=chunk_size, overlap=overlap)

    docs = []
    for i, ch in enumerate(chunks):
        # [날짜 수정: 2026-01-24 rag JSONL 필드명에 맞게 chunk_id/section/technique_title 추가]
        chunk_id = f"MITRE:{technique_id}:full_page:{i}"
        docs.append(
            {
                "id": chunk_id,
                "source": "MITRE_ATT&CK",
                "retrieved_at": retrieved_at,
                "label": label,
                "technique_id": technique_id,
                "technique_title": parsed.get("title", ""),
                "section": "full_page",
                "chunk_id": chunk_id,
                "text": ch,
                "source_url": source_url,
            }
        )
    return docs

# LABLE_TO_ATTACK을 받아와
# 모든 라벨 x 모든 anchor_techniques에 대해
# MITRE ATT&CK 크롤링, chunking, JSONL 저장
def build_mitre_chunks(
    label_to_attack: Dict[str, dict],
    out_jsonl_path: str,
    timeout: int = 20,
): #-> List[dict]:
    all_docs: List[dict] = []
    seen = set()

    for label, info in label_to_attack.items():
        for tid in info.get("anchor_techniques", []):
            # 중복 technique_id는 한번만(저장/크롤링 중복 방지)
            key = (label, tid)
            if key in seen:
                continue
            seen.add(key)

            docs = build_mitre_chunks_for_technique(
                technique_id=tid,
                label=label,
                timeout=timeout,
            )
            all_docs.extend(docs)

    save_jsonl(all_docs, out_jsonl_path)
    return all_docs

# 문서 리스트를 JSONL 형식으로 저장
def save_jsonl(items: List[dict], path: str): # -> None:
    with open(path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
