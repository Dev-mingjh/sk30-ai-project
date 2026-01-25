import os
from pathlib import Path

import time
import streamlit as st

from rag.retriever import ChromaRetriever
from rag.generator import (
    AnswerGenerator,
    build_kisa_system,
    build_mitre_system,
    build_recent_cases_system,
    format_evidence,
)

from rag.web_search.web_search import collect_web_evidence
from rag.rag_engine import RAGEngine

from rag.configs.env import load_env
from rag.configs.constants import (
    DEFAULT_EMBED_MODEL,
    DEFAULT_LLM_MODEL,
    DEFAULT_TOP_K,
    COLLECTION_MITRE,
    COLLECTION_KISA,
    DEFAULT_OUT_DIR,
    DEFAULT_CHROMA_SUBDIR,
    ATTACK_LABELS,
    LABEL_TO_ATTACK,
)

load_env()

# 1) Chroma DB 경로
CHROMA_DIR = str(Path(DEFAULT_OUT_DIR) / DEFAULT_CHROMA_SUBDIR)

# 2) 컬렉션명
COLLECTION_MITRE_NAME = os.getenv("COLLECTION_MITRE", COLLECTION_MITRE)
COLLECTION_KISA_NAME = os.getenv("COLLECTION_KISA", COLLECTION_KISA)

# 혹시 env에 예전 값(mitre/kisa)이 남아있으면 경고용으로만 표시하고,
# 실제 사용은 constants 값으로 고정하고 싶다면 아래 2줄로 강제 고정도 가능:
# COLLECTION_MITRE_NAME = COLLECTION_MITRE
# COLLECTION_KISA_NAME = COLLECTION_KISA

# 3) 모델명
EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", DEFAULT_EMBED_MODEL)
GEN_MODEL = os.getenv("OPENAI_GEN_MODEL", DEFAULT_LLM_MODEL)

# 4) 공격 유형
ATTACK_TYPES = ATTACK_LABELS

# 긍/부정 답변 키워드
POSITIVE = ("네", "예", "필요", "해줘", "좋아", "응", "그래")
NEGATIVE = ("아니", "아니오", "괜찮", "필요없", "필요 없어")

# 선택지 키워드
CHOICE_REPORT = ("신고절차", "신고 절차", "신고", "절차")
CHOICE_MORE = ("최근 사례 설명", "사례", "최근 사례", "최근사례", "추가")

# =========================================================
# Streamlit UI
# =========================================================
st.set_page_config(page_title="공격 가이드 챗봇", layout="wide")
st.title("공격 가이드 챗봇")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "attack_type" not in st.session_state:
    st.session_state.attack_type = None
if "explain_done" not in st.session_state:
    st.session_state.explain_done = False
if "pending_choice" not in st.session_state:
    st.session_state.pending_choice = False
if "report_done" not in st.session_state:
    st.session_state.report_done = False
if "recent_done" not in st.session_state:
    st.session_state.recent_done = False
if "debug" not in st.session_state:
    st.session_state.debug = False


@st.cache_resource
def load_rag():
    retriever_mitre = ChromaRetriever(
        chroma_dir=CHROMA_DIR,
        collection_name=COLLECTION_MITRE_NAME,
        embed_model=EMBED_MODEL,
    )
    retriever_kisa = ChromaRetriever(
        chroma_dir=CHROMA_DIR,
        collection_name=COLLECTION_KISA_NAME,
        embed_model=EMBED_MODEL,
    )

    generator = AnswerGenerator(gen_model=GEN_MODEL)

    rag_mitre = RAGEngine(retriever_mitre, generator)
    rag_kisa = RAGEngine(retriever_kisa, generator)
    return rag_mitre, rag_kisa


rag_mitre, rag_kisa = load_rag()


def push(role: str, content: str):
    st.session_state.messages.append({"role": role, "content": content})


def render_messages():
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

# 챗팅 문장에서 공격 유형을 추출 (ATTACK_TYPES 기준 단순 포함 매칭)
def extract_attack_type(text: str):
    t = (text or "").lower()
    for attack in ATTACK_TYPES:
        if attack.lower() in t:
            return attack
    return None

# MITRE 기반 공격 특징/징후 설명 생성 + 응답 시간 출력 + 다음 선택지 안내
def run_explain():
    if not st.session_state.attack_type:
        push("assistant", "먼저 공격 유형을 알려주세요. 예: DDoS, PortScan")
        return

    label = st.session_state.attack_type
    q = f"{label} 공격 유형의 핵심 특징을 시스템 포멧을 따라서 작성해줘"

    # 라벨에 매핑된 Technique을 우선 사용
    anchors = LABEL_TO_ATTACK.get(label, {}).get("anchor_techniques", []) or []

    with st.spinner("공격 유형 특징 작성중..."):
        start = time.perf_counter()

        contexts = []

        # Technique별로 “해당 Technique 근거”를 강제로 확보
        if anchors:
            for tid in anchors:
                where = {
                    "$and": [
                        {"technique_id": tid},
                        {"$or": [
                            {"section": "Description"},
                            {"section": "Detection"},
                            {"section": "Mitigations"},
                            {"section": "Procedure Examples"},
                        ]},
                    ]
                }
                ctxs = rag_mitre.retrieve(
                    query=f"{label} {tid}",
                    top_k=2,          # tid당 2개 정도면 충분히 MITRE가 녹음
                    where=where,
                    fallback=True,
                )
                contexts.extend(ctxs)

        # 만약 technique 기반 검색이 거의 비었으면 기존 방식으로 보강
        if not contexts:
            contexts = rag_mitre.retrieve(q, top_k=DEFAULT_TOP_K + 2, where=None)

        mitre_evidence = format_evidence(contexts)

        system = build_mitre_system(
            attack_label=label,
            anchor_techniques=", ".join(anchors) if anchors else "",
            mitre_evidence=mitre_evidence,
        )

        answer = rag_mitre.generate(q, contexts, system=system) if contexts else "문서 근거를 찾지 못했습니다."
        elapsed = time.perf_counter() - start

    push("assistant", f"### 공격 유형 설명 ({label})\n\n{answer}\n\n_Response time: {elapsed:.2f}s_")
    push("assistant", "원하시는 항목을 선택하세요: **'신고절차'** 또는 **'최근 사례'**")
    st.session_state.pending_choice = True

# KISA 기반 신고 절차 생성
def run_report():
    if not st.session_state.attack_type:
        push("assistant", "먼저 공격 유형을 알려주세요. 예: DDoS, PortScan")
        return

    label = st.session_state.attack_type

    # (기존 로직 유지) DDoS면 label 필터, 아니면 section 필터
    if label.lower() == "ddos":
        q = f"{label} 상황에서 신고 절차를 단계별로 정리해줘."
        where = {"label": label}
        title = f"### KISA 기반 신고 절차 ({label})"
    else:
        q = "DDoS가 아닌 일반 침해사고 신고 절차 양식을 단계별로 정리해줘."
        where = {"section": "incident_response_guide"}
        title = "### KISA 기반 일반 신고 절차 (기타 유형)"

    with st.spinner("KISA 신고 절차 생성 중..."):
        contexts = rag_kisa.retrieve(q, top_k=DEFAULT_TOP_K + 1, where=where)
        if contexts:
            kisa_evidence = format_evidence(contexts)
            system = build_kisa_system(
                attack_label=label,
                kisa_evidence=kisa_evidence,
            )
            answer = rag_kisa.generate(q, contexts, system=system)
        else:
            answer = "문서 근거를 찾지 못했습니다."

    push("assistant", f"{title}\n\n{answer}")
    st.session_state.report_done = True
    st.session_state.pending_choice = False

    if st.session_state.debug:
        push("assistant", f"**[DEBUG: kisa contexts={len(contexts)}]**")

# 웹서치 기반 최근 사례 요약 + 응답 시간 출력
def run_recent_cases():
    if not st.session_state.attack_type:
        push("assistant", "먼저 공격 유형을 알려주세요. 예: DDoS, PortScan")
        return

    label = st.session_state.attack_type
    q = f"{label} 최근 사례 요약을 생성해줘."

    with st.spinner("최근 사례 검색 중..."):
        start = time.perf_counter()

        # 웹 증거 수집(최근 사례 2개)
        web_evidence = collect_web_evidence(label, [], top_n=2)

        system = build_recent_cases_system(
            attack_label=label,
            anchor_techniques="",
            web_evidence=web_evidence,
            top_n=2,
        )

        # 최근 사례는 RAG 컨텍스트 없이(system에 web_evidence 포함) 생성
        answer = rag_mitre.generate(q, [], system=system)

        elapsed = time.perf_counter() - start

    push("assistant", f"### 최근 사례 ({label})\n\n{answer}\n\n_Response time: {elapsed:.2f}s_")
    st.session_state.recent_done = True
    st.session_state.pending_choice = False

# 한 가지 출력 후, 아직 안 본 항목을 안내
def prompt_other_if_needed():
    if st.session_state.report_done and st.session_state.recent_done:
        return
    if st.session_state.report_done and not st.session_state.recent_done:
        push("assistant", "최근 사례가 필요하면 **'최근 사례'**라고 입력해주세요.")
    elif st.session_state.recent_done and not st.session_state.report_done:
        push("assistant", "신고절차가 필요하면 **'신고절차'**라고 입력해주세요.")


# 최초 안내 메시지
if not st.session_state.explain_done and len(st.session_state.messages) == 0:
    push("assistant", "어떤 공격 유형인지 먼저 알려주세요. 예: DDoS, PortScan")
    st.session_state.explain_done = True

render_messages()

user_text = st.chat_input("공격 유형을 입력하세요. 예: DDoS, PortScan")
if user_text:
    push("user", user_text)
    with st.chat_message("user"):
        st.markdown(user_text)

    detected_attack = extract_attack_type(user_text)

    # 1) 공격 유형을 포함해서 입력한 경우 → 설명 생성
    if detected_attack:
        if detected_attack != st.session_state.attack_type:
            st.session_state.attack_type = detected_attack
            st.session_state.explain_done = False
            st.session_state.pending_choice = False
            st.session_state.report_done = False
            st.session_state.recent_done = False
        run_explain()

    # 2) 공격 유형이 없는 입력 → 선택지 처리(신고/최근사례)
    else:
        if st.session_state.pending_choice:
            if any(k in user_text for k in CHOICE_REPORT):
                run_report()
                prompt_other_if_needed()
            elif any(k in user_text for k in CHOICE_MORE):
                run_recent_cases()
                prompt_other_if_needed()
            else:
                push("assistant", "원하시는 항목을 선택하세요: **'신고절차'** 또는 **'최근 사례'**")
        else:
            # 대기 상태가 아니어도 사용자가 바로 신고절차/최근사례를 요구할 수 있으니 허용
            if any(k in user_text for k in CHOICE_REPORT):
                run_report()
                prompt_other_if_needed()
            elif any(k in user_text for k in CHOICE_MORE):
                run_recent_cases()
                prompt_other_if_needed()
            else:
                push("assistant", "공격 유형을 포함해 입력해주세요. 예: **'DDoS'**")

    st.rerun()