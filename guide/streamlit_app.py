import time
import streamlit as st

from rag import rag_api

# =========================================================
# Streamlit UI
# =========================================================
st.set_page_config(page_title="Attack Guide Chat", layout="wide")
st.title("Attack Guide Chat")

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
if "guide_done" not in st.session_state:
    st.session_state.guide_done = False
if "debug" not in st.session_state:
    st.session_state.debug = False


@st.cache_resource
def load_bundle():
    return rag_api.create_rag_bundle()


bundle = load_bundle()

CHOICE_REPORT = ("report", "kisa report", "incident response")
CHOICE_MORE = ("recent", "recent cases", "cases")
CHOICE_GUIDE = ("guide", "kisa guide")


def push(role: str, content: str):
    st.session_state.messages.append({"role": role, "content": content})


def render_messages():
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])


def run_explain():
    if not st.session_state.attack_type:
        push("assistant", "Please provide an attack type, e.g., DDoS, PortScan.")
        return

    label = st.session_state.attack_type

    with st.spinner("Generating explanation..."):
        start = time.perf_counter()
        result = rag_api.answer_mitre_explain(bundle, label)
        elapsed = time.perf_counter() - start

    push("assistant", f"### Attack Explanation ({label})\n\n{result['answer']}\n\n_Response time: {elapsed:.2f}s_")
    push("assistant", "Choose next: **report** or **recent cases** or **guide**")
    st.session_state.pending_choice = True


def run_report():
    if not st.session_state.attack_type:
        push("assistant", "Please provide an attack type, e.g., DDoS, PortScan.")
        return

    label = st.session_state.attack_type

    with st.spinner("Generating KISA report response..."):
        result = rag_api.answer_kisa_report(bundle, label)

    push("assistant", f"### KISA Report ({label})\n\n{result['answer']}")
    st.session_state.report_done = True
    st.session_state.pending_choice = False

    if st.session_state.debug:
        push("assistant", f"**[DEBUG: kisa contexts={len(result['contexts'])}]**")


def run_recent_cases():
    if not st.session_state.attack_type:
        push("assistant", "Please provide an attack type, e.g., DDoS, PortScan.")
        return

    label = st.session_state.attack_type

    with st.spinner("Searching recent cases..."):
        start = time.perf_counter()
        result = rag_api.answer_recent_cases(bundle, label)
        elapsed = time.perf_counter() - start

    push("assistant", f"### Recent Cases ({label})\n\n{result['answer']}\n\n_Response time: {elapsed:.2f}s_")
    st.session_state.recent_done = True
    st.session_state.pending_choice = False


def run_guide():
    if not st.session_state.attack_type:
        push("assistant", "Please provide an attack type, e.g., DDoS, PortScan.")
        return

    label = st.session_state.attack_type

    with st.spinner("Generating KISA guide..."):
        start = time.perf_counter()
        result = rag_api.answer_kisa_guide(bundle, label)
        elapsed = time.perf_counter() - start

    push("assistant", f"### KISA Guide ({label})\n\n{result['answer']}\n\n_Response time: {elapsed:.2f}s_")
    st.session_state.guide_done = True
    st.session_state.pending_choice = False


def prompt_other_if_needed():
    if st.session_state.report_done and st.session_state.recent_done:
        return
    if st.session_state.report_done and not st.session_state.recent_done:
        push("assistant", "If you want recent cases, type **recent cases**.")
    elif st.session_state.recent_done and not st.session_state.report_done:
        push("assistant", "If you want a report, type **report**.")


if not st.session_state.explain_done and len(st.session_state.messages) == 0:
    push("assistant", "What attack type is this about? (e.g., DDoS, PortScan)")
    st.session_state.explain_done = True

render_messages()

user_text = st.chat_input("Enter attack type or choose: report / recent cases / guide")
if user_text:
    push("user", user_text)
    with st.chat_message("user"):
        st.markdown(user_text)

    detected_attack = rag_api.extract_attack_type(user_text)
    lowered = user_text.lower()

    if detected_attack:
        if detected_attack != st.session_state.attack_type:
            st.session_state.attack_type = detected_attack
            st.session_state.pending_choice = False
            st.session_state.report_done = False
            st.session_state.guide_done = False
            st.session_state.recent_done = False
        run_explain()
    else:
        if st.session_state.pending_choice:
            if any(k in lowered for k in CHOICE_REPORT):
                run_report()
                prompt_other_if_needed()
            elif any(k in lowered for k in CHOICE_MORE):
                run_recent_cases()
                prompt_other_if_needed()
            elif any(k in lowered for k in CHOICE_GUIDE):
                run_guide()
                prompt_other_if_needed()
            else:
                push("assistant", "Please choose **report**, **recent cases**, or **guide**.")
        else:
            if any(k in lowered for k in CHOICE_REPORT):
                run_report()
                prompt_other_if_needed()
            elif any(k in lowered for k in CHOICE_MORE):
                run_recent_cases()
                prompt_other_if_needed()
            elif any(k in lowered for k in CHOICE_GUIDE):
                run_guide()
                prompt_other_if_needed()
            else:
                push("assistant", "Please provide an attack type, e.g., DDoS.")

    st.rerun()
