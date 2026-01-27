import os
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import time
import base64
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from io import BytesIO
from openai import OpenAI

from analyze import *
from guide import *
from model import infer

client = None

@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

def init_settings():
    """페이지 설정 및 세션 상태 초기화"""
    st.set_page_config(page_title="Network chatbot", layout="wide")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "df" not in st.session_state:
        st.session_state.df = None
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
    if "last_processed_file" not in st.session_state:
        st.session_state.last_processed_file = None
    infer._load_model()
    load_dotenv()
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    global client
    client = OpenAI(api_key=OPENAI_API_KEY)



def apply_custom_css():
    """기존 CSS 스타일 그대로 적용"""
    st.markdown("""
        <style>
        .main-header {
            font-size: 2.5rem;
            font-weight: bold;
            color: #1e40af;
            margin-bottom: 0.5rem;
        }
        .sub-header {
            font-size: 1rem;
            color: #6b7280;
            margin-bottom: 2rem;
        }
        .main .block-container {
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 100vh;
            padding-bottom: 5rem;
        }
        
        /* 파일 업로더 디자인 압축 */
        div[data-testid="stFileUploader"] section { padding: 0; min-height: 35px; }
        div[data-testid="stFileUploader"] label { display: none; }
        div[data-testid="stFileUploader"] section > div { display: none; }
        
        /* 플로팅 대시보드 CSS */
        div[data-testid="stExpander"] {
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 350px;
            background: white;
            z-index: 9999;
            border-radius: 15px;
            box-shadow: 0px 10px 30px rgba(0,0,0,0.3);
        }
        </style>
        """, unsafe_allow_html=True)

def typewriter_markdown(text: str, chunk_size: int = 6, delay: float = 0.01):
    placeholder = st.empty()
    acc = ""

    for i in range(0, len(text), chunk_size):
        acc += text[i:i + chunk_size]
        placeholder.markdown(acc)

        ensure_chat_bottom_anchor()
        scroll_to_bottom_smooth()

        time.sleep(delay)

    return acc



def ensure_chat_bottom_anchor():
    st.markdown('<div id="chat-bottom"></div>', unsafe_allow_html=True)

def scroll_to_bottom_smooth():
    components.html(
        """
        <script>
        const el = window.parent.document.getElementById("chat-bottom");
        if (el) { el.scrollIntoView({ behavior: "smooth", block: "end" }); }
        </script>
        """,
        height=0,
    )

def push_msg(role, content, visualize=False):
    """메시지를 세션 상태에 추가"""
    st.session_state.messages.append({
        "role": role, 
        "content": content, 
        "visualize": visualize
    })

def visualize_attack_counts(_df, exclude_benign: bool = True, use_log_scale: bool = False):
    df = _df
    target_col = "attack_type"
    counts = df[target_col].value_counts()

    if exclude_benign:
        counts = counts.drop(labels=["Benign"], errors="ignore")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(counts.index.astype(str), counts.values)
    ax.set_title(f'Detected Threats Distribution (Excluding Benign)', fontsize=14, fontweight='bold')
    ax.set_xlabel('Attack Type', fontsize=12)
    ax.set_ylabel('Count', fontsize=12)
    ax.tick_params(axis="x", rotation=45)

    if use_log_scale:
        ax.set_yscale("log")

    for i, v in enumerate(counts.values):
        ax.text(i, v, f"{int(v)}", ha="center", va="bottom", fontsize=9)

    fig.tight_layout()

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)

    return {
        "target_col": target_col,
        "counts": counts.to_dict(),
        "image_base64": base64.b64encode(buf.getvalue()).decode("utf-8"),
    }

def display_chat_messages():
    if not st.session_state.messages:
        typewriter_markdown("안녕하세요.   분석할 로그 파일을 업로드 해주세요")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg.get("is_report") and st.session_state.df is not None:
                csv_data = convert_df_to_csv(st.session_state.df)
                st.download_button(
                    label="📥 분석 결과 리포트 다운로드 (CSV)",
                    data=csv_data,
                    file_name=f"analysis_result_{st.session_state.last_processed_file}",
                    mime="text/csv",
                    key=f"download_btn_{st.session_state.last_processed_file}" 
                )
            if msg.get("type") == "plot" and msg.get("plot_base64"):
                if msg.get("content"):
                    st.markdown(msg["content"])
                img_bytes = base64.b64decode(msg["plot_base64"])
                st.image(BytesIO(img_bytes), width="stretch")
            else:
                st.markdown(msg["content"])

def render_dashboard():
    with st.expander("🚨 로그 요약 및 대시보드", expanded=True):
        df = st.session_state.df
        if df is None:
            st.info("로그 파일을 업로드하면 실시간 요약이 활성화됩니다.")
            return

        c1, c2 = st.columns(2)
        c1.metric("전체 로그", f"{len(df):,}건")

        if "attack_type" in df.columns:
            threat_df = df[df["attack_type"].str.lower() != "benign"]

            c2.metric(
                "위협 감지",
                f"{len(threat_df)}건",
                delta_color="inverse"
            )

            if len(threat_df) > 0:
                st.divider()
                st.write("🧨 **공격 유형 분포**")

                for k, v in threat_df["attack_type"].value_counts().items():
                    st.write(f"- {k}: {v}건")
            else:
                st.success("✅ 모든 트래픽이 정상(Benign)입니다.")


def set_sidebar():
    """사이드바 정보 표시"""
    with st.sidebar:
        st.header("시스템 정보")
        st.subheader("탐지 모델")
        st.write("- **모델:** RandomForest")
        st.write("- **데이터셋:** CICIDS2017")
        st.write("- **성능 지표:** F1 Score, Recall")
        st.divider()
        st.subheader("대응 가이드 DB")
        st.write("- **DB:** Vector DB")
        st.write("- **참조:** 정보통신분야 침해사고 대응 안내서(개정본)")
        st.write("- **참조:** 한국인터넷진흥원 훈련 분야별 대응 가이드")

        
def set_header():
    st.markdown('<div class="main-header">🛡️ 네트워크 로그 이상 징후 탐지 시스템</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">※ PCAP/패킷 로그를 CICFlowMeter로 변환한 flow-level feature CSV 파일만 지원합니다 ※</div>', unsafe_allow_html=True)


def set_putter():
    st.divider()
    st.markdown("""
        <div style="text-align: center; color: #6b7280; font-size: 0.875rem; padding: 1rem 0;">
            <strong>HighFive</strong> | 5조 정예진 심재학 주재현 김지윤 김도현 김수경 이기찬 조민현
        </div>
        """, unsafe_allow_html=True)



def set_chat_upload():
    chat_container = st.container()
    with chat_container:
        display_chat_messages()

    input_area = st.container()
    with input_area:
        col_input, col_upload = st.columns([9.5, 0.5])
        
        with col_input:
            if prompt := st.chat_input("메시지를 입력하세요..."):
                handle_input(prompt)
                st.rerun()

        with col_upload:
            uploaded_file = st.file_uploader("로그 파일 첨부하기", type=["csv", "pcap"], label_visibility="collapsed")
            if uploaded_file:
                if "last_processed_file" not in st.session_state:
                    st.session_state.last_processed_file = None

                if st.session_state.last_processed_file != uploaded_file.name:
                    st.session_state.df = pd.read_csv(uploaded_file)
                    st.toast(f"✅ {uploaded_file.name} 로드 완료!", icon="📄")
                    
                    predicted_df = infer.add_pred_column(st.session_state.df)
                    st.session_state.df = predicted_df 
                    st.session_state.csv_path = 'user_log_with_pred.csv'
                    st.toast("✅ 모델 예측 완료", icon="🤖")
                    result = visualize_attack_counts(st.session_state.df)
                    attacks = predicted_df['attack_type'].unique()
                    content = f'{uploaded_file.name}` 분석 완료\n\n'
                    
                    if len(attacks) <= 1 and attacks[0] == 'Benign':
                        content += "✅ 악성 로그가 탐지되지 않았습니다."
                    else: 
                        content += '🧨 **탐지된 악성 공격 리스트:**\n\n'
                        for atk in attacks:
                            if atk != 'Benign':
                                count = len(predicted_df[predicted_df['attack_type'] == atk])
                                content += f'- {atk} ({count}건)\n'

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": content,
                    })

                    st.session_state.messages.append({
                        "role": "assistant",
                        "type": "plot",
                        "content": "공격 유형별 탐지 건수 그래프",
                        "plot_base64": result["image_base64"],
                    })

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "\n상세 설명이 필요한 공격명을 입력하시거나, 다운로드 버튼을 눌러 전체 결과(CSV)를 다운로드하세요.",
                        "is_report": True
                    })
                    st.session_state.last_processed_file = uploaded_file.name
                    
                    st.rerun()

def handle_input(user_text):
    push_msg("user", user_text)

    integrated_tools = TOOLS + ANALYZE_TOOLS

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system", 
                "content": (
                    "당신은 네트워크 보안 전문가입니다. "
                    "1. '내 파일', '내 로그', '이 데이터' 등 업로드된 파일 내용을 묻는 경우 'analyze_user_file'을 호출하세요. "
                    "2. 그런 언급 없이 일반적인 정의나 대응 방법을 물으면 가이드(guide) 관련 함수를 호출하세요. "
                    "3. analyze_user_file의 결과(JSON)를 받으면, 수치를 나열하지 말고 'Flow Packets/s가 매우 높아 플러딩 공격으로 의심된다'는 식으로 전문가답게 해석해 답변하세요."
                )
            },
            *st.session_state.messages
        ],
        tools=integrated_tools,
        tool_choice="auto",
    )

    msg = response.choices[0].message

    if msg.tool_calls:
        tool_call = msg.tool_calls[0]
        fn_name = tool_call.function.name
        fn_args = json.loads(tool_call.function.arguments)

        with st.spinner(f"분석 중: {fn_name}..."):
            if fn_name == "analyze_user_file":
                raw_analysis = analyze_user_file_stats(fn_args["attack_type"])
                
                second_response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "당신은 제공된 통계 데이터를 기반으로 근거를 제시하는 보안 분석가입니다. '현상 나열'이 아니라 '데이터 기반 해석'을 하세요."},
                        *st.session_state.messages,
                        msg,
                        {
                            "role": "tool", 
                            "tool_call_id": tool_call.id, 
                            "name": fn_name, 
                            "content": f"이것은 실제 파일에서 추출한 데이터입니다. 수치(평균, 최대값)를 언급하며 DDoS/DoS 등의 근거를 설명하세요: {raw_analysis['answer']}"
                        }
                    ]
                )
                final_answer = second_response.choices[0].message.content
            else:
                result = FUNCTION_MAP[fn_name](fn_args)
                final_answer = result['answer']
        typewriter_markdown(final_answer, chunk_size=6, delay=0.01)
        st.session_state.messages.append({
                        "role": "assistant",
                        "content": final_answer,
                    })
    else:
        typewriter_markdown(msg.content, chunk_size=6, delay=0.01)
        st.session_state.messages.append({
                        "role": "assistant",
                        "content": msg.content,
                    })
    
    st.rerun()

def execute_chatbot():
    init_settings()
    apply_custom_css()
    set_header()
    set_chat_upload()
    set_sidebar()
    set_putter()
