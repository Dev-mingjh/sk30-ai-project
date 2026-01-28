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

from guide import *
from model import infer

# OpenAI API Client 전역 변수 (init_settings에서 초기화)
client = None

# [Utility] DataFrame -> CSV bytes 변환 (다운로드 버튼에 사용)
@st.cache_data
def convert_df_to_csv(df):
    """
    분석 결과 DataFrame을 CSV(bytes)로 변환.
    - index 제외
    - utf-8-sig: 엑셀에서 한글 깨짐 방지
    - cache_data: 같은 df에 대해 반복 변환 비용 절감
    """
    return df.to_csv(index=False).encode('utf-8-sig')

# [Init] 페이지 설정/세션 상태/모델/환경변수/OpenAI 클라이언트 초기화
def init_settings():
    """
    앱 구동 시 1회 호출되는 초기화 함수.
    - Streamlit 페이지 설정
    - 세션 상태(session_state) 기본값 세팅
    - 탐지 모델 로드
    - .env 로드 후 OpenAI API client 생성
    """
    st.set_page_config(page_title="Network chatbot", layout="wide")

    # 채팅 메시지 저장소
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 업로드된 CSV를 읽어둔 DF
    if "df" not in st.session_state:
        st.session_state.df = None

    # 사용자가 선택한 공격 유형 등 상태 값들
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

    # 디버그 모드
    if "debug" not in st.session_state:
        st.session_state.debug = False

    # 마지막으로 처리한 업로드 파일명(중복 처리 방지용)
    if "last_processed_file" not in st.session_state:
        st.session_state.last_processed_file = None

    # ML 모델 로드(추론용)
    infer.load_model('./model/cicids2017_rf_model_v2.pkl')

    # 환경변수 로드 후 OpenAI 클라이언트 초기화
    load_dotenv()
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

    global client
    client = OpenAI(api_key=OPENAI_API_KEY)


# [UI] CSS 커스터마이징 (헤더/업로더 최소화 등)
def apply_custom_css():
    """
    Streamlit 기본 UI를 커스터마이징하기 위한 CSS 삽입.
    - 헤더 스타일
    - 파일 업로더 영역을 얇게/불필요한 요소 숨김
    - 전체 컨테이너 높이/패딩 조절
    """
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
        div[data-testid="stFileUploader"] section { padding: 0; min-height: 35px; }
        div[data-testid="stFileUploader"] label { display: none; }
        div[data-testid="stFileUploader"] section > div { display: none; }
        </style>
        """, unsafe_allow_html=True)

# [Chat UX] 타이핑 효과(유사 스트리밍) 출력
def typewriter_markdown(text: str, chunk_size: int = 6, delay: float = 0.01):
    """
    메시지를 chunk 단위로 끊어가며 출력해 '스트리밍처럼 보이게' 하는 함수.
    - ensure_chat_bottom_anchor / scroll_to_bottom_smooth 로 자동 스크롤 동작
    """
    placeholder = st.empty()
    acc = ""

    for i in range(0, len(text), chunk_size):
        acc += text[i:i + chunk_size]
        placeholder.markdown(acc)

        # 채팅 하단 앵커 생성 + 스무스 스크롤
        ensure_chat_bottom_anchor()
        scroll_to_bottom_smooth()

        time.sleep(delay)
    return acc

# [Chat UX] 채팅창 하단 고정 앵커
def ensure_chat_bottom_anchor():
    """스크롤 이동 목표가 되는 하단 앵커(div) 삽입"""
    st.markdown('<div id="chat-bottom"></div>', unsafe_allow_html=True)


# [Chat UX] 하단으로 부드럽게 스크롤
def scroll_to_bottom_smooth():
    """
    components.html 로 부모 DOM에 접근해
    chat-bottom 요소가 있으면 scrollIntoView 실행
    """
    components.html(
        """
        <script>
        const el = window.parent.document.getElementById("chat-bottom");
        if (el) { el.scrollIntoView({ behavior: "smooth", block: "end" }); }
        </script>
        """,
        height=0,
    )


# [State] 메시지 push 헬퍼
def push_msg(role, content, visualize=False):
    """
    세션 상태(messages)에 메시지 객체를 추가.
    - role: "user"/"assistant"
    - visualize: 시각화 메시지인지 여부(현재는 주로 확장용)
    """
    st.session_state.messages.append({
        "role": role,
        "content": content,
        "visualize": visualize
    })

# [Viz] 공격 유형 분포 그래프 생성 -> base64 이미지 반환
def visualize_attack_counts(_df, exclude_benign: bool = True, use_log_scale: bool = False):
    """
    df['attack_type'] value_counts로 공격 유형별 탐지 건수 막대그래프 생성.
    - exclude_benign=True면 Benign 제외
    - use_log_scale=True면 y축 log scale
    - 반환값에 base64 PNG 포함 (Streamlit st.image로 렌더링)
    """
    df = _df
    target_col = "attack_type"
    counts = df[target_col].value_counts()

    # 정상(Benign) 제외 옵션
    if exclude_benign:
        counts = counts.drop(labels=["Benign"], errors="ignore")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(counts.index.astype(str), counts.values)
    ax.set_title('Detected Threats Distribution (Excluding Benign)', fontsize=14, fontweight='bold')
    ax.set_xlabel('Attack Type', fontsize=12)
    ax.set_ylabel('Count', fontsize=12)
    ax.tick_params(axis="x", rotation=45)

    # 로그 스케일 옵션
    if use_log_scale:
        ax.set_yscale("log")

    # 막대 위에 숫자 표시
    for i, v in enumerate(counts.values):
        ax.text(i, v, f"{int(v)}", ha="center", va="bottom", fontsize=9)

    fig.tight_layout()

    # 이미지를 메모리 버퍼로 저장 후 base64 인코딩
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)

    return {
        "target_col": target_col,
        "counts": counts.to_dict(),
        "image_base64": base64.b64encode(buf.getvalue()).decode("utf-8"),
    }


# [UI] 채팅 메시지 렌더링
def display_chat_messages():
    """
    session_state.messages에 쌓인 채팅을 순서대로 화면에 그리는 함수.
    - 초기 메시지(안내) 출력
    - 리포트 다운로드 버튼(is_report)
    - plot 메시지(type == "plot")는 base64 이미지를 디코딩해 st.image로 표시
    """
    if not st.session_state.messages:
        typewriter_markdown("안녕하세요.   분석할 로그 파일을 업로드 해주세요")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):

            # CSV 다운로드 버튼을 띄우는 메시지
            if msg.get("is_report") and st.session_state.df is not None:
                csv_data = convert_df_to_csv(st.session_state.df)
                st.download_button(
                    label="📥 분석 결과 리포트 다운로드 (CSV)",
                    data=csv_data,
                    file_name=f"analysis_result_{st.session_state.last_processed_file}",
                    mime="text/csv",
                    key=f"download_btn_{st.session_state.last_processed_file}"
                )

            # plot 메시지 렌더링
            if msg.get("type") == "plot" and msg.get("plot_base64"):
                if msg.get("content"):
                    st.markdown(msg["content"])
                img_bytes = base64.b64decode(msg["plot_base64"])
                st.image(BytesIO(img_bytes), width="stretch")

            # 일반 텍스트 메시지 렌더링
            else:
                st.markdown(msg["content"])


# [UI] 사이드바 구성
def set_sidebar():
    """
    앱 오른쪽(또는 왼쪽) 사이드바에 시스템 정보를 표시.
    - 모델/데이터셋/지표
    - 가이드 DB 정보
    """
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


# [UI] 상단 헤더 구성
def set_header():
    """메인 타이틀 + 안내 문구 표시"""
    st.markdown('<div class="main-header">🛡️ 네트워크 로그 이상 징후 탐지 시스템</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">※ PCAP/패킷 로그를 CICFlowMeter로 변환한 flow-level feature CSV 파일만 지원합니다 ※</div>', unsafe_allow_html=True)


# [UI] 푸터 구성 (팀/크레딧)
def set_putter():
    """하단 크레딧 표시 (divider 포함)"""
    st.divider()
    st.markdown("""
        <div style="text-align: center; color: #6b7280; font-size: 0.875rem; padding: 1rem 0;">
            <strong>HighFive</strong> | 5조 정예진 심재학 주재현 김지윤 김도현 김수경 이기찬 조민현
        </div>
        """, unsafe_allow_html=True)


# [UI] 채팅 입력 + 파일 업로드(핵심 UX)
def set_chat_upload():
    """
    화면 메인 영역에
    1) 채팅 메시지 출력
    2) 하단에 채팅 입력창 + 파일 업로더 배치
    3) 파일 업로드 시 DF 로드 -> 모델 예측 -> 시각화 -> 안내 메시지까지 한번에 수행
    """
    chat_container = st.container()
    with chat_container:
        display_chat_messages()

    input_area = st.container()
    with input_area:
        # 채팅 입력 영역(넓게) + 업로더(좁게) 두 컬럼 구성
        col_input, col_upload = st.columns([9.5, 0.5])

        # 채팅 입력 처리
        with col_input:
            if prompt := st.chat_input("메시지를 입력하세요..."):
                handle_input(prompt)
                st.rerun()

        # 파일 업로드 처리
        with col_upload:
            uploaded_file = st.file_uploader("로그 파일 첨부하기", type=["csv", "pcap"], label_visibility="collapsed")
            if uploaded_file:

                # last_processed_file 없으면 초기화
                if "last_processed_file" not in st.session_state:
                    st.session_state.last_processed_file = None

                # 같은 파일명을 반복 업로드했을 때 중복 처리 방지
                if st.session_state.last_processed_file != uploaded_file.name:

                    # CSV 로드
                    st.session_state.df = pd.read_csv(uploaded_file)
                    st.toast(f"✅ {uploaded_file.name} 로드 완료!", icon="📄")

                    # 모델 예측 컬럼 추가
                    predicted_df = infer.add_pred_column(st.session_state.df)
                    st.session_state.df = predicted_df
                    st.session_state.csv_path = 'user_log_with_pred.csv'
                    st.toast("✅ 모델 예측 완료", icon="🤖")

                    # 공격유형별 건수 그래프 생성
                    result = visualize_attack_counts(st.session_state.df)

                    # 탐지된 공격 유형 목록
                    attacks = predicted_df['attack_type'].unique()

                    # 결과 요약 메시지 생성
                    content = f'{uploaded_file.name}` 분석 완료\n\n'
                    if len(attacks) <= 1 and attacks[0] == 'Benign':
                        content += "✅ 악성 로그가 탐지되지 않았습니다."
                    else:
                        content += '🧨 **탐지된 악성 공격 리스트:**\n\n'
                        for atk in attacks:
                            if atk != 'Benign':
                                count = len(predicted_df[predicted_df['attack_type'] == atk])
                                content += f'- {atk} ({count}건)\n'

                    # 채팅 메시지에 결과 요약 추가
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": content,
                    })

                    # 그래프(plot) 메시지 추가
                    st.session_state.messages.append({
                        "role": "assistant",
                        "type": "plot",
                        "content": "공격 유형별 탐지 건수 그래프",
                        "plot_base64": result["image_base64"],
                    })

                    # CSV 다운로드 안내 메시지 추가
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "\n상세 설명이 필요한 공격명을 입력하시거나, 다운로드 버튼을 눌러 전체 결과(CSV)를 다운로드하세요.",
                        "is_report": True
                    })

                    # 마지막 처리 파일명 갱신
                    st.session_state.last_processed_file = uploaded_file.name

                    # 화면 갱신
                    st.rerun()



# 사용자 입력 처리: Function Calling + (가이드/분석) 분기
def handle_input(user_text):
    """
    사용자가 채팅에 입력한 내용을 처리하는 핵심 함수.
    - 우선 user 메시지를 세션에 저장
    - OpenAI Function Calling으로 의도 분석
      - '내 파일/내 로그/이 데이터' 등: analyze_user_file 호출
      - 일반 대응/정의 질문: guide 함수 호출
    - tool 결과를 다시 LLM에 넣어 '해석' 답변 생성(분석형 답변)
    """
    push_msg("user", user_text)


    # 1차 호출: tool 선택(자동)
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
        tools=TOOLS,
        tool_choice="auto",
    )

    msg = response.choices[0].message

    # tool_call이 존재하면 해당 함수를 실행
    if msg.tool_calls:
        tool_call = msg.tool_calls[0]
        fn_name = tool_call.function.name
        fn_args = json.loads(tool_call.function.arguments)

        with st.spinner(f"분석 중: {fn_name}..."):

            # 업로드 파일 기반 분석인 경우: 통계 뽑고 -> 2차 LLM 호출로 해석 생성
            if fn_name == "analyze_user_file":
                raw_analysis = analyze_user_file_stats(fn_args["attack_type"])

                # 2차 호출: "통계 결과를 근거로 해석"하는 답변을 생성
                second_response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "당신은 제공된 통계 데이터를 기반으로 근거를 제시하는 보안 분석가입니다. "
                                "'현상 나열'이 아니라 '데이터 기반 해석'을 하세요."
                            )
                        },
                        *st.session_state.messages,
                        msg,
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": fn_name,
                            "content": (
                                "이것은 실제 파일에서 추출한 데이터입니다. "
                                "수치(평균, 최대값)를 언급하며 DDoS/DoS 등의 근거를 설명하세요: "
                                f"{raw_analysis['answer']}"
                            )
                        }
                    ]
                )
                final_answer = second_response.choices[0].message.content

            # 가이드/기타 함수인 경우: FUNCTION_MAP으로 실행 후 answer 사용
            else:
                result = FUNCTION_MAP[fn_name](fn_args)
                final_answer = result['answer']

        # 타이핑 효과로 출력 + 메시지 저장
        typewriter_markdown(final_answer, chunk_size=6, delay=0.01)
        st.session_state.messages.append({
            "role": "assistant",
            "content": final_answer,
        })

    # tool_call이 없으면 일반 응답 그대로 출력
    else:
        typewriter_markdown(msg.content, chunk_size=6, delay=0.01)
        st.session_state.messages.append({
            "role": "assistant",
            "content": msg.content,
        })

    # 입력 처리 후 리렌더
    st.rerun()



# 챗봇 실행(페이지 구성 순서)
def execute_chatbot():
    """
    실제 앱 실행 진입점.
    - 초기화 -> CSS -> 헤더 -> 채팅/업로드 -> 사이드바 -> 푸터 순으로 렌더링
    """
    init_settings()
    apply_custom_css()
    set_header()
    set_chat_upload()
    set_sidebar()
    set_putter()
