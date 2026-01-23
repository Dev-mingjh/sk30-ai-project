"""
네트워크 로그 이상 징후 탐지 & 대응 가이드 시스템
Streamlit 기반 웹 애플리케이션

요구사항:
pip install streamlit pandas numpy scikit-learn plotly openai python-dotenv 등
"""

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

# 환경 변수 로드
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=OPENAI_API_KEY)

# 페이지 설정
st.set_page_config(
    page_title="네트워크 로그 이상 징후 탐지",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS
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
    .metric-card {
        background-color: #f9fafb;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 1px solid #e5e7eb;
    }
    .alert-box {
        background-color: #fef2f2;
        border-left: 4px solid #ef4444;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .chat-message {
        padding: 1rem;
        margin-bottom: 0.5rem;
        border-radius: 0.5rem;
    }
    .user-message {
        background-color: #dbeafe;
        margin-left: 2rem;
    }
    .assistant-message {
        background-color: #f3f4f6;
        margin-right: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# 세션 스테이트 초기화
if 'messages' not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "안녕하세요! 네트워크 보안 분석 AI 어시스턴트입니다. 로그 분석 결과나 보안 대응 방법에 대해 질문해주세요."
        }
    ]
if 'threat_data' not in st.session_state:
    st.session_state.threat_data = None

# ============================================================
# 헤더
# ============================================================
st.markdown('<div class="main-header">🛡️ 네트워크 로그 이상 징후 탐지 시스템</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">ML 기반 실시간 보안 위협 탐지 및 대응 가이드</div>', unsafe_allow_html=True)

# ============================================================
# 1. 파일 업로드 섹션 (상단)
# ============================================================
st.header("📁 로그 파일 업로드")
st.markdown("네트워크 로그 파일(CSV, PCAP)을 업로드하여 RandomForest ML 모델 기반 이상 징후 분석을 시작하세요.")

uploaded_file = st.file_uploader(
    "파일 선택",
    type=["csv", "pcap"],
    help="CSV 또는 PCAP 형식의 네트워크 로그 파일을 업로드하세요."
)

if uploaded_file is not None:
    st.success(f"✅ 파일 업로드 완료: {uploaded_file.name} ({uploaded_file.size / 1024:.2f} KB)")
    
    # 분석 버튼
    if st.button("🔍 로그 분석 시작", type="primary"):
        with st.spinner("ML 모델로 로그 분석 중..."):
            # 실제 환경에서는 여기서 ML 모델 실행
            # 현재는 목 데이터 생성
            import time
            time.sleep(2)
            
            # 목 데이터 생성
            st.session_state.threat_data = {
                'risk_score': 78,
                'total_logs': 15420,
                'threats_detected': 234,
                'attack_types': {
                    'DDoS': 89,
                    'Port Scan': 67,
                    'Brute Force': 45,
                    'SQL Injection': 23,
                    'XSS': 10
                },
                'timeline': {
                    '00:00': 12, '04:00': 8, '08:00': 35, '12:00': 52,
                    '16:00': 68, '20:00': 45, '23:59': 14
                }
            }
        
        st.success("✅ 분석 완료!")
        st.rerun()

# ============================================================
# 2. 로그 데이터 시각화 (중간)
# ============================================================
st.header("📊 분석 결과 대시보드")

if st.session_state.threat_data:
    data = st.session_state.threat_data
    
    # 경고 메시지
    if data['threats_detected'] > 0:
        st.markdown(f"""
        <div class="alert-box">
            <strong>⚠️ 보안 위협 감지!</strong><br>
            총 {data['threats_detected']}개의 이상 징후가 탐지되었습니다. 즉시 대응이 필요합니다.
        </div>
        """, unsafe_allow_html=True)
    
    # 통계 카드
    col1, col2, col3 = st.columns(3)
    
    with col1:
        risk_level = "높음" if data['risk_score'] >= 70 else "중간" if data['risk_score'] >= 40 else "낮음"
        risk_color = "🔴" if data['risk_score'] >= 70 else "🟡" if data['risk_score'] >= 40 else "🟢"
        st.metric(
            label="위험 점수",
            value=f"{data['risk_score']}/100",
            delta=f"{risk_color} {risk_level}"
        )
    
    with col2:
        st.metric(
            label="전체 로그",
            value=f"{data['total_logs']:,}"
        )
    
    with col3:
        threat_percentage = (data['threats_detected'] / data['total_logs']) * 100
        st.metric(
            label="위협 탐지",
            value=f"{data['threats_detected']}",
            delta=f"{threat_percentage:.2f}%",
            delta_color="inverse"
        )
    
    st.divider()
    
    # 차트
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.subheader("공격 유형 분포")
        
        # 파이 차트
        attack_df = pd.DataFrame({
            'Attack Type': list(data['attack_types'].keys()),
            'Count': list(data['attack_types'].values())
        })
        
        fig_pie = px.pie(
            attack_df,
            values='Count',
            names='Attack Type',
            color_discrete_sequence=px.colors.sequential.RdBu,
            hole=0.3
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with chart_col2:
        st.subheader("시간대별 위협 탐지")
        
        # 바 차트
        timeline_df = pd.DataFrame({
            'Time': list(data['timeline'].keys()),
            'Threats': list(data['timeline'].values())
        })
        
        fig_bar = px.bar(
            timeline_df,
            x='Time',
            y='Threats',
            color='Threats',
            color_continuous_scale='Reds',
            labels={'Threats': '탐지된 위협'}
        )
        fig_bar.update_layout(showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # 상세 공격 유형 테이블
    st.subheader("탐지된 공격 상세 정보")
    attack_detail_df = pd.DataFrame({
        '공격 유형': list(data['attack_types'].keys()),
        '탐지 횟수': list(data['attack_types'].values()),
        '위험도': ['높음' if v > 50 else '중간' if v > 20 else '낮음' 
                   for v in data['attack_types'].values()],
        '대응 상태': ['대기 중'] * len(data['attack_types'])
    })
    st.dataframe(attack_detail_df, use_container_width=True)

else:
    st.info("📤 로그 파일을 업로드하여 분석을 시작하세요.")

# ============================================================
# 3. 챗봇 기능 (아래)
# ============================================================
st.header("💬 보안 대응 가이드 챗봇")
st.markdown("**AI 어시스턴트**")

# 채팅 메시지 표시
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f'<div class="chat-message user-message">👤 {message["content"]}</div>', 
                       unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-message assistant-message">🤖 {message["content"]}</div>', 
                       unsafe_allow_html=True)

# 채팅 입력
user_input = st.chat_input("보안 위협에 대해 질문하세요...")

def generate_response(question, threat_data):
    """OpenAI API를 사용한 응답 생성"""
    try:
        # 시스템 프롬프트 생성
        system_content = """당신은 네트워크 보안 전문가 AI 어시스턴트입니다.
MITRE ATT&CK 프레임워크와 KISA 침해사고대응 안내서를 기반으로 사용자에게 보안 조언을 제공합니다.

주요 역할:
1. 네트워크 로그 분석 결과 설명
2. 탐지된 공격 유형에 대한 상세 정보 제공
3. 즉각적인 대응 방법 가이드
4. KISA 신고 절차 안내
5. MITRE ATT&CK 기반 공격 전술 및 기법 설명

답변 시 다음 형식을 따르세요:
- 명확하고 구조화된 답변
- 실행 가능한 단계별 가이드
- 한국어로 친절하게 설명
- 필요시 KISA나 MITRE ATT&CK 참조"""

        # 위협 데이터가 있는 경우 컨텍스트 추가
        if threat_data:
            threat_context = f"""

현재 시스템에서 탐지된 위협 정보:
- 전체 로그 수: {threat_data.get('total_logs', 0):,}개
- 탐지된 위협: {threat_data.get('threats_detected', 0)}개
- 위험 점수: {threat_data.get('risk_score', 0)}/100
- 탐지된 공격 유형: {', '.join(threat_data.get('attack_types', {}).keys()) if threat_data.get('attack_types') else '없음'}
"""
            system_content += threat_context
        
        # OpenAI API 호출
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # 또는 "gpt-4" 등 원하는 버젼 첨부
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": question}
            ],
            temperature=0.7,
            max_tokens=800
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        # API 오류 시 폴백 응답
        return f"""⚠️ OpenAI API 연결 중 오류가 발생했습니다: {str(e)}

API 키가 올바르게 설정되었는지 확인해주세요.
.env 파일에 OPENAI_API_KEY를 설정하거나 환경 변수로 등록해주세요.
"""

if user_input:
    # 사용자 메시지 추가
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # OpenAI API로 응답 생성
    with st.spinner("AI가 답변을 생성하는 중..."):
        response = generate_response(user_input, st.session_state.threat_data)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
    
    st.rerun()

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
    
    with st.expander("주요 공격 유형"):
        st.write("""
        - **DDoS:** 분산 서비스 거부 공격
        - **Port Scan:** 포트 스캔 공격
        - **Brute Force:** 무차별 대입 공격
        - **SQL Injection:** SQL 인젝션
        - **XSS:** 크로스 사이트 스크립팅
        """)

# 푸터
st.divider()
st.markdown("""
<div style="text-align: center; color: #6b7280; font-size: 0.875rem; padding: 1rem 0;">
    <strong>HiFive</strong> | 
    5조 정예진 심재학 주재현 김지윤 김도현 김수경 이기찬 조민현
</div>
""", unsafe_allow_html=True)