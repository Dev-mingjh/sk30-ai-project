import streamlit as st
import matplotlib.pyplot as plt

def render_sidebar_charts(df):
    #사이드바에 Matplotlib 시각화 리포트 표시
    with st.sidebar:
        st.header("📊 보안 대시보드")
        if df is not None:
            # 1. 위협 유형 분포 (Pie Chart)
            if 'label' in df.columns:
                st.subheader("위협 유형 분포")
                fig1, ax1 = plt.subplots()
                df['label'].value_counts().plot(kind='pie', autopct='%1.1f%%', ax=ax1)
                ax1.set_ylabel('')
                st.pyplot(fig1)
            
            # 2. 통계 요약표
            st.divider()
            st.write("📋 데이터 통계")
            st.dataframe(df.describe(), use_container_width=True)
        else:
            st.info("파일을 업로드하면 대시보드가 활성화됩니다.")

def display_chat_messages(messages):
    # 채팅 기록 
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])



# 1. 페이지 설정
st.set_page_config(page_title="Network chatbot", layout="wide")

# 2. CSS: 입력창 하단 고정 및 간격 조정
st.markdown("""
    <style>
    .main .block-container {
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 100vh;
        padding-bottom: 5rem; /* 하단 입력바와 겹치지 않게 여백 추가 */
    }
    
    /* 파일 업로더 디자인 압축 */
    div[data-testid="stFileUploader"] section { padding: 0; min-height: 35px; }
    div[data-testid="stFileUploader"] label { display: none; }
    div[data-testid="stFileUploader"] section > div { display: none; }
    
    /* 하단 고정 영역 스타일 */
    .fixed-bottom {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background-color: white;
        padding: 10px 5%;
        z-index: 999;
        border-top: 1px solid #ddd;
    }
    </style>
    """, unsafe_allow_html=True)

# 세션 상태 관리
if "messages" not in st.session_state:
    st.session_state.messages = []
if "df" not in st.session_state:
    st.session_state.df = None

# --- UI 레이아웃 ---

# 1. 사이드바 시각화 호출
render_sidebar_charts(st.session_state.df)

# 2. 메인 영역 (스크롤 가능한 대화창 영역)
chat_container = st.container()
with chat_container:
    st.title("🛡️ 네트워크 로그 기반 위협 분석 챗봇")
    display_chat_messages(st.session_state.messages)
    
    # 초기 화면에서 타이틀과 바 사이를 벌려주기 위한 빈 공간 삽입
    if not st.session_state.messages:
        for _ in range(15): # 빈 줄 삽입으로 하단바를 아래로 밀어냄
            st.write("")
input_area = st.container()

with input_area:
    # 오른쪽 끝으로 배치
    col_input, col_upload = st.columns([9, 1])
    
    with col_input:
        # 채팅 입력창
        if prompt := st.chat_input("보안 위협 질문 입력..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # [확장 포인트] classifier.py 연결
            with st.chat_message("assistant"):
                response = f"입력하신 '{prompt}' 건에 대해 분석 중입니다."
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()

    with col_upload:
        # 입력창 오른쪽에 위치하는 파일 업로더
        uploaded_file = st.file_uploader("로그 파일 첨부하기", type=["csv", "pcap"], label_visibility="collapsed")
        if uploaded_file:
            st.session_state.df = pd.read_csv(uploaded_file)
            st.toast(f"✅ {uploaded_file.name} 로드 완료!", icon="📄")
            # 업로드 알림
            if not any(uploaded_file.name in m.get("content", "") for m in st.session_state.messages):
                st.session_state.messages.append({"role": "assistant", "content": f"📎 `{uploaded_file.name}` 파일이 분석 준비되었습니다."})
                st.rerun()