import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from scapy.all import rdpcap
import tempfile
import os
import random # 가상 데이터용

# --- 페이지 설정 ---
st.set_page_config(page_title="PCAP 실시간 보안 분석", layout="wide")

# --- [추가] 데이터 변환 함수 (한글 깨짐 방지) ---
@st.cache_data
def convert_df(df):
    # 엑셀에서 열었을 때 한글이 깨지지 않도록 utf-8-sig로 인코딩합니다.
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
        for i, pkt in enumerate(packets[:100]):
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

# --- [수정] 파일 업로드 및 다운로드 (나란히 배치) ---
col1, col2 = st.columns([1, 1])
with col1:
    uploaded_file = st.file_uploader("네트워크 PCAP 로그 파일 업로드", type=["pcap"])

# 버튼 위치 정렬을 위한 공간 확보
with col2:
    st.write("##") # 업로드 버튼과 높이를 맞추기 위한 공백
    if st.session_state.log_data is not None:
        csv_file = convert_df(st.session_state.log_data)
        st.download_button(
            label="📥 분석 결과 보고서 다운로드 (CSV)",
            data=csv_file,
            file_name=f"security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )

if uploaded_file is not None:
    with st.spinner("패킷 파싱 및 분석 중..."):
        parsed_df = process_pcap(uploaded_file)
        if not parsed_df.empty:
            st.session_state.log_data = analyze_packets(parsed_df)
            st.success("패킷 분석이 완료되었습니다!")

# --- 대시보드 영역 ---
st.divider()
st.subheader("📊 실시간 분석 결과")

if st.session_state.log_data is None:
    st.info("파일을 업로드하면 패킷 분석 결과가 여기에 표시됩니다.")
else:
    data = st.session_state.log_data

    # --- 지표 카드 ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("평균 위험도", f"{data['위험도'].mean():.1f}%")
    c2.metric("총 패킷 수", f"{len(data)}건")
    c3.metric("이상 징후 탐지", f"{len(data[data['상태']=='Attack'])}건")
    c4.metric("최신 패킷 위험도", f"{data.iloc[-1]['위험도']}%")

    # --- 그래프 ---
    g1, g2 = st.columns(2)

    with g1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=data["로그번호"], y=data["위험도"], mode="lines+markers", name="위험도"))
        fig.add_hline(y=60, line_dash="dash", line_color="red", annotation_text="위험 기준선")
        fig.update_layout(title="패킷별 위험도 추이", xaxis_title="패킷 순서", yaxis_title="위험도 (%)")
        st.plotly_chart(fig, use_container_width=True)

    with g2:
        attack_df = data[data["상태"] == "Attack"]
        if not attack_df.empty:
            fig_bar = px.bar(attack_df["공격유형"].value_counts(), title="탐지된 공격 분포", color_discrete_sequence=["#FF4B4B"])
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("정상적인 트래픽 흐름입니다.")

    # --- 패킷 상세 테이블 ---
    st.divider()
    with st.expander("📝 패킷 상세 분석 데이터 (Raw Features)"):
        st.dataframe(data[["시간", "Source", "Destination", "Protocol", "Length", "위험도", "상태"]], use_container_width=True)

# --- 플로팅 챗봇 ---
with st.expander("💬 AI 보안 가이드 (PCAP 분석)", expanded=True):
    chat_box = st.container(height=300)

    for msg in st.session_state.chat_history:
        with chat_box.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("패킷 분석 결과에 대해 질문하세요"):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        with chat_box.chat_message("assistant"):
            if "위험" in prompt or "공격" in prompt:
                response = "분석된 PCAP 내 특정 패킷의 데이터 길이가 비정상적으로 큽니다. 이는 데이터 유출 시도 혹은 DDoS 예비 동작일 수 있으므로 해당 Source IP를 차단하십시오."
            else:
                response = "해당 패킷은 표준 프로토콜을 준수하고 있습니다. 추가적인 포트 스캔 여부를 모니터링하겠습니다."
            
            st.markdown(response)
            st.session_state.chat_history.append({"role": "assistant", "content": response})