from rag import rag_api
from guide import *
import streamlit as st
import time


# [RAG] 벡터DB + 임베딩 + 검색 파이프라인 로드
@st.cache_resource
def load_bundle():
    """
    RAG 검색에 필요한 리소스 번들을 초기화한다.

    Returns
    -------
    object
        - 벡터 DB
        - 임베딩 모델
        - 검색 파이프라인이 포함된 RAG bundle 객체

    Notes
    -----
    st.cache_resource를 사용하여
    Streamlit 재실행 시에도 RAG 리소스를 재사용한다.
    """
    return rag_api.create_rag_bundle()


# RAG 번들 로드 (앱 전체에서 재사용)
bundle = load_bundle()


# [LLM Function Calling] 사용 가능한 도구 정의
'''
1. explain_attack 
2. get_kisa_report
3. get_recent_cases
4. get_kisa_guide
'''
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "explain_attack",
            "description": "Explain a cybersecurity attack using MITRE ATT&CK",
            "parameters": {
                "type": "object",
                "properties": {
                    "attack_type": {
                        "type": "string",
                        "description": "Attack type like DDoS, PortScan, SQL Injection"
                    }
                },
                "required": ["attack_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_kisa_report",
            "description": "Generate a KISA incident response report",
            "parameters": {
                "type": "object",
                "properties": {
                    "attack_type": {"type": "string"}
                },
                "required": ["attack_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_cases",
            "description": "Find recent real-world attack cases",
            "parameters": {
                "type": "object",
                "properties": {
                    "attack_type": {"type": "string"}
                },
                "required": ["attack_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_kisa_guide",
            "description": "Provide KISA security guide",
            "parameters": {
                "type": "object",
                "properties": {
                    "attack_type": {"type": "string"}
                },
                "required": ["attack_type"]
            }
        }
    }
]

# [Function Map] LLM 함수 호출 → 실제 Python 함수 매핑
FUNCTION_MAP = {
    "explain_attack": lambda args: rag_api.answer_mitre_explain(
        bundle, args["attack_type"]
    ),
    "get_kisa_report": lambda args: rag_api.answer_kisa_report(
        bundle, args["attack_type"]
    ),
    "get_recent_cases": lambda args: rag_api.answer_recent_cases(
        bundle, args["attack_type"]
    ),
    "get_kisa_guide": lambda args: rag_api.answer_kisa_guide(
        bundle, args["attack_type"]
    ),
}

# [Chat State] 메시지 헬퍼
def push(role: str, content: str):
    """
    Streamlit 세션 상태에 채팅 메시지를 추가한다.
    """
    st.session_state.messages.append({
        "role": role,
        "content": content
    })

# [UI] 채팅 메시지 렌더링
def render_messages():
    """
    session_state.messages에 저장된 모든 채팅 메시지를
    Streamlit chat UI로 출력한다.
    """
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

# [RAG Flow] 공격 유형 설명(MITRE ATT&CK)
def run_explain():
    """
    선택된 공격 유형에 대해 MITRE ATT&CK 기반 설명을 생성한다.

    Flow
    ----
    1. attack_type 존재 여부 확인
    2. RAG 기반 공격 설명 생성
    3. 응답 시간 측정 및 결과 출력
    4. 다음 선택(report / recent cases / guide) 유도
    """
    if not st.session_state.attack_type:
        push("assistant", "Please provide an attack type, e.g., DDoS, PortScan.")
        return

    label = st.session_state.attack_type

    with st.spinner("Generating explanation..."):
        start = time.perf_counter()
        result = rag_api.answer_mitre_explain(bundle, label)
        elapsed = time.perf_counter() - start

    push(
        "assistant",
        f"### Attack Explanation ({label})\n\n"
        f"{result['answer']}\n\n"
        f"_Response time: {elapsed:.2f}s_"
    )

    push("assistant", "Choose next: **report** or **recent cases** or **guide**")
    st.session_state.pending_choice = True

# [RAG Flow] KISA 침해사고 대응 보고서
def run_report():
    """
    KISA 침해사고 대응 보고서 형식의 응답을 생성한다.
    """
    if not st.session_state.attack_type:
        push("assistant", "Please provide an attack type, e.g., DDoS, PortScan.")
        return

    label = st.session_state.attack_type

    with st.spinner("Generating KISA report response..."):
        result = rag_api.answer_kisa_report(bundle, label)

    push("assistant", f"### KISA Report ({label})\n\n{result['answer']}")

    st.session_state.report_done = True
    st.session_state.pending_choice = False

    # 디버그 모드일 경우 검색 컨텍스트 출력
    if st.session_state.debug:
        push("assistant", f"**[DEBUG: kisa contexts={len(result['contexts'])}]**")


# [RAG Flow] 최근 실제 공격 사례 검색
def run_recent_cases():
    """
    실제 최근 보안 사고 사례를 검색하여 요약한다.
    """
    if not st.session_state.attack_type:
        push("assistant", "Please provide an attack type, e.g., DDoS, PortScan.")
        return

    label = st.session_state.attack_type

    with st.spinner("Searching recent cases..."):
        start = time.perf_counter()
        result = rag_api.answer_recent_cases(bundle, label)
        elapsed = time.perf_counter() - start

    push(
        "assistant",
        f"### Recent Cases ({label})\n\n"
        f"{result['answer']}\n\n"
        f"_Response time: {elapsed:.2f}s_"
    )

    st.session_state.recent_done = True
    st.session_state.pending_choice = False


# [RAG Flow] KISA 보안 대응 가이드
def run_guide():
    """
    KISA 보안 가이드를 기반으로 대응 방법을 제공한다.
    """
    if not st.session_state.attack_type:
        push("assistant", "Please provide an attack type, e.g., DDoS, PortScan.")
        return

    label = st.session_state.attack_type

    with st.spinner("Generating KISA guide..."):
        start = time.perf_counter()
        result = rag_api.answer_kisa_guide(bundle, label)
        elapsed = time.perf_counter() - start

    push(
        "assistant",
        f"### KISA Guide ({label})\n\n"
        f"{result['answer']}\n\n"
        f"_Response time: {elapsed:.2f}s_"
    )

    st.session_state.guide_done = True
    st.session_state.pending_choice = False
