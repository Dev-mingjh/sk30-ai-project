#--------------------------------------------------------------##
## 수정사항 MEMO:
# 0125: 응답 시간을 알기위해 time 모듈 imoport_이기찬
# 0125: 공격 유형 특징, 최근 사례 응답의 응답 시간만 알수있음, 응답 마지막 줄 time:~s 출력_이기찬
#--------------------------------------------------------------##

import os
import streamlit as st

## 0125 수정: 모델의 응답 시간을 알기위해 time 추가_이기찬
import time 
from rag_refactoring.retriever import ChromaRetriever
from rag_refactoring.generator import (
    AnswerGenerator,
    build_kisa_system,
    build_mitre_system,
    build_recent_cases_system,
    format_evidence,
)
## 0125수정 : 잘못된 web_search를 참조해서, 수정본이 반영안되고 있엇음
from rag_refactoring.web_search.web_search import collect_web_evidence
from rag_refactoring.rag_engine import RAGEngine
from rag_refactoring.configs.env import load_env

load_env()

CHROMA_DIR = os.getenv("CHROMA_DIR", "chroma_db")
COLLECTION_KISA = os.getenv("COLLECTION_KISA", "kisa")
EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
GEN_MODEL = os.getenv("OPENAI_GEN_MODEL", "gpt-5.2")

ATTACK_TYPES = [
    "DDoS",
    "PortScan",
    "Web Attack",
    "Brute Force",
    "BotNet",
    "Infiltration",
    "DoS",
]

POSITIVE = ("예", "응", "필요", "해주세요", "좋아", "ㅇㅋ", "그래")
NEGATIVE = ("아니", "아니요", "괜찮", "필요없", "필요 없어")

CHOICE_REPORT = ("신고절차", "신고 절차", "신고", "절차")
CHOICE_MORE = ("최근 사례 설명", "사례", "최근 사례", "최근사례", "추가")

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

##rag연결 함수
def load_rag():
    retriever_mitre = ChromaRetriever(
        chroma_dir=CHROMA_DIR,
        collection_name="mitre",
        embed_model=EMBED_MODEL,
    )
    retriever_kisa = ChromaRetriever(
        chroma_dir=CHROMA_DIR,
        collection_name=COLLECTION_KISA,
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


# 챗팅 문장에서 공격 유형을 추출
def extract_attack_type(text: str):
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
    q = f"{label} 공격 유형을 설명해줘. 공격 특징과 지표 포함."
    with st.spinner("공격 유형 설명 생성 중..."):
        ## 0125 수정:응답 시간 추가
        start = time.perf_counter()

        contexts = rag_mitre.retrieve(q, top_k=2, where=None)
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
            ## 0125 수정: 응답 시간 추가
            elapsed = time.perf_counter() -start
        else:
            answer = "문서 근거를 찾지 못했습니다."
            ## 0125 수정: 응답 시간 추가
            elapsed = time.perf_counter() -start
    push("assistant", f"### 공격 유형 설명 ({label})\n\n{answer}\n\n_Response time: {elapsed:.2f}s_")
    push("assistant", "원하시는 항목을 선택하세요: '신고절차' 또는 '최근 사례'")
    st.session_state.pending_choice = True

    if st.session_state.debug:
        push("assistant", f"**[DEBUG: mitre contexts={len(contexts)}]**")


def run_report():
    if not st.session_state.attack_type:
        push("assistant", "먼저 공격 유형을 알려주세요. 예: DDoS, PortScan")
        return
    label = st.session_state.attack_type
    if label.lower() == "ddos":
        q = f"{label} 상황에서 신고 절차를 단계별로 정리해줘."
        where = {"label": label}
        title = f"### KISA 기반 신고 절차 ({label})"
    else:
        q = "DDoS가 아닌 일반 침해사고 신고 절차를 단계별로 정리해줘."
        where = {"section": "incident_response_guide"}
        title = "### KISA 기반 일반 신고 절차 (기타 유형)"

    with st.spinner("KISA 신고 절차 생성 중..."):
        contexts = rag_kisa.retrieve(q, top_k=6, where=where)
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


def run_recent_cases():
    if not st.session_state.attack_type:
        push("assistant", "먼저 공격 유형을 알려주세요. 예: DDoS, PortScan")
        return
    label = st.session_state.attack_type
    q = f"{label} 최근 사례 요약을 생성해줘."

    with st.spinner("최근 사례 검색 중..."):
        start = time.perf_counter()
        recent_cases = collect_web_evidence(label, [], top_n=2)
        ## 0125 수정: 응답시간
        system = build_recent_cases_system(
            attack_label=label,
            anchor_techniques="",
            web_evidence=recent_cases,
            top_n=2,
        )
        answer = rag_mitre.generate(q, [], system=system)
        ## 0125 수정: 응답시간 확인
        elapsed = time.perf_counter() - start
    push("assistant", f"### 최근 사례 ({label})\n\n{answer}\n\n_Response time: {elapsed:.2f}s_")
    st.session_state.recent_done = True
    st.session_state.pending_choice = False


def prompt_other_if_needed():
    if st.session_state.report_done and st.session_state.recent_done:
        return
    if st.session_state.report_done:
        push("assistant", "추가 공격 설명이 필요하면 '추가 공격 설명'이라고 입력해주세요.")
    elif st.session_state.recent_done:
        push("assistant", "신고절차가 필요하면 '신고절차'라고 입력해주세요.")


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
            st.session_state.pending_choice = False
            st.session_state.report_done = False
            st.session_state.recent_done = False
        run_explain()
    else:
        if st.session_state.pending_choice:
            if any(k in user_text for k in CHOICE_REPORT):
                run_report()
                prompt_other_if_needed()
            elif any(k in user_text for k in CHOICE_MORE):
                run_recent_cases()
                prompt_other_if_needed()
            else:
                push("assistant", "원하시는 항목을 선택하세요: '신고절차' 또는 '추가 공격 설명'")
        else:
            if any(k in user_text for k in CHOICE_REPORT):
                run_report()
                prompt_other_if_needed()
            elif any(k in user_text for k in CHOICE_MORE):
                run_recent_cases()
                prompt_other_if_needed()
            else:
                push("assistant", "공격 유형을 포함해 입력해주세요. 예: 'DDoS'")

    st.rerun()
