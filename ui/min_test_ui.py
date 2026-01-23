import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io
import os
from dotenv import load_dotenv
from openai import OpenAI
import matplotlib.pyplot as plt

# 환경 변수 로드
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=OPENAI_API_KEY)


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
        height: 100vh;
        overflow: hidden;
        padding-top: 2rem;
        padding-bottom: 1rem;
    }
    div[data-testid="stChatMessageContainer"] {
        height: 50vh !important;  /* 브라우저 높이의 70% 고정 */
        max-height: 70vh !important;
        overflow-y: auto !important;
    }
    /* 3. 하단 입력바 영역을 하단에 딱 붙임 */
    div[data-testid="stChatInput"] {
        bottom: 20px;
    }
    /* 파일 업로더 디자인 압축 */
    div[data-testid="stFileUploader"] section { padding: 0; min-height: 35px; }
    div[data-testid="stFileUploader"] label { display: none; }
    div[data-testid="stFileUploader"] section > div { display: none; }
    
    /* --- 플로팅 대시보드 CSS --- */
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

# 세션 상태 관리
if "messages" not in st.session_state:
    st.session_state.messages = []
if "df" not in st.session_state:
    st.session_state.df = None

# --- UI 레이아웃 ---

# ============================================================
# 헤더
# ============================================================
st.markdown('<div class="main-header">🛡️ 네트워크 로그 이상 징후 탐지 시스템</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">ML 기반 보안 위협 탐지 및 대응 가이드</div>', unsafe_allow_html=True)


# 1. 메인 영역 (스크롤 가능한 대화창 영역)
chat_container = st.container(height = 100)
with chat_container:
    display_chat_messages(st.session_state.messages)
    
input_area = st.container()

with input_area:
    # 오른쪽 끝으로 배치
    col_input, col_upload = st.columns([9, 1])
    
    # --- 기존 input_area 내부 로직 수정 ---

    with col_input: 
    # 채팅 입력창
        if prompt := st.chat_input("보안 위협 질문 입력..."):
            # 1. 사용자 메시지 추가 및 화면 표시
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)
    
                # 2. OpenAI API 호출
                with st.chat_message("assistant"):
                    message_placeholder = st.empty() # 스트리밍 효과를 위한 빈 칸
                    full_response = ""
                
                    # API 요청 (전체 대화 맥락 포함)
                    try:
                        # 시스템 프롬프트 추가 (선택 사항: 챗봇에게 역할을 부여합니다)
                        system_msg = {"role": "system", "content": "너는 네트워크 보안 전문가야. 로그 분석 결과와 보안 위협에 대해 전문적으로 답변해줘."}
                    
                        completion = client.chat.completions.create(
                            model="gpt-4o-mini", # 또는 "gpt-3.5-turbo"
                            messages=[system_msg] + [
                                {"role": m["role"], "content": m["content"]}
                                for m in st.session_state.messages
                            ],
                            stream=True, # 실시간으로 글자가 써지는 효과
                        )
    
                        for response in completion:
                            full_response += (response.choices[0].delta.content or "")
                            message_placeholder.markdown(full_response + "▌")
                    
                        message_placeholder.markdown(full_response)
                    
                        # 3. 어시스턴트 답변을 세션에 저장
                        st.session_state.messages.append({"role": "assistant", "content": full_response})
                
                    except Exception as e:
                        st.error(f"OpenAI API 오류가 발생했습니다: {e}")
    
                # st.rerun()은 굳이 필요 없으므로 제거 (내용이 바로 업데이트됨)

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

# ============================================================
# [추가] 플로팅 대시보드 뷰
# ============================================================
with st.expander("🚨 로그 요약 및 대시보드", expanded=True):
    if st.session_state.df is not None:
        df = st.session_state.df
        
        # 1. 상단 주요 지표
        m1, m2 = st.columns(2)
        m1.metric("전체 로그", f"{len(df):,}건")
        
        # 위험 감지 로직 (label 컬럼에서 'Normal'이 아닌 것 추출)
        if 'label' in df.columns:
            # 대소문자 구분 없이 'Normal'이 포함되지 않은 행을 위험 로그로 간주
            threat_df = df[~df['label'].str.contains('Normal', case=False, na=False)]
            threat_count = len(threat_df)
            m2.metric("위협 감지", f"{threat_count}건", delta=f"{threat_count}건", delta_color="inverse")
            
            st.divider()
            
            # 2. 구체적인 위협 위치 및 내용 요약
            if threat_count > 0:
                st.write("⚠️ **주요 위협 탐지 위치:**")
                # 위협이 발생한 행(Index) 번호 나열 (상위 5개)
                indices = threat_df.index.tolist()
                idx_display = ", ".join([f"#{i+1}" for i in indices[:5]])
                if len(indices) > 5:
                    idx_display += " 등..."
                
                st.error(f"**로그 라인:** {idx_display}")
                
                # 3. 위협 유형별 요약 (Summary)
                st.write("📝 **위협 유형별 요약:**")
                summary = threat_df['label'].value_counts()
                for label, count in summary.items():
                    st.write(f"- {label}: {count}건")
            else:
                st.success("✅ 현재 모든 로그가 정상 범위 내에 있습니다.")
        else:
            # label 컬럼이 없는 경우 기본 정보 표시
            st.warning("'label' 컬럼을 찾을 수 없습니다. 분석 데이터 구성을 확인하세요.")
            st.write(f"**데이터 요약:** {len(df.columns)}개의 특성 분석 중")
            
    else:
        st.info("로그 파일을 업로드하면 실시간 요약이 활성화됩니다.\n 모델 연결 후 수정 필요")
    

# ============================================================
# 사이드바 - 시스템 정보 (생략 가능)
# ============================================================
with st.sidebar:
    st.header("시스템 정보")
    
    st.subheader("탐지 모델")
    st.write("- **모델:** RandomForest")
    st.write("- **데이터셋:** CICIDS2017")
    st.write("- **성능 지표:** 정확도, F1-Score, Silhouette Score")
    st.divider()
    st.subheader("대응 가이드 DB")
    st.write("- **DB:** MySQL")
    st.write("- **참조:** MITRE ATT&CK")
    st.write("- **참조:** KISA 침해사고대응 안내서")

# 푸터
st.divider()
st.markdown("""
<div style="text-align: center; color: #6b7280; font-size: 0.875rem; padding: 1rem 0;">
    <strong>HiFive</strong> | 
    5조 정예진 심재학 주재현 김지윤 김도현 김수경 이기찬 조민현
</div>
""", unsafe_allow_html=True)