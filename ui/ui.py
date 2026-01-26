import sys
import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)


from model.infer import predict_attack_type

# 1. 초기 설정 및 환경 변수
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)

def init_settings():
    st.set_page_config(page_title="Network chatbot", layout="wide")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "df" not in st.session_state:
        st.session_state.df = None

    # 업로드 중복 방지용
    if "last_uploaded_file" not in st.session_state:
        st.session_state.last_uploaded_file = None

# 2. UI 및 CSS
def apply_custom_css():
    st.markdown("""<style>
        .main-header { font-size:2.5rem;font-weight:bold;color:#1e40af; }
        .sub-header { font-size:1rem;color:#6b7280;margin-bottom:2rem; }
        div[data-testid="stExpander"] {
            position:fixed;bottom:30px;right:30px;width:350px;
            background:white;z-index:9999;border-radius:15px;
            box-shadow:0px 10px 30px rgba(0,0,0,0.3);
        }
    </style>""", unsafe_allow_html=True)

def display_chat_messages():
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# 3. AI 채팅
def handle_ai_chat(prompt, chat_container):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with chat_container:
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            full = ""

            system_msg = {
                "role": "system",
                "content": "너는 네트워크 보안 전문가야. 로그 분석 결과와 보안 위협을 근거 기반으로 설명해."
            }

            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[system_msg] + st.session_state.messages,
                stream=True,
            )

            for chunk in completion:
                full += chunk.choices[0].delta.content or ""
                placeholder.markdown(full + "▌")

            placeholder.markdown(full)
            st.session_state.messages.append(
                {"role": "assistant", "content": full}
            )

# 4. 플로팅 대시보드 (attack_type 활용)
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

# 5. 사이드바
def display_sidebar():
    with st.sidebar:
        st.header("시스템 정보")
        st.write("- **모델:** RandomForest (CICIDS2017)")
        st.write("- **출력:** attack_type")
        st.divider()
        st.write("참조 DB")
        st.write("- MITRE ATT&CK")
        st.write("- KISA 침해대응 가이드")

# 6. 메인 UI
def ui():
    init_settings()
    apply_custom_css()

    st.markdown(
        '<div class="main-header">🛡️ 네트워크 로그 이상 징후 탐지 시스템</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="sub-header">ML 기반 보안 위협 탐지 및 대응 가이드</div>',
        unsafe_allow_html=True
    )

    # 채팅 영역
    chat_container = st.container()
    with chat_container:
        display_chat_messages()

    # 입력 / 업로드 영역
    input_area = st.container()
    with input_area:
        col_input, col_upload = st.columns([9.5, 0.5])

        with col_input:
            if prompt := st.chat_input("보안 위협 질문 입력..."):
                handle_ai_chat(prompt, chat_container)

        with col_upload:
            uploaded = st.file_uploader(
                "로그 업로드",
                type="csv",
                label_visibility="collapsed"
            )

            # 같은 파일이면 다시 처리하지 않음
            if uploaded and uploaded.name != st.session_state.last_uploaded_file:
                df = pd.read_csv(uploaded)
                df = predict_attack_type(df)

                st.session_state.df = df
                st.session_state.last_uploaded_file = uploaded.name

                st.toast("✅ 모델 예측 완료", icon="🤖")

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"📎 `{uploaded.name}` 분석 완료 (attack_type 생성)"
                })

                st.rerun()

    render_dashboard()
    display_sidebar()

    st.divider()
    st.markdown(
        "<div style='text-align:center;color:#6b7280;font-size:0.85rem; padding: 1rem 0;'>"
        "<strong>HighFive</strong> | 5조 정예진 심재학 주재현 김지윤 김도현 김수경 이기찬 조민현 "
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    ui()