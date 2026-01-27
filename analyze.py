import streamlit as st
import pandas as pd
import json

def analyze_user_file_stats(attack_type: str):
    df = st.session_state.get("df")
    if df is None:
        return {"answer": "파일 로드 실패"}

    # 공격 데이터와 정상 데이터 분리
    target_df = df[df['attack_type'].str.lower() == attack_type.lower()]
    benign_df = df[df['attack_type'].str.lower() == 'benign']
    
    if target_df.empty:
        return {"answer": "해당 공격 데이터 없음"}

    # 주요 특징 추출
    cols = ['Flow Duration', 'Total Fwd Packets', 'Flow Bytes/s', 'Flow Packets/s', 'Avg Packet Size']
    
    stats = {}
    for col in cols:
        if col in df.columns:
            stats[col] = {
                "attack_mean": float(round(target_df[col].mean(), 2)),
                "benign_mean": float(round(benign_df[col].mean(), 2)) if not benign_df.empty else "N/A",
                "attack_max": float(round(target_df[col].max(), 2))
            }

    analysis_context = {
        "target_attack": attack_type,
        "found_count": int(len(target_df)),
        "row_locations": [int(x) for x in target_df.index[:10]],
        "metrics_comparison": stats
    }

    return {"answer": json.dumps(analysis_context, ensure_ascii=False)}

ANALYZE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "analyze_user_file",
            "description": "사용자가 업로드한 파일/로그/데이터에 대한 구체적인 분석이나 통계를 원할 때 사용",
            "parameters": {
                "type": "object",
                "properties": {
                    "attack_type": {"type": "string", "description": "분석할 공격 유형"}
                },
                "required": ["attack_type"]
            }
        }
    }
]