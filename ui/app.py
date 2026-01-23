import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from scapy.all import rdpcap
import tempfile
import os
import random
from dotenv import load_dotenv
from openai import OpenAI

# --- 환경 변수 및 OpenAI 클라이언트 설정 ---
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)

# --- 페이지 설정 ---
st.set_page_config(page_title="PCAP 실시간 보안 분석", layout="wide")

# --- 데이터 변환 함수 (한글 깨짐 방지) ---
@st.cache_data
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8-sig')

# --- 세션 상태 관리 ---
if "log_data" not in st.session_state:
    st.session_state.log_data = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": "PCAP 파일을 업로드하시면 패킷을 분석하여 위협 여부를 탐지합니다."}
    ]

# --- PCAP 파싱 함수 ---
def process_pcap(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pcap") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    try:
        packets = rdpcap(tmp_path)
        packet_list = []
        for i, pkt in enumerate(packets[:100]): # 성능을 위해 상위 100개만 샘플링
            if pkt.haslayer('IP'):
                packet_list.append({
                    "시간": datetime.fromtimestamp(float(pkt.time)).strftime('%H:%M:%S'),
                    "Source": pkt['IP'].src,
                    "Destination": pkt['IP'].dst,
                    "Protocol": pkt['IP'].proto,
                    "Length": len(pkt)
                })
        df = pd.DataFrame(packet_list)
        return df
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

# --- 분석 로직 (Mock) ---
def analyze_packets(df):
    df = df.copy()
    df["로그번호"] = range(1, len(df) + 1)
    # 1000바이트 이상이면 위험도가 높게 나오도록 시뮬레이션
    df["위험도"] = df["Length"].apply(lambda x: random.randint(70, 95) if x > 1000 else random.randint(10, 40))
    df["공격유형"] = df["위험도"].apply(lambda x: "Traffic Spike" if x >= 70 else "Normal")
    df["상태"] = df["위험도"].apply(lambda x: "Attack" if x >= 70 else "Normal")
    return df

# --- 플로팅 챗봇 CSS ---
st.markdown("""
<style>
[data-testid="stExpander"] {
    position: fixed;
    bottom: 30px;
    right: 30px;
    width: 400px;
    background: white;
    z-index: 9999;
    border-radius: 15px;
    box-shadow: 0px 10px 30px rgba(0,0,0,0.3);
}
</style>
""", unsafe_allow_html=True)

# --- 헤더 ---
st.title("🛡️ PCAP 패킷 기반 보안 탐지 대시보드")
st.divider()

col1, col2 = st.columns([1, 1])
with col1:
    uploaded_file = st.file_uploader("네트워크 PCAP 로그 파일 업로드", type=["pcap"])

with col2:
    st.write("##") 
    if st.session_state.log_data is not None:
        csv_file = convert_df(st.session_state.log_data)
        st.download_button(
            label="📥 분석 결과 보고서 다운로드 (CSV)",
            data=csv_file,
            file_name=f"security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )

if uploaded_file is not None:
    if st.session_state.log_data is None: # 중복 분석 방지
        with st.spinner("패킷 파싱 및 분석 중..."):
            parsed_df = process_pcap(uploaded_file)
            if not parsed_df.empty:
                st.session_state.log_data = analyze_packets(parsed_df)
                st.success("패킷 분석이 완료되었습니다!")

# --- 대시보드 영역 ---
if st.session_state.log_data is not None:
    data = st.session_state.log_data
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("평균 위험도", f"{data['위험도'].mean():.1f}%")
    c2.metric("총 패킷 수", f"{len(data)}건")
    c3.metric("이상 징후 탐지", f"{len(data[data['상태']=='Attack'])}건")
    c4.metric("최신 패킷 위험도", f"{data.iloc[-1]['위험도']}%")

    g1, g2 = st.columns(2)
    with g1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=data["로그번호"], y=data["위험도"], mode="lines+markers", name="위험도"))
        fig.add_hline(y=60, line_dash="dash", line_color="red", annotation_text="위험 기준선")
        st.plotly_chart(fig, use_container_width=True)
    with g2:
        attack_df = data[data["상태"] == "Attack"]
        if not attack_df.empty:
            fig_bar = px.bar(attack_df["공격유형"].value_counts(), title="탐지된 공격 분포")
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("정상 트래픽입니다.")

    with st.expander("📝 패킷 상세 분석 데이터"):
        st.dataframe(data, use_container_width=True)

# --- [수정] OpenAI 기반 플로팅 챗봇 ---
with st.expander("💬 AI 보안 가이드 (PCAP 분석)", expanded=True):
    chat_box = st.container(height=300)

    for msg in st.session_state.chat_history:
        with chat_box.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("패킷 분석 결과에 대해 질문하세요"):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with chat_box.chat_message("user"):
            st.markdown(prompt)
        
        with chat_box.chat_message("assistant"):
            # 1. 데이터 요약 생성 (AI에게 전달할 컨텍스트)
            if st.session_state.log_data is not None:
                df_summary = st.session_state.log_data.describe().to_string()
                attack_count = len(st.session_state.log_data[st.session_state.log_data['상태']=='Attack'])
                context = f"현재 분석된 패킷 데이터 요약:\n{df_summary}\n이상 징후 건수: {attack_count}건"
            else:
                context = "아직 업로드된 PCAP 데이터가 없습니다."

            # 2. 메시지 구성 (시스템 메시지에 보안 전문가 역할 부여)
            messages = [
                {"role": "system", "content": f"당신은 보안 분석 전문가입니다. 다음 분석 데이터를 바탕으로 사용자의 질문에 답변하세요.\n\n{context}"},
            ]
            # 최근 대화 내역 추가 (히스토리 유지)
            for m in st.session_state.chat_history[-5:]: 
                messages.append({"role": m["role"], "content": m["content"]})

            # 3. OpenAI API 호출
            try:
                response = client.chat.completions.create(
                    model="gpt-4o", # 또는 gpt-4-turbo
                    messages=messages,
                    temperature=0.7
                )
                ai_message = response.choices[0].message.content
                st.markdown(ai_message)
                st.session_state.chat_history.append({"role": "assistant", "content": ai_message})
            except Exception as e:
                st.error(f"AI 응답 생성 중 오류 발생: {e}")