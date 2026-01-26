# model/infer.py
import os
import joblib
import pandas as pd

DROP_COLS = ["Label", "label_big", "is_anomaly"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "cicids2017_rf_model_v1.pkl")

_model = None

def _load_model():
    global _model
    if _model is None:
        _model = joblib.load(MODEL_PATH)
    return _model

def predict_attack_type(df, col="attack_type"):
    model = _load_model()
    X = df.drop(columns=DROP_COLS, errors="ignore")

    if "Protocol" in X.columns:
        X["Protocol"] = (
            pd.to_numeric(X["Protocol"], errors="coerce")
            .astype("Int64")
            .astype(str)
        )

    df[col] = model.predict(X)
    return df