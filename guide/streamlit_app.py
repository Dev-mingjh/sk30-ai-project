import os
from pathlib import Path

import streamlit as st

from rag.retriever import ChromaRetriever
from rag.generator import (
    AnswerGenerator,
    build_kisa_system,
    build_mitre_system,
    format_evidence,
)
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
if "pending_report" not in st.session_state:
    st.session_state.pending_report = False
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


def extract_attack_type(text: str):
    """채팅 문장에서 공격 유형을 추출 (ATTACK_TYPES 기준 단순 포함 매칭)."""
    t = (text or "").lower()
    for attack in ATTACK_TYPES:
        if attack.lower() in t:
            return attack
    return None


def run_explain():
    if not st.session_state.attack_type:
        push("assistant", "먼저 공격 유형을 알려주세요. 예: DDoS, PortScan")
        return

    label = st.session_state.attack_type
    q = f"{label} 공격 유형의 핵심 특징을 시스템 포멧을 따라서 작성해줘"

    with st.spinner("공격 유형 특징 작성중..."):
        contexts = rag_mitre.retrieve(q, top_k=DEFAULT_TOP_K + 1, where=None)
        if contexts:
            anchor_techniques = sorted(
                {
                    c.get("metadata", {}).get("technique_id", "")
                    for c in contexts
                    if c.get("metadata", {}).get("technique_id")
                }
            )
            mitre_evidence = format_evidence(contexts)
            system = build_mitre_system(
                attack_label=label,
                anchor_techniques=", ".join(anchor_techniques),
                mitre_evidence=mitre_evidence,
            )
            answer = rag_mitre.generate(q, contexts, system=system)
        else:
            answer = "문서 근거를 찾지 못했습니다."

    push("assistant", f"### 작성중 ({label})\n\n{answer}")
    push("assistant", "신고 절차가 필요하신가요? 필요하면 '네'라고 답해주세요.")
    st.session_state.pending_report = True

    if st.session_state.debug:
        push("assistant", f"**[DEBUG: mitre contexts={len(contexts)}]**")
        push("assistant", f"**[DEBUG: chroma_dir={CHROMA_DIR}]**")
        push("assistant", f"**[DEBUG: collections mitre={COLLECTION_MITRE_NAME}, kisa={COLLECTION_KISA_NAME}]**")
        push("assistant", f"**[DEBUG: models embed={EMBED_MODEL}, gen={GEN_MODEL}]**")


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

    if st.session_state.debug:
        push("assistant", f"**[DEBUG: kisa contexts={len(contexts)}]**")
        push("assistant", f"**[DEBUG: chroma_dir={CHROMA_DIR}]**")
        push("assistant", f"**[DEBUG: collections mitre={COLLECTION_MITRE_NAME}, kisa={COLLECTION_KISA_NAME}]**")
        push("assistant", f"**[DEBUG: models embed={EMBED_MODEL}, gen={GEN_MODEL}]**")


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
    if detected_attack:
        if detected_attack != st.session_state.attack_type:
            st.session_state.attack_type = detected_attack
            st.session_state.explain_done = False
            st.session_state.pending_report = False
        run_explain()
    else:
        if st.session_state.pending_report:
            if any(k in user_text for k in POSITIVE):
                run_report()
                st.session_state.pending_report = False
            elif any(k in user_text for k in NEGATIVE):
                push("assistant", "알겠습니다. 필요하면 '신고절차'라고 말씀해주세요.")
                st.session_state.pending_report = False
            else:
                push("assistant", "신고 절차가 필요하면 '네', 아니면 '아니오'로 답해주세요.")
        else:
            push("assistant", "공격 유형을 포함해서 입력해주세요. 예: 'DDoS'")

    st.rerun()
