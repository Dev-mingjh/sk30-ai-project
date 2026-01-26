import streamlit as st
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv
from openai import OpenAI

# ============================================================
# 1. 초기 설정 및 환경 변수
# ============================================================
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)

def init_settings():
    """페이지 설정 및 세션 상태 초기화"""
    st.set_page_config(page_title="Network chatbot", layout="wide")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "df" not in st.session_state:
        st.session_state.df = None

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
    """채팅 기록 표시"""
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# ============================================================
# 3. 비즈니스 로직 함수
# ============================================================
def handle_ai_chat(prompt, chat_container):
    """OpenAI API 호출 및 스트리밍 응답 처리"""
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with chat_container:
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            try:
                system_msg = {"role": "system", "content": "너는 네트워크 보안 전문가야. 로그 분석 결과와 보안 위협에 대해 전문적으로 답변해줘."}
                completion = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[system_msg] + [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.messages
                    ],
                    stream=True,
                )

                for response in completion:
                    full_response += (response.choices[0].delta.content or "")
                    message_placeholder.markdown(full_response + "▌")
                
                message_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            
            except Exception as e:
                st.error(f"OpenAI API 오류가 발생했습니다: {e}")

def render_dashboard():
    """우측 하단 플로팅 대시보드 렌더링"""
    with st.expander("🚨 로그 요약 및 대시보드", expanded=True):
        if st.session_state.df is not None:
            df = st.session_state.df
            m1, m2 = st.columns(2)
            m1.metric("전체 로그", f"{len(df):,}건")
            
            if 'label' in df.columns:
                threat_df = df[~df['label'].str.contains('Normal', case=False, na=False)]
                threat_count = len(threat_df)
                m2.metric("위협 감지", f"{threat_count}건", delta=f"{threat_count}건", delta_color="inverse")
                
                st.divider()
                if threat_count > 0:
                    st.write("⚠️ **주요 위협 탐지 위치:**")
                    indices = threat_df.index.tolist()
                    idx_display = ", ".join([f"#{i+1}" for i in indices[:5]])
                    if len(indices) > 5: idx_display += " 등..."
                    st.error(f"**로그 라인:** {idx_display}")
                    
                    st.write("📝 **위협 유형별 요약:**")
                    summary = threat_df['label'].value_counts()
                    for label, count in summary.items():
                        st.write(f"- {label}: {count}건")
                else:
                    st.success("✅ 현재 모든 로그가 정상 범위 내에 있습니다.")
            else:
                st.warning("'label' 컬럼을 찾을 수 없습니다.")
        else:
            st.info("로그 파일을 업로드하면 실시간 요약이 활성화됩니다.\n 모델 연결 후 수정 필요")

def display_sidebar():
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

# ============================================================
# 4. 메인 실행 흐름
# ============================================================
def ui():
    init_settings()
    apply_custom_css()
    
    # 헤더 영역
    st.markdown('<div class="main-header">🛡️ 네트워크 로그 이상 징후 탐지 시스템</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">ML 기반 보안 위협 탐지 및 대응 가이드</div>', unsafe_allow_html=True)

    # 1. 메인 채팅 영역
    chat_container = st.container()
    with chat_container:
        display_chat_messages()

    # 2. 하단 입력 및 파일 업로드 영역
    input_area = st.container()
    with input_area:
        col_input, col_upload = st.columns([9.5, 0.5])
        
        with col_input:
            if prompt := st.chat_input("보안 위협 질문 입력..."):
                handle_ai_chat(prompt, chat_container)

        with col_upload:
            uploaded_file = st.file_uploader("로그 파일 첨부하기", type=["csv", "pcap"], label_visibility="collapsed")
            if uploaded_file:
                st.session_state.df = pd.read_csv(uploaded_file)
                st.toast(f"✅ {uploaded_file.name} 로드 완료!", icon="📄")
                
                # 중복 알림 방지 후 메시지 추가
                msg_content = f"📎 `{uploaded_file.name}` 파일이 분석 준비되었습니다."
                if not st.session_state.messages or st.session_state.messages[-1]["content"] != msg_content:
                    st.session_state.messages.append({"role": "assistant", "content": msg_content})
                    st.rerun()

    # 3. 플로팅 대시보드
    render_dashboard()

    # 4. 사이드바
    display_sidebar()

    # 푸터
    st.divider()
    st.markdown("""
        <div style="text-align: center; color: #6b7280; font-size: 0.875rem; padding: 1rem 0;">
            <strong>HighFive</strong> | 5조 정예진 심재학 주재현 김지윤 김도현 김수경 이기찬 조민현
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    ui()