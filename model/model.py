import os
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier


# 본인 컴퓨터의 파일 경로로 수정
DATA_DIR = r"C:\Users\ez\Downloads\CICIDS2017_parquet"
OUT_DIR  = r"C:\Users\ez\Downloads\CICIDS2017_models"
os.makedirs(OUT_DIR, exist_ok=True)

train_files = [
    "DoS-Wednesday-no-metadata.parquet",
    "WebAttacks-Thursday-no-metadata.parquet",
    "Infiltration-Thursday-no-metadata.parquet",
    "Botnet-Friday-no-metadata.parquet",
    "Portscan-Friday-no-metadata.parquet",
    "Bruteforce-Tuesday-no-metadata.parquet",
    "DDoS-Friday-no-metadata.parquet",
]
paths = [os.path.join(DATA_DIR, f) for f in train_files]

# 로드 + 병합
df = pd.concat([pd.read_parquet(p) for p in paths], ignore_index=True)

# inf/-inf -> NaN 전처리 진행
df = df.replace([np.inf, -np.inf], np.nan)

df["Label"] = (df["Label"].astype(str)
               .str.replace("�", "-", regex=False)
               .str.replace(r"\s+", " ", regex=True)
               .str.strip())

# 라벨 매핑
def map_label_big(x):
    s = str(x).strip().lower()

    # 정상
    if s == "benign":
        return "Benign"
    # ddos
    if "ddos" in s:
        return "DDoS"
    # dos
    if s.startswith("dos"):
        return "DoS"
    # heartbleed(Dos 파일에 들어있는 분류임)
    if "heartbleed" in s:
        return "DoS"
    # portscan
    if "portscan" in s or "port scan" in s:
        return "PortScan"
    # botnet
    if "bot" in s:
        return "Botnet"
    # infiltration
    if "infiltration" in s:
        return "Infiltration"
    # web attack
    if "web attack" in s or ("web" in s and "attack" in s):
        return "WebAttack"
    # Bruteforce
    if "brute" in s or "patator" in s:
        return "BruteForce"
    return "OtherAttack"


df["label_big"] = df["Label"].apply(map_label_big)

print("\n[label_big 분포(전체)]")
print(df["label_big"].value_counts())

# 불균형 제거(1:1 비율)
df["is_anomaly"] = (df["label_big"] != "Benign").astype(int)
attack_df = df[df["is_anomaly"] == 1].copy()
benign_df = df[df["is_anomaly"] == 0].copy()

# Benign을 공격 개수만큼만 샘플링해서 1:1 맞춤
benign_sample = benign_df.sample(n=len(attack_df), random_state=42)
df_balanced = pd.concat([attack_df, benign_sample], ignore_index=True)
# 모델 섞음
df_balanced = df_balanced.sample(frac=1, random_state=42).reset_index(drop=True)

print("\n[밸런싱 후 is_anomaly 분포]")
print(df_balanced["is_anomaly"].value_counts())

print("\n[밸런싱 후 label_big 분포]")
print(df_balanced["label_big"].value_counts())

# X, y 
y = df_balanced["label_big"]
X = df_balanced.drop(columns=["Label", "label_big", "is_anomaly"], errors="ignore")

# 범주형/수치형 컬럼 자동 탐지
cat_cols = []
num_cols = []

for c in X.columns:
    if X[c].dtype.name in ["object", "category"]:
        cat_cols.append(c)
    else:
        num_cols.append(c)

# Protocal 원핫인코딩 처리를 위해 범주형 변환
if "Protocol" in num_cols:
    num_cols.remove("Protocol")
    cat_cols.append("Protocol")
    X["Protocol"] = X["Protocol"].astype("Int64").astype(str) 

print("\n범주형 컬럼:", cat_cols)
print("수치형 컬럼 수:", len(num_cols))

# 전처리 파이프라인
# - 범주형: 결측값을 최빈값으로 채우고 → 원핫인코딩
cat_preprocess = Pipeline(steps=[
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("onehot", OneHotEncoder(handle_unknown="ignore")),
])

# - 수치형: 결측값을 중앙값으로 채우고 → 표준화(평균0, 표준편차1)
num_preprocess = Pipeline(steps=[
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler()),
])
# 범주형/수치형 전처리를 합치기
preprocess = ColumnTransformer(
    transformers=[
        ("cat", cat_preprocess, cat_cols),
        ("num", num_preprocess, num_cols),
    ],
    remainder="drop",
)

# ---- 여기서부터 모델 학습 진행하면 되는데, Pipeline 때문에 미리 좀 만들었고 이후에 fit까지 진행해주시면 됩니다.---
# Train/Test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# 모델 + 파이프라인 (전처리 + 분류기)
clf = Pipeline(steps=[
    ("preprocess", preprocess),
    ("model", RandomForestClassifier(
        n_estimators=300,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced_subsample"
    ))
])