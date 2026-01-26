import os
import joblib
import pandas as pd

# ============================================================
# 기본 경로 설정
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))      # scripts/
PROJECT_ROOT = os.path.dirname(BASE_DIR)                   # sk30-ai-project/

MODEL_PATH = os.path.join(
    PROJECT_ROOT, "model", "cicids2017_rf_model_v1.pkl"
)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# ============================================================
# 설정
# ============================================================
DROP_COLS = ["Label", "label_big", "is_anomaly"]

# ============================================================
# 함수 정의
# ============================================================
def load_model(model_path):
    return joblib.load(model_path)

def prepare_X(df):
    X = df.drop(columns=DROP_COLS, errors="ignore")
    if "Protocol" in X.columns:
        X["Protocol"] = (
            pd.to_numeric(X["Protocol"], errors="coerce")
            .astype("Int64")
            .astype(str)
        )
    return X

def add_pred_column(
    input_csv_path,
    output_csv_path,
    pred_col="attack_type"
):
    print("모델 로딩 중...")
    model = load_model(MODEL_PATH)

    print("CSV 읽는 중:", input_csv_path)
    df = pd.read_csv(input_csv_path)

    if df.empty:
        raise ValueError("입력 CSV가 비어 있습니다.")

    print(f"{len(df)}개의 행을 예측 중...")
    X = prepare_X(df)
    df[pred_col] = model.predict(X)

    df.to_csv(output_csv_path, index=False)
    print("파일 저장 완료:", output_csv_path)

    return output_csv_path

# ============================================================
# 실행부
# ============================================================
if __name__ == "__main__":
    input_csv = os.path.join(DATA_DIR, "output2.csv")
    output_csv = os.path.join(DATA_DIR, "user_log_with_pred3.csv")

    out = add_pred_column(
        input_csv_path=input_csv,
        output_csv_path=output_csv,
        pred_col="attack_type",
    )

    print("DONE:", out)