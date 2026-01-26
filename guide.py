import os
import time
import streamlit as st
import json
from rag import rag_api
from pathlib import Path
from openai import OpenAI
import os
from dotenv import load_dotenv


def push_msg(role: str, content: str):
    st.session_state.messages.append({"role": role, "content": content})

@st.cache_resource
def load_bundle():
    return rag_api.create_rag_bundle()

bundle = load_bundle()
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)


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

# =========================================================
# 4. 이벤트 핸들러 및 메인 (Handlers & Main)
# =========================================================
def handle_input(user_text):
    # """사용자 입력에 따른 분기 처리"""
    # push_msg("user", user_text)
    # detected_attack = rag_api.extract_attack_type(user_text)
    # lowered = user_text.lower()

    # if detected_attack:
    #     if detected_attack != st.session_state.attack_type:
    #         st.session_state.attack_type = detected_attack
    #         st.session_state.pending_choice = False
    #         st.session_state.report_done = False
    #         st.session_state.guide_done = False
    #         st.session_state.recent_done = False
    #     run_explain()
    # else:
    #     if st.session_state.pending_choice:
    #         if any(k in lowered for k in CHOICE_REPORT):
    #             run_report()
    #             prompt_other_if_needed()
    #         elif any(k in lowered for k in CHOICE_MORE):
    #             run_recent_cases()
    #             prompt_other_if_needed()
    #         elif any(k in lowered for k in CHOICE_GUIDE):
    #             run_guide()
    #             prompt_other_if_needed()
    #         else:
    #             push("assistant", "Please choose **report**, **recent cases**, or **guide**.")
    #     else:
    #         if any(k in lowered for k in CHOICE_REPORT):
    #             run_report()
    #             prompt_other_if_needed()
    #         elif any(k in lowered for k in CHOICE_MORE):
    #             run_recent_cases()
    #             prompt_other_if_needed()
    #         elif any(k in lowered for k in CHOICE_GUIDE):
    #             run_guide()
    #             prompt_other_if_needed()
    #         else:
    #             push("assistant", "Please provide an attack type, e.g., DDoS.")
    #    """LLM Function Calling 기반 입력 처리"""
    push_msg("user", user_text)

    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a cybersecurity assistant. "
                    "Decide which function to call based on the user's intent. "
                    "Always extract the attack type."
                )
            },
            *st.session_state.messages,
        ],
        tools=TOOLS,
        tool_choice="auto",
    )

    msg = response.choices[0].message

    # ✅ Function Call 발생
    if msg.tool_calls:
        tool_call = msg.tool_calls[0]
        fn_name = tool_call.function.name
        fn_args = json.loads(tool_call.function.arguments)

        with st.spinner(f"Running {fn_name}..."):
            result = FUNCTION_MAP[fn_name](fn_args)

        push(
            "assistant",
            f"### Result ({fn_args['attack_type']})\n\n{result['answer']}"
        )

        if st.session_state.debug:
            push(
                "assistant",
                f"**[DEBUG: contexts={len(result.get('contexts', []))}]**"
            )

    # ✅ 일반 텍스트 응답
    else:
        push("assistant", msg.content)
    st.rerun()
