import os
import joblib
import pandas as pd

# -----------------------------------
# 1. 기본 설정
# -----------------------------------
                                                                                        # 예측 시 제거할 라벨 관련 컬럼
DROP_COLS = ["Label", "label_big", "is_anomaly"]

                                                                                        # 현재 파일 기준 경로
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

                                                                                        # 학습된 RandomForest 모델 경로
MODEL_PATH = os.path.join(BASE_DIR, "cicids2017_rf_model_v2.pkl")


# -----------------------------------
# 2. 모델 로딩
# -----------------------------------

def load_model(model_path):
    """저장된 학습 모델 로드"""
    return joblib.load(model_path)


# -----------------------------------
# 3. 모델이 요구하는 컬럼 추출
# -----------------------------------

def get_required_columns(model):
    """
    Pipeline + ColumnTransformer 기반 모델에서
    학습 시 사용된 feature 컬럼 목록 추출
    """
                                                                                        # Pipeline 내부 step 중 feature_names_in_ 속성을 가진 객체 탐색
    for step in model.named_steps.values():
        if hasattr(step, "feature_names_in_"):
            return list(step.feature_names_in_)

                                                                                        # 컬럼 정보를 찾지 못한 경우 예외 처리
    raise RuntimeError("모델에서 feature_names_in_ 를 찾을 수 없습니다.")


# -----------------------------------
# 4. 입력 데이터 전처리
# -----------------------------------

def prepare_X(df, required_cols):
    """
    입력 데이터프레임을
    모델 학습 시 사용된 컬럼 구조와 동일하게 맞추는 함수
    """
                                                                                        # 라벨 관련 컬럼 제거 (존재하지 않으면 무시)
    X = df.drop(columns=DROP_COLS, errors="ignore")
                                                                                        # 모델이 요구하는 컬럼 중 입력 데이터에 없는 컬럼은 0으로 생성
    for col in required_cols:
        if col not in X.columns:
            X[col] = 0
                                                                                        # 모델이 학습하지 않은 불필요한 컬럼 제거
    X = X[required_cols]
                                                                                        # Protocol 컬럼 타입 보정
                                                                                        # (문자 → 숫자 변환, 변환 불가 값은 0 처리)
    if "Protocol" in X.columns:
        X["Protocol"] = (
            pd.to_numeric(X["Protocol"], errors="coerce")
            .fillna(0)
            .astype(int)
        )

    return X


# -----------------------------------
# 5. 예측 결과 및 확률 컬럼 추가
# -----------------------------------

def add_pred_column(input_csv_path, output_csv_path, pred_col="attack_type"):
    """
    입력 CSV에 대해 공격 유형 예측 수행 후
    예측 결과 및 클래스별 확률 컬럼을 추가하여 저장
    """
    print("모델 로딩 중입니다.")
    model = load_model(MODEL_PATH)

    print("모델이 요구하는 컬럼 추출 중...")
    required_cols = get_required_columns(model)
    print(f"필요 컬럼 수: {len(required_cols)}")

    print("CSV 읽는 중:", input_csv_path)
    df = pd.read_csv(input_csv_path)

                                                                                            # 빈 파일 방어 코드
    if df.empty:
        raise ValueError("입력 CSV가 비어 있습니다.")

    print(f"{len(df)}개의 행을 예측 중입니다.")

                                                                                            # 입력 데이터 전처리
    X = prepare_X(df, required_cols)

                                                                                            # 공격 유형 예측
    df[pred_col] = model.predict(X)

                                                                                            # 클래스별 확률 계산 (지원되는 모델일 경우)
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X)
        classes = model.classes_

        for i, cls in enumerate(classes):
                                                                                            # 확률을 % 단위로 변환 후 소수점 1자리까지 표현
            df[f"prob_{cls}"] = (proba[:, i] * 100).round(1)

                                                                                            # 결과 CSV 저장
    df.to_csv(output_csv_path, index=False)
    print("파일 저장 완료:", output_csv_path)

    return output_csv_path


# =========================
# 6. 실행 진입점
# =========================

if __name__ == "__main__":
    out = add_pred_column(
        input_csv_path="output.csv",
        output_csv_path="user_log_with_pred.csv",
        pred_col="attack_type",
    )
    print("DONE:", out)