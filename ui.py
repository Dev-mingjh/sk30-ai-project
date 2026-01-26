import streamlit as st
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv
from openai import OpenAI
from guide import *
from model import infer
import matplotlib.pyplot as plt
import seaborn as sns

# ============================================================
# 1. 초기 설정 및 환경 변수
# ============================================================
# load_dotenv()
# OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
# client = OpenAI(api_key=OPENAI_API_KEY)


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

    infer._load_model()


# ============================================================
# 2. UI 및 CSS 함수
# ============================================================
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

def display_chat_messages():
    # 초기 안내
    if not st.session_state.messages:
        push_msg("assistant", "안녕하세요.   분석할 로그 파일을 업로드 해주세요")
        st.rerun()
    # 채팅 기록 표시
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# ============================================================
# 3. 비즈니스 로직 함수
# ============================================================
# def handle_ai_chat(prompt, chat_container):
#     """OpenAI API 호출 및 스트리밍 응답 처리"""
#     st.session_state.messages.append({"role": "user", "content": prompt})
    
#     with chat_container:
#         with st.chat_message("user"):
#             st.markdown(prompt)

#         with st.chat_message("assistant"):
#             message_placeholder = st.empty()
#             full_response = ""
            
#             try:
#                 system_msg = {"role": "system", "content": "너는 네트워크 보안 전문가야. 로그 분석 결과와 보안 위협에 대해 전문적으로 답변해줘."}
#                 completion = client.chat.completions.create(
#                     model="gpt-4o-mini",
#                     messages=[system_msg] + [
#                         {"role": m["role"], "content": m["content"]}
#                         for m in st.session_state.messages
#                     ],
#                     stream=True,
#                 )

#                 for response in completion:
#                     full_response += (response.choices[0].delta.content or "")
#                     message_placeholder.markdown(full_response + "▌")
                
#                 message_placeholder.markdown(full_response)
#                 st.session_state.messages.append({"role": "assistant", "content": full_response})
            
#             except Exception as e:
#                 st.error(f"OpenAI API 오류가 발생했습니다: {e}")

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
        st.write("- **참조:** MITRE ATT&CK")
        st.write("- **참조:** KISA 침해사고대응 안내서")

        
def set_header():
    # 헤더 영역
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
     # 1. 메인 채팅 영역
    chat_container = st.container()
    with chat_container:
        display_chat_messages()

    # 2. 하단 입력 및 파일 업로드 영역
    input_area = st.container()
    with input_area:
        col_input, col_upload = st.columns([9.5, 0.5])
        
        with col_input:
            if prompt := st.chat_input("메시지를 입력하세요..."):
                handle_input(prompt)
                #handle_ai_chat(prompt, chat_container)
                st.rerun()

        with col_upload:
            uploaded_file = st.file_uploader("로그 파일 첨부하기", type=["csv", "pcap"], label_visibility="collapsed")
            if uploaded_file:
                if "last_processed_file" not in st.session_state:
                    st.session_state.last_processed_file = None

                # 현재 업로드된 파일이 이전에 처리한 파일과 다를 때만 실행
                if st.session_state.last_processed_file != uploaded_file.name:
                    st.session_state.df = pd.read_csv(uploaded_file)
                    st.toast(f"✅ {uploaded_file.name} 로드 완료!", icon="📄")
                    
                    # 모델 예측 실행
                    df = infer.predict_attack_type(st.session_state.df)
                    st.session_state.df = df
                    
                    st.toast("✅ 모델 예측 완료", icon="🤖")

                    attacks = df['attack_type'].unique()
                    content = f'`{uploaded_file.name}` 분석 완료\n\n 로그 분석 결과 입니다'
                    
                    if len(attacks) == 1:
                        cotent += "악성 로그가 탐지 되지 않았습니다."
                    else: 
                        content += '탐지된 악성 공격 리스트 입니다\n\n'
                        for num in range(len(attacks)):
                            if attacks[num] != 'Benign':
                                content += f'{num}. {attacks[num]}\n\n'
                        content += "상세 설명 원하시는 공격이 있을 경우 입력해주세요"
                        # 메시지 추가
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": content,
                    })
                    # visualize(df)
                    # 현재 파일 이름을 기록하여 다음 리런 때 중복 실행 방지
                    st.session_state.last_processed_file = uploaded_file.name
                    
                    # 상태 업데이트 후 화면 갱신
                    st.rerun()

def visualize(df):
    # 컬럼명 자동 지정 (마지막 컬럼이 attack_type인 경우)
    target_col = df.columns[-1]
    counts = df[target_col].value_counts()

    # 2. 시각화 설정 (Figure 객체 생성)
    fig, ax = plt.subplots(figsize=(10, 6))

    # 3. Seaborn 막대 그래프 그리기
    sns.barplot(
        x=counts.index, 
        y=counts.values, 
        ax=ax, 
        hue=counts.index,     # x축 변수를 hue에도 똑같이 지정
        palette='viridis',    # 사용할 색상 팔레트
        legend=False          # hue를 쓰면 자동으로 생기는 범례를 숨김
    )   

    # 4. Y축을 로그 스케일로 설정 (가장 중요한 부분)
    ax.set_yscale("log")

    # 5. 그래프 디테일 추가
    ax.set_title(f'Log-Scaled Distribution of {target_col}', fontsize=14)
    ax.set_xlabel('Attack Type', fontsize=12)
    ax.set_ylabel('Count (Log Scale)', fontsize=12)
    plt.xticks(rotation=45) # 라벨이 겹치지 않게 회전

    # 그래프 상단에 실제 수치 표시 (선택 사항)
    for i, v in enumerate(counts.values):
        ax.text(i, v, f'{v:,}', ha='center', va='bottom', fontsize=10)

    # 6. Streamlit 출력
    st.pyplot(fig)

def execute_chatbot():
    init_settings()
    apply_custom_css()
    set_header()
    set_chat_upload()
    set_sidebar()
    set_putter()
