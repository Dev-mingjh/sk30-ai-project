import os
import joblib
import pandas as pd

DROP_COLS = ["Label", "label_big", "is_anomaly"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "cicids2017_rf_model_v1.pkl")

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

def add_pred_column(input_csv_path, output_csv_path, pred_col="attack_type"):
    print("모델 로딩 중입니다.")
    model = load_model(MODEL_PATH)

    print("CSV 읽는 중:", input_csv_path)
    df = pd.read_csv(input_csv_path)

    if df.empty:
        raise ValueError("입력 CSV가 비어 있습니다.")

    print(f"{len(df)}개의 행을 예측 중입니다.")
    X = prepare_X(df)
    df[pred_col] = model.predict(X)

    df.to_csv(output_csv_path, index=False)
    print("파일 저장 중:", output_csv_path)
    return output_csv_path

if __name__ == "__main__":
    out = add_pred_column(
    input_csv_path="output.csv",
    output_csv_path="user_log_with_pred.csv",
    pred_col="attack_type",
    )
    print("DONE:", out)