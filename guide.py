import os
import time
import streamlit as st
import json
from rag import rag_api
from pathlib import Path
from openai import OpenAI
import os
from dotenv import load_dotenv
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import streamlit.components.v1 as components

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


def typewriter_markdown(text: str, chunk_size: int = 6, delay: float = 0.01):
    placeholder = st.empty()
    acc = ""

    for i in range(0, len(text), chunk_size):
        acc += text[i:i + chunk_size]
        placeholder.markdown(acc)

        # ✅ 매 chunk마다 자동 스크롤
        ensure_chat_bottom_anchor()
        scroll_to_bottom_smooth()

        time.sleep(delay)

    return acc


def push(role: str, content: str):
    st.session_state.messages.append({"role": role, "content": content})

def visualize_attack_counts(_df, exclude_benign: bool = True, use_log_scale: bool = False):
    df = _df

    # attack_type 없으면 fallback
    target_col = "attack_type"

    counts = df[target_col].value_counts()

    if exclude_benign:
        counts = counts.drop(labels=["Benign"], errors="ignore")

    # ✅ matplotlib(plt)만 사용해서 bar plot

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(counts.index.astype(str), counts.values)
    ax.set_title(f'Detected Threats Distribution (Excluding Benign)', fontsize=14, fontweight='bold')
    ax.set_xlabel('Attack Type', fontsize=12)
    ax.set_ylabel('Count', fontsize=12)
    ax.tick_params(axis="x", rotation=45)

    if use_log_scale:
        ax.set_yscale("log")

    # 수치 라벨
    for i, v in enumerate(counts.values):
        ax.text(i, v, f"{int(v)}", ha="center", va="bottom", fontsize=9)

    fig.tight_layout()

    # ✅ PNG(base64)로 변환해서 반환
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)

    return {
        "target_col": target_col,
        "counts": counts.to_dict(),
        "image_base64": base64.b64encode(buf.getvalue()).decode("utf-8"),
    }

def render_messages():
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])


def analyze_log_csv(csv_path):
    df = pd.read_csv(csv_path)
    result = visualize_attack_counts(df)
    result["total_logs"] = len(df)

    if "prediction" in df.columns:
        attacks = df[df["prediction"] == 1]
        result["attack_count"] = len(attacks)
        result["attack_ratio"] = round(len(attacks) / len(df), 3)

    if "attack_type" in df.columns:
        result["attack_type_distribution"] = (
            df["attack_type"].value_counts().to_dict()
        )

    if "src_ip" in df.columns:
        result["top_source_ips"] = (
            df["src_ip"].value_counts().head(5).to_dict()
        )

    return result

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

# def typewriter_markdown(text: str, chunk_size: int = 6, delay: float = 0.01):
#     placeholder = st.empty()
#     acc = ""

#     for i in range(0, len(text), chunk_size):
#         acc += text[i:i + chunk_size]
#         placeholder.markdown(acc)

#         # ✅ 매 chunk마다 아래로 따라 내려가기
#         ensure_chat_bottom_anchor()
#         scroll_to_bottom_smooth()

#         time.sleep(delay)

#     return acc

def ensure_chat_bottom_anchor():
    # 채팅 맨 아래에 앵커를 항상 찍어둠
    st.markdown('<div id="chat-bottom"></div>', unsafe_allow_html=True)

def scroll_to_bottom_smooth():
    # key를 매번 바꿔서 컴포넌트가 "실제로" 다시 실행되게 함
    components.html(
        """
        <script>
        const el = window.parent.document.getElementById("chat-bottom");
        if (el) { el.scrollIntoView({ behavior: "smooth", block: "end" }); }
        </script>
        """,
        height=0,
    )


def handle_input(user_text):

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
                    "if user asks guide , call run_guide"
                    "if user asks cases, run_recent_cases"
                    'if user asks explain, run_explain'
                    'if user asks report, run_report'
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

        text = f"### Result{fn_args['attack_type']}\n\n{result['answer']}" f"**{fn_args['attack_type']}\n\n{result['answer']}"

        with st.chat_message("assistant"):
                final_text = typewriter_markdown(text, chunk_size=6, delay=0.01)

        if st.session_state.debug:
            text = f"**[DEBUG: contexts={len(result.get('contexts', []))}]**"
            final_text = typewriter_markdown(text, chunk_size=6, delay=0.01)
        st.session_state.messages.append({
                        "role": "assistant",
                        "content": text,
                    })
    else:
        placeholder = st.empty()
        acc = ""

        stream = client.chat.completions.create(
            model='gpt-4.1',
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant. Always respond in Korean."
                },
                {"role": "user", "content": user_text}
            ],
            stream=True,
        )

        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                acc += delta
                placeholder.markdown(acc)

        typewriter_markdown(acc)
        st.session_state.messages.append({
                        "role": "assistant",
                        "content": acc,
                    })
    st.rerun()
