import os
import time
from pathlib import Path
import streamlit as st

# RAG 관련 모듈 임포트
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
    DEFAULT_EMBED_MODEL, DEFAULT_LLM_MODEL, DEFAULT_TOP_K,
    COLLECTION_MITRE, COLLECTION_KISA, DEFAULT_OUT_DIR,
    DEFAULT_CHROMA_SUBDIR, ATTACK_LABELS, LABEL_TO_ATTACK,
)

# =========================================================
# 1. 설정 및 초기화 (Configuration & Init)
# =========================================================


@st.cache_resource
def load_rag_engines():
    """RAG 엔진 로드 및 캐싱"""
    retriever_mitre = ChromaRetriever(CHROMA_DIR, COLLECTION_MITRE_NAME, EMBED_MODEL)
    retriever_kisa = ChromaRetriever(CHROMA_DIR, COLLECTION_KISA_NAME, EMBED_MODEL)
    generator = AnswerGenerator(gen_model=GEN_MODEL)
    return RAGEngine(retriever_mitre, generator), RAGEngine(retriever_kisa, generator)

# =========================================================
# 2. 유틸리티 및 메시지 함수 (Utilities)
# =========================================================
def push_msg(role: str, content: str):
    st.session_state.messages.append({"role": role, "content": content})

def extract_attack_type(text: str):
    t = (text or "").lower()
    for attack in ATTACK_LABELS:
        if attack.lower() in t: return attack
    return None

def prompt_other_if_needed():
    """추가로 확인 가능한 항목 안내"""
    if st.session_state.report_done and not st.session_state.recent_done:
        push_msg("assistant", "최근 사례가 필요하면 **'최근 사례'**라고 입력해주세요.")
    elif st.session_state.recent_done and not st.session_state.report_done:
        push_msg("assistant", "신고절차가 필요하면 **'신고절차'**라고 입력해주세요.")

# =========================================================
# 3. 핵심 비즈니스 로직 (Core RAG Logic)
# =========================================================
def run_explain_logic(rag_mitre, label):
    """공격 특징 설명 생성"""
    q = f"{label} 공격 유형의 핵심 특징 분석"
    anchors = LABEL_TO_ATTACK.get(label, {}).get("anchor_techniques", []) or []

    with st.spinner(f"{label} 공격 분석 중..."):
        start = time.perf_counter()
        contexts = []
        if anchors:
            for tid in anchors:
                where = {"$and": [{"technique_id": tid}, {"section": {"$in": ["Description", "Detection", "Mitigations", "Procedure Examples"]}}]}
                contexts.extend(rag_mitre.retrieve(query=f"{label} {tid}", top_k=2, where=where, fallback=True))
        
        if not contexts:
            contexts = rag_mitre.retrieve(q, top_k=DEFAULT_TOP_K + 2)

        system = build_mitre_system(label, ", ".join(anchors), format_evidence(contexts))
        answer = rag_mitre.generate(q, contexts, system=system) if contexts else "문서 근거를 찾지 못했습니다."
        elapsed = time.perf_counter() - start

    push_msg("assistant", f"### 공격 유형 분석 ({label})\n\n{answer}\n\n_Response time: {elapsed:.2f}s_")
    push_msg("assistant", "원하시는 항목을 선택하세요: **'신고절차'** 또는 **'최근 사례'**")
    st.session_state.pending_choice = True

def run_report_logic(rag_kisa, label):
    """신고 절차 안내 생성"""
    is_ddos = label.lower() == "ddos"
    q = f"{label} 신고 절차" if is_ddos else "일반 침해사고 신고 절차"
    where = {"label": label} if is_ddos else {"section": "incident_response_guide"}
    title = f"### KISA 기반 신고 절차 ({label})"

    with st.spinner("대응 가이드 구성 중..."):
        contexts = rag_kisa.retrieve(q, top_k=DEFAULT_TOP_K + 1, where=where)
        if contexts:
            system = build_kisa_system(label, format_evidence(contexts))
            answer = rag_kisa.generate(q, contexts, system=system)
        else:
            answer = "가이드 문서를 찾지 못했습니다."

    push_msg("assistant", f"{title}\n\n{answer}")
    st.session_state.report_done = True
    st.session_state.pending_choice = False

def run_recent_cases_logic(rag_mitre, label):
    """최근 사례 요약 생성"""
    with st.spinner("최근 사례 검색 중..."):
        start = time.perf_counter()
        web_evidence = collect_web_evidence(label, [], top_n=2)
        system = build_recent_cases_system(label, "", web_evidence, top_n=2)
        answer = rag_mitre.generate(f"{label} 최근 사례 요약", [], system=system)
        elapsed = time.perf_counter() - start

    push_msg("assistant", f"### 최근 사례 ({label})\n\n{answer}\n\n_Response time: {elapsed:.2f}s_")
    st.session_state.recent_done = True
    st.session_state.pending_choice = False

# =========================================================
# 4. 이벤트 핸들러 및 메인 (Handlers & Main)
# =========================================================
def handle_input(user_text, rag_mitre, rag_kisa):
    """사용자 입력에 따른 분기 처리"""
    push_msg("user", user_text)
    detected_attack = extract_attack_type(user_text)

    # 1) 공격 유형이 감지된 경우 (설명 우선)
    if detected_attack:
        if detected_attack != st.session_state.attack_type:
            st.session_state.attack_type = detected_attack
            st.session_state.report_done = False
            st.session_state.recent_done = False
        run_explain_logic(rag_mitre, detected_attack)
    
    # 2) 공격 유형이 없는 경우 (선택지 처리)
    else:
        label = st.session_state.attack_type
        if any(k in user_text for k in CHOICE_REPORT):
            if label: 
                run_report_logic(rag_kisa, label)
                prompt_other_if_needed()
            else: push_msg("assistant", "먼저 분석할 공격 유형을 알려주세요.")
        elif any(k in user_text for k in CHOICE_MORE):
            if label:
                run_recent_cases_logic(rag_mitre, label)
                prompt_other_if_needed()
            else: push_msg("assistant", "먼저 분석할 공격 유형을 알려주세요.")
        else:
            msg = "원하시는 항목을 선택하세요: **'신고절차'** 또는 **'최근 사례'**" if st.session_state.pending_choice else "분석할 공격 유형을 입력해주세요. (예: DDoS)"
            push_msg("assistant", msg)

def main():
    # 초기 안내
    if not st.session_state.messages:
        push_msg("assistant", "안녕하세요! 어떤 공격 유형에 대해 도움이 필요하신가요? (예: DDoS, PortScan)")
        st.rerun()

    # 채팅 입력
    if user_text := st.chat_input("메시지를 입력하세요..."):
        handle_input(user_text, rag_mitre, rag_kisa)
        st.rerun()

load_env()

CHROMA_DIR = str(Path(DEFAULT_OUT_DIR) / DEFAULT_CHROMA_SUBDIR)
COLLECTION_MITRE_NAME = os.getenv("COLLECTION_MITRE", COLLECTION_MITRE)
COLLECTION_KISA_NAME = os.getenv("COLLECTION_KISA", COLLECTION_KISA)
EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", DEFAULT_EMBED_MODEL)
GEN_MODEL = os.getenv("OPENAI_GEN_MODEL", DEFAULT_LLM_MODEL)

CHOICE_REPORT = ("신고절차", "신고 절차", "신고", "절차")
CHOICE_MORE = ("최근 사례 설명", "사례", "최근 사례", "최근사례", "추가")
rag_mitre, rag_kisa = load_rag_engines()
