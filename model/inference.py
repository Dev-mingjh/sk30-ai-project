import os
import joblib
import pandas as pd

DROP_COLS = ["Label", "label_big", "is_anomaly"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "cicids2017_rf_model_v2.pkl")


def load_model(model_path):
    return joblib.load(model_path)


def get_required_columns(model):
    """
    Pipeline + ColumnTransformer 모델에서
    학습 시 사용된 컬럼 목록 추출
    """
    # 보통 preprocess라는 이름을 씀 (다를 수도 있음)
    for step in model.named_steps.values():
        if hasattr(step, "feature_names_in_"):
            return list(step.feature_names_in_)
    raise RuntimeError("모델에서 feature_names_in_ 를 찾을 수 없습니다.")


def prepare_X(df, required_cols):
    # 이 로직이 모델이 원하는 컬럼이면 그대로 진행한다.
    X = df.drop(columns=DROP_COLS, errors="ignore")
    
    # 그렇지 않으면 모델이 원하는 컬럼으로 만들기.
    # 없는 컬럼은 0으로 생성
    for col in required_cols:
        if col not in X.columns:
            X[col] = 0

    # 불필요한 컬럼 제거 (모델이 모르는 컬럼)
    X = X[required_cols]

    # Protocol 타입 처리 (모델 학습 방식에 맞춤)
    if "Protocol" in X.columns:
        X["Protocol"] = (
            pd.to_numeric(X["Protocol"], errors="coerce")
            .fillna(0)
            .astype(int)
        )

    return X


def add_pred_column(input_csv_path, output_csv_path, pred_col="attack_type"):
    print("모델 로딩 중입니다.")
    model = load_model(MODEL_PATH)

    print("모델이 요구하는 컬럼 추출 중...")
    required_cols = get_required_columns(model)
    print(f"필요 컬럼 수: {len(required_cols)}")

    print("CSV 읽는 중:", input_csv_path)
    df = pd.read_csv(input_csv_path)

    if df.empty:
        raise ValueError("입력 CSV가 비어 있습니다.")

    print(f"{len(df)}개의 행을 예측 중입니다.")

    X = prepare_X(df, required_cols)

    # 예측
    df[pred_col] = model.predict(X)

    # 확률
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X)
        classes = model.classes_
        for i, cls in enumerate(classes):
            df[f"prob_{cls}"] = (proba[:, i] * 100).round(1)

    df.to_csv(output_csv_path, index=False)
    print("파일 저장 완료:", output_csv_path)

    return output_csv_path


if __name__ == "__main__":
    out = add_pred_column(
        input_csv_path="output.csv",
        output_csv_path="user_log_with_pred.csv",
        pred_col="attack_type",
    )
    print("DONE:", out)