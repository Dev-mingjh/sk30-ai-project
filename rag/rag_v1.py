"""RAG utilities converted from VectorDB2.ipynb for non-Colab use."""
# VectorDB2 ?? ??/???/??? ?? ??

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup


Attack_LABELS = [
    "DDoS",
    "PortScan",
    "Web Attack - Brute Force",
    "FTP-Patator",
    "Bot",
    "BENIGN",
    "Infiltration",
    "DoS slowloris",
]


label_to_attack = {
    "DDoS": {
        "behavior": "대량의 트래픽을 발생시켜 네트워크 또는 서비스의 가용성을 저하시키는 공격 행위",
        "anchor_techniques": ["T1498", "T1498.001", "T1498.002", "T1498", "T1499.001", "T1499.002", "T1499.003", "T1499.004"],
        "tactics": ["Impact"],
        "notes": ["대용량 플러딩, 반사(reflection) 기반 DDoS 포함"],
    },
    "DoS slowloris": {
        "behavior": "HTTP 연결을 장시간 유지하여 서버 자원을 고갈시키는 애플리케이션 계층 DoS 공격",
        "anchor_techniques": ["T1498", "T1498.001", "T1498.002", "T1498", "T1499.001", "T1499.002", "T1499.003", "T1499.004"],
        "tactics": ["Impact"],
        "notes": ["L7 slow DoS, 이후 KISA 문서에서 웹서버/서비스거부 대응 섹션과 강하게 결합"],
    },
    "PortScan": {
        "behavior": "대상 시스템의 열려 있는 포트 및 서비스 정보를 탐색하기 위한 스캔 행위",
        "anchor_techniques": ["T1046"],
        "tactics": ["Discovery"],
        "notes": ["사전 정찰 단계, IDS/방화벽 로그 분석과 연계"],
    },
    "Web Attack - Brute Force": {
        "behavior": "웹 로그인 인터페이스를 대상으로 계정 정보를 반복적으로 추측하는 공격 행위",
        "anchor_techniques": ["T1110", "T1110.001", "T1110.002", "T1110.003", "T1110.004"],
        "tactics": ["Credential Access"],
        "notes": ["로그인 실패 횟수 급증, 계정 잠금 정책 대응"],
    },
    "FTP-Patator": {
        "behavior": "FTP 서비스를 대상으로 사용자 계정 정보를 무차별 대입하는 공격 행위",
        "anchor_techniques": ["T1110", "T1110.001", "T1110.002", "T1110.003", "T1110.004"],
        "tactics": ["Credential Access"],
        "notes": ["프로토콜(FTP)은 메타데이터로 관리 (service=ftp)"],
    },
    "Bot": {
        "behavior": "감염된 호스트가 외부 명령제어 서버와 통신하는 봇넷 기반 행위",
        "anchor_techniques": ["T1110.002"],
        "tactics": ["Command and Control"],
        "notes": ["HTTP/HTTPS 기반 C2면 T1071.001에 태그. DNS면 이후 T1071.004 등으로 확장"],
    },
    "Infiltration": {
        "behavior": "외부 공격자가 내부 네트워크로 침투하여 정보 접근 또는 외부 유출을 시도하는 행위",
        "anchor_techniques": ["T1567", "T1567.002", "T1078", "T1190", "T1204"],
        "tactics": ["Exfiltration"],
        "notes": ["CICIDS 'Infiltration'은 환경에 따라 lateral movement/collection도 섞일 수 있어 추후 보강"],
    },
    "BENIGN": {
        "behavior": "정상적인 네트워크 트래픽 및 서비스 이용 행위",
        "anchor_techniques": [],
        "tactics": [],
        "notes": ["DB 수집 대상(가이드/대응)에서 제외. 베이스라인/정상 설명용 메타로만 유지"],
    },
}


LABEL_TO_KISA_CATEGORY = {
    "Web Attack - Brute Force": "계정탈취/인증공격",
    "FTP-Patator": "계정탈취/인증공격",
    "PortScan": "스캔/정찰",
    "DDoS": "서비스거부(DoS/DDoS)",
    "DoS slowloris": "서비스거부(DoS/DDoS)",
    "Infiltration": "침투/내부확산",
    "Bot": "악성코드/봇넷",
    "BENIGN": "일반/정상",
}


KISA_CATEGORY_KEYWORDS_KO = {
    "계정탈취/인증공격": ["계정탈취", "비밀번호 추측", "무차별 대입", "인증", "로그인 실패", "크리덴셜"],
    "스캔/정찰": ["포트스캔", "스캔", "정찰", "서비스 탐색", "nmap", "배너그래빙"],
    "서비스거부(DoS/DDoS)": ["서비스거부", "디도스", "가용성", "트래픽 폭주", "세션 고갈", "slowloris"],
    "침투/내부확산": ["침투", "권한상승", "내부 확산", "측면이동", "원격접속", "백도어"],
    "악성코드/봇넷": ["봇넷", "C2", "악성코드", "감염", "원격제어", "좀비PC"],
    "일반/정상": ["정상"],
}


LABEL_KEYWORDS = {
    "DDoS": ["디도스", "ddos", "대량", "트래픽 폭주", "가용성"],
    "DoS slowloris": ["slowloris", "슬로우리", "느린 요청", "연결 유지", "세션 고갈"],
    "PortScan": ["포트", "스캔", "정찰", "탐색", "nmap"],
    "Web Attack - Brute Force": ["무차별", "대입", "brute", "로그인 실패", "비밀번호", "인증"],
    "FTP-Patator": ["ftp", "patator", "로그인 실패", "비밀번호"],
    "Bot": ["봇넷", "c2", "명령제어", "악성코드", "감염"],
    "Infiltration": ["침투", "내부", "유출", "원격", "확산"],
    "BENIGN": ["정상"],
}


BASE_MITRE_URL = "https://attack.mitre.org"


# 라벨 표기 흔들림을 정규화해 표준 라벨로 맞춤
def normalize_label(label: str) -> str:
    """입력 라벨 표기 흔들림을 최대한 흡수해서 Attack_LABELS 중 하나로 정규화."""
    s = (label or "").strip()

    alias = {
        "DoS Slowloris": "DoS slowloris",
        "dos slowloris": "DoS slowloris",
        "Port Scan": "PortScan",
        "WebAttack-BruteForce": "Web Attack - Brute Force",
        "Web Attack Brute Force": "Web Attack - Brute Force",
        "FTP Patator": "FTP-Patator",
    }
    if s in alias:
        return alias[s]

    s2 = re.sub(r"\s+", " ", s)
    return alias.get(s2, s2)


# 라벨 문서에서 수집 대상 Technique ID를 모음
def collect_technique_ids(label_docs: List[Dict[str, Any]]) -> List[str]:
    tids = set()
    for d in label_docs:
        pages = d.get("collection_targets", {}).get("mitre_attack", {}).get("technique_pages", [])
        for tid in pages:
            if tid:
                tids.add(tid.strip())
    return sorted(tids)


# MITRE Technique 페이지에서 제목/섹션 텍스트를 크롤링
def fetch_technique_text(technique_id: str, base_url: str = BASE_MITRE_URL) -> Dict[str, Any]:
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


# 긴 텍스트를 고정 길이 기준으로 분할
def chunk_text(text: str, max_len: int = 1200) -> List[str]:
    text = (text or "").strip()
    if len(text) <= max_len:
        return [text] if text else []
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_len)
        chunks.append(text[start:end].strip())
        start = end
    return [c for c in chunks if c]


# MITRE Technique 문서를 라벨별 청크로 변환
def build_mitre_chunks(
    label_map: Dict[str, Any],
    base_url: str = BASE_MITRE_URL,
) -> List[Dict[str, Any]]:
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
                    mitre_chunks.append({
                        "source": "MITRE_ATT&CK",
                        "retrieved_at": retrieved_at,
                        "label": label,
                        "technique_id": tid,
                        "technique_title": doc.get("title", ""),
                        "section": sec_title,
                        "chunk_id": f"MITRE:{tid}:{sec_title}:{idx}",
                        "text": ch,
                        "source_url": doc.get("url", ""),
                    })

    return mitre_chunks


# 리스트를 JSONL 파일로 저장
def save_jsonl(items: List[Dict[str, Any]], path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for x in items:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    return path


# JSONL 파일을 리스트로 로드
def load_jsonl(path: str) -> List[Dict[str, Any]]:
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


# PDF에서 페이지별 텍스트 추출
def extract_pdf_text_by_page(pdf_path: str) -> List[Dict[str, Any]]:
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    pages = []
    for pno in range(len(doc)):
        text = doc[pno].get_text("text") or ""
        pages.append({"page_no": pno + 1, "text": text})
    doc.close()
    return pages


# 페이지 텍스트를 문단 단위로 분리
def split_paragraphs(text: str) -> List[str]:
    parts = [p.strip() for p in (text or "").split("\n\n")]
    return [p for p in parts if len(p) >= 40]


# 문단 키워드로 라벨을 간단 분류
def classify_paragraph(para: str) -> Optional[str]:
    s = (para or "").lower()
    best_label = None
    best_score = 0
    for label, kws in LABEL_KEYWORDS.items():
        score = sum(1 for k in kws if k.lower() in s)
        if score > best_score:
            best_score = score
            best_label = label
    return best_label if best_score >= 1 else None


# KISA PDF에서 라벨별 청크 생성
def build_kisa_chunks(pdf_path: str) -> List[Dict[str, Any]]:
    pages = extract_pdf_text_by_page(pdf_path)
    paras = []
    for p in pages:
        for para in split_paragraphs(p["text"]):
            paras.append({"page_no": p["page_no"], "text": para})

    classified_paragraphs = []
    for x in paras:
        lbl = classify_paragraph(x["text"])
        if lbl:
            classified_paragraphs.append({
                "label": lbl,
                "page_no": x["page_no"],
                "text": x["text"],
            })

    kisa_chunks: List[Dict[str, Any]] = []
    retrieved_at = datetime.now(timezone.utc).isoformat()
    for item in classified_paragraphs:
        chunks = chunk_text(item["text"])
        for idx, ch in enumerate(chunks):
            kisa_chunks.append({
                "source": "KISA",
                "source_doc": pdf_path,
                "retrieved_at": retrieved_at,
                "label": item["label"],
                "section": "incident_response_guide",
                "page_no": item["page_no"],
                "chunk_id": f"KISA:{item['label']}:{item['page_no']}:{idx}",
                "text": ch,
            })

    return kisa_chunks


# MITRE 청크를 Chroma 업서트용 포맷으로 정규화
def normalize_mitre(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    docs = []
    for x in items:
        labels = x.get("labels")
        if labels is None:
            labels = x.get("label")
        if isinstance(labels, list):
            labels_csv = ",".join(labels)
        elif labels:
            labels_csv = str(labels)
        else:
            labels_csv = ""

        docs.append({
            "id": x["chunk_id"],
            "text": x.get("text", ""),
            "meta": {
                "source": "MITRE_ATT&CK",
                "technique_id": x.get("technique_id", ""),
                "technique_title": x.get("technique_title", ""),
                "section": x.get("section", ""),
                "labels_csv": labels_csv,
                "mitigation_id": x.get("mitigation_id", ""),
                "mitigation_name": x.get("mitigation_name", ""),
                "source_url": x.get("source_url", ""),
            },
        })
    return docs


# KISA 청크를 Chroma 업서트용 포맷으로 정규화
def normalize_kisa(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    docs = []
    for x in items:
        raw_label = x.get("label", "")
        norm_label = normalize_label(raw_label) if raw_label else raw_label
        kisa_category = LABEL_TO_KISA_CATEGORY.get(norm_label, "기타")
        docs.append({
            "id": x["chunk_id"],
            "text": x.get("text", ""),
            "meta": {
                "source": "KISA",
                "label": norm_label,
                "kisa_category": kisa_category,
                "section": x.get("section", ""),
                "page_no": int(x.get("page_no", -1)) if str(x.get("page_no", "-1")).isdigit() else -1,
                "source_doc": x.get("source_doc", ""),
            },
        })
    return docs

## API키 가져오기
# 환경변수에서 OpenAI API 키 조회
from typing import Optional
import os
from pathlib import Path
from dotenv import load_dotenv

# app.py / rag 모듈 어디서든 1회 호출되게 두는 것을 권장
def load_env() -> None:
    # 프로젝트 루트에 .env가 있다면 거기로 맞추세요.
    # (이 파일이 rag/ 아래라면 parent를 한 번 더 올려야 할 수 있습니다.)
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        # 흔한 케이스: .env가 프로젝트 루트에 있는 경우
        env_path = Path(__file__).resolve().parent.parent / ".env"

    load_dotenv(dotenv_path=env_path, override=True)

    # OPEN_API_KEY로 저장한 경우 OpenAI 표준 키로도 주입
    if os.getenv("OPEN_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = os.environ["OPEN_API_KEY"]

def get_openai_key() -> Optional[str]:
    # dotenv 로드를 보장
    load_env()
    return os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_API_KEY")



# OpenAI 임베딩 API로 텍스트를 벡터화
def embed_texts(texts: List[str], model: Optional[str] = None) -> List[List[float]]:
    from openai import OpenAI

    model = model or os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
    api_key = get_openai_key()

    if not api_key:
        raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

    client = OpenAI(api_key=api_key)
    resp = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in resp.data]


# 문서 ID 중복 제거(마지막 항목 유지)
def dedup_docs_by_id(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    m = {}
    for d in docs:
        m[d["id"]] = d
    return list(m.values())


# 문서 ID 중복 여부를 출력하고 중복 목록 반환
def assert_unique_ids(docs: List[Dict[str, Any]], name: str = "docs") -> List[str]:
    from collections import Counter

    ids = [d["id"] for d in docs]
    dup = [k for k, v in Counter(ids).items() if v > 1]
    print(f"[{name}] total={len(ids)} unique={len(set(ids))} dups={len(dup)}")
    if dup:
        print("예시 dup ids:", dup[:10])
    return dup


# Chroma 클라이언트/컬렉션 초기화
def init_chroma(
    chroma_path: str,
    mitre_collection: str = "mitre",
    kisa_collection: str = "kisa",
):
    import chromadb

    client = chromadb.PersistentClient(path=chroma_path)
    col_mitre = client.get_or_create_collection(mitre_collection)
    col_kisa = client.get_or_create_collection(kisa_collection)
    return client, col_mitre, col_kisa


# 문서를 배치로 임베딩 후 Chroma에 업서트
def upsert_to_chroma(collection, docs: List[Dict[str, Any]], batch_size: int = 128) -> None:
    for i in range(0, len(docs), batch_size):
        b = docs[i : i + batch_size]
        ids = [d["id"] for d in b]
        texts = [d["text"] for d in b]
        metas = [d["meta"] for d in b]
        embs = embed_texts(texts)
        collection.upsert(ids=ids, documents=texts, metadatas=metas, embeddings=embs)


# MITRE 컬렉션에서 유사도 검색
def search_mitre(collection, query: str, technique_id: Optional[str] = None, k: int = 5) -> List[Dict[str, Any]]:
    where = {"technique_id": technique_id} if technique_id else None
    q_emb = embed_texts([query])
    res = collection.query(query_embeddings=q_emb, n_results=k, where=where)

    out = []
    for i in range(len(res["ids"][0])):
        out.append({
            "id": res["ids"][0][i],
            "text": res["documents"][0][i],
            "meta": res["metadatas"][0][i],
            "distance": res["distances"][0][i],
        })
    return out


# KISA 컬렉션에서 유사도 검색
def search_kisa(
    collection,
    query: str,
    category: Optional[str] = None,
    label: Optional[str] = None,
    k: int = 5,
) -> List[Dict[str, Any]]:
    where = None
    if category:
        where = {"kisa_category": category}
    elif label:
        where = {"label": label}

    q_emb = embed_texts([query])
    res = collection.query(query_embeddings=q_emb, n_results=k, where=where)

    out = []
    for i in range(len(res["ids"][0])):
        out.append({
            "id": res["ids"][0][i],
            "text": res["documents"][0][i],
            "meta": res["metadatas"][0][i],
            "distance": res["distances"][0][i],
        })
    return out


# MITRE 검색 결과를 근거 문자열로 구성
def build_mitre_evidence(mitre_chunks: List[Dict[str, Any]], max_items: int = 8) -> str:
    lines = []
    for c in mitre_chunks[:max_items]:
        meta = c.get("meta", {})
        tid = meta.get("technique_id", "")
        sec = meta.get("section", "")
        lines.append(f"- ({tid} / {sec}) {c.get('text', '')}")
    return "\n".join(lines) if lines else "- 관련 근거를 찾지 못했습니다."


# KISA 검색 결과를 근거 문자열로 구성
def build_kisa_evidence(kisa_chunks: List[Dict[str, Any]], max_items: int = 8) -> str:
    lines = []
    for c in kisa_chunks[:max_items]:
        meta = c.get("meta", {})
        pno = meta.get("page_no", "")
        lines.append(f"- (p.{pno}) {c.get('text', '')}")
    return "\n".join(lines) if lines else "- 관련 근거를 찾지 못했습니다."


# 검색 결과를 바탕으로 LLM 응답 생성
def rag_answer(
    query: str,
    col_mitre,
    col_kisa,
    category: Optional[str] = None,
    label: Optional[str] = None,
    k_mitre: int = 3,
    k_kisa: int = 3,
    model: str = "gpt-4o-mini",
) -> str:
    from openai import OpenAI

    mitre_hits = search_mitre(col_mitre, query, k=k_mitre)
    kisa_hits = search_kisa(col_kisa, query, category=category, label=label, k=k_kisa)

    context = (
        "[MITRE]\n"
        + build_mitre_evidence(mitre_hits)
        + "\n\n[KISA]\n"
        + build_kisa_evidence(kisa_hits)
    )

    api_key = get_openai_key()
    if not api_key:
        raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "너는 사이버 보안 분석가다. 제공된 근거를 바탕으로 한국어로 간결하게 답하라.",
            },
            {
                "role": "user",
                "content": f"질문: {query}\n\n근거:\n{context}",
            },
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content


# 전체 파이프라인 실행: 수집 -> 저장 -> 정규화 -> 업서트
def build_vector_db(
    pdf_path: str,
    out_dir: str,
    chroma_path: str,
    mitre_jsonl: str = "mitre_chunks.jsonl",
    kisa_jsonl: str = "kisa_chunks.jsonl",
    mitre_collection: str = "mitre",
    kisa_collection: str = "kisa",
) -> Tuple[Any, Any, Any]:
    mitre_chunks = build_mitre_chunks(label_to_attack)
    kisa_chunks = build_kisa_chunks(pdf_path)

    mitre_jsonl_path = save_jsonl(mitre_chunks, os.path.join(out_dir, mitre_jsonl))
    kisa_jsonl_path = save_jsonl(kisa_chunks, os.path.join(out_dir, kisa_jsonl))

    mitre_items = load_jsonl(mitre_jsonl_path)
    kisa_items = load_jsonl(kisa_jsonl_path)

    docs_mitre = dedup_docs_by_id(normalize_mitre(mitre_items))
    docs_kisa = dedup_docs_by_id(normalize_kisa(kisa_items))

    client, col_mitre, col_kisa = init_chroma(chroma_path, mitre_collection, kisa_collection)
    upsert_to_chroma(col_mitre, docs_mitre)
    upsert_to_chroma(col_kisa, docs_kisa)

    return client, col_mitre, col_kisa


if __name__ == "__main__":
    print("rag_v1.py: import해서 사용하세요. 예시:")
    print("  from rag_v1 import build_vector_db, rag_answer")
