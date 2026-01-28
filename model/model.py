import os
import joblib
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
import re

from sklearn.metrics import classification_report
from sklearn.model_selection import learning_curve, train_test_split, validation_curve
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier

#------------------------------------------------------------------------
# 1. 데이터 로드 와 데이터 병합 및 극값 전처리
#------------------------------------------------------------------------
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT_DIR, exist_ok=True)

train_files = [
    "DoS-Wednesday-no-metadata.parquet",
    "WebAttacks-Thursday-no-metadata.parquet",
    "Botnet-Friday-no-metadata.parquet",
    "Portscan-Friday-no-metadata.parquet",
    "Bruteforce-Tuesday-no-metadata.parquet",
    "DDoS-Friday-no-metadata.parquet",
    "Infiltration-Thursday-no-metadata.parquet",
]
paths = [os.path.join(DATA_DIR, f) for f in train_files]

df = pd.concat([pd.read_parquet(p) for p in paths], ignore_index=True)

# inf/-inf -> NaN
df = df.replace([np.inf, -np.inf], np.nan)

# ------------------------------------------------------------------------
# 2. 공격 유형 8가지 대분류 라벨 매핑
# ------------------------------------------------------------------------
df["Label"] = (
    df["Label"].astype(str)
    .str.replace("�", "-", regex=False)
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)

def map_label_big(x):
    s = str(x).strip().lower()
    s = re.sub(r"\s+", " ", s)

    # 정상
    if s == "benign":
        return "Benign"

    # DDoS
    if re.search(r"\bddos\b", s) or "ddos" in s:
        return "DDoS"

    # DoS / Heartbleed
    if s.startswith("dos") or "heartbleed" in s:
        return "DoS"

    # PortScan
    if re.search(r"\bportscan\b|\bport scan\b", s):
        return "PortScan"

    # WebAttack
    if "web attack" in s or s.startswith("webattack") or ("web" in s and "attack" in s):
        return "WebAttack"

    # BruteForce
    if "brute" in s or "patator" in s:
        return "BruteForce"

    # Infiltration
    if "infiltration" in s:
        return "Infiltration"

    # Botnet (bot 문자열 전체를 쓰지 말고 botnet만)
    if re.search(r"\bbotnet\b", s) or "botnet" in s:
        return "Botnet"

    return "OtherAttack"


df["label_big"] = df["Label"].apply(map_label_big)

print("\n[label_big 분포(전체)]")
print(df["label_big"].value_counts())


# ------------------------------------------------------------------------
# 3. Infiltration 데이터 증강 (7개 → 200개) : 약한 노이즈 증강
# ------------------------------------------------------------------------
def augment_infiltration(infil_df, target_size=200, noise_ratio=0.01, random_state=42):
    """
    - std를 반복 계산하지 않고 1회 계산(효율)
    - 가우시안 노이즈 추가 후 음수 방지(현실성)
    """
    rng = np.random.default_rng(random_state)

    if len(infil_df) == 0:
        return infil_df

    num_cols = infil_df.select_dtypes(include=[np.number]).columns.tolist()
    if not num_cols:
        return infil_df

    stds = infil_df[num_cols].std(numeric_only=True).replace(0, np.nan)

    need = max(0, target_size - len(infil_df))
    if need == 0:
        return infil_df

    augmented = []
    for _ in range(need):
        sample = infil_df.sample(
            1, replace=True,
            random_state=int(rng.integers(0, 1_000_000))
        )
        noisy = sample.copy()

        noise = rng.normal(
            loc=0.0,
            scale=(stds * noise_ratio).fillna(0.0).values
        )

        noisy.loc[:, num_cols] = noisy.loc[:, num_cols].values + noise
        noisy.loc[:, num_cols] = noisy.loc[:, num_cols].clip(lower=0)

        augmented.append(noisy)

    return pd.concat([infil_df] + augmented, ignore_index=True)


infil_df = df[df["label_big"] == "Infiltration"].copy()
print("\n원본 Infiltration 개수:", len(infil_df))

infil_aug = augment_infiltration(infil_df, target_size=200)
print("증강 후 Infiltration 개수:", len(infil_aug))

df = df[df["label_big"] != "Infiltration"]
df = pd.concat([df, infil_aug], ignore_index=True)

print("\n[label_big 분포(증강 후)]")
print(df["label_big"].value_counts())


# ------------------------------------------------------------------------
# 4. 공격/일반 데이터를 1:1 비율로 불균형 제거
# ------------------------------------------------------------------------
df["is_anomaly"] = (df["label_big"] != "Benign").astype(int)
attack_df = df[df["is_anomaly"] == 1].copy()
benign_df = df[df["is_anomaly"] == 0].copy()

benign_sample = benign_df.sample(n=len(attack_df), random_state=42)
df_balanced = pd.concat([attack_df, benign_sample], ignore_index=True)
df_balanced = df_balanced.sample(frac=1, random_state=42).reset_index(drop=True)

print("\n[밸런싱 후 is_anomaly 분포]")
print(df_balanced["is_anomaly"].value_counts())

print("\n[밸런싱 후 label_big 분포]")
print(df_balanced["label_big"].value_counts())


# ------------------------------------------------------------------------
# 5. 데이터 전처리 및 Train/Test split
# ------------------------------------------------------------------------
y = df_balanced["label_big"]
X = df_balanced.drop(columns=["Label", "label_big", "is_anomaly"], errors="ignore")

cat_cols = []
num_cols = []

for c in X.columns:
    if X[c].dtype.name in ["object", "category"]:
        cat_cols.append(c)
    else:
        num_cols.append(c)

# Protocol: 원핫인코딩 위해 범주형으로 이동
if "Protocol" in num_cols:
    num_cols.remove("Protocol")
    cat_cols.append("Protocol")
    X["Protocol"] = X["Protocol"].astype("Int64").astype(str)

print("\n범주형 컬럼:", cat_cols)
print("수치형 컬럼 수:", len(num_cols))

cat_preprocess = Pipeline(steps=[
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("onehot", OneHotEncoder(handle_unknown="ignore")),
])

num_preprocess = Pipeline(steps=[
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler()),
])

preprocess = ColumnTransformer(
    transformers=[
        ("cat", cat_preprocess, cat_cols),
        ("num", num_preprocess, num_cols),
    ],
    remainder="drop",
)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)


# ------------------------------------------------------------------------
# 6. 모델 학습 및 분석 모드
# ------------------------------------------------------------------------
clf = Pipeline(steps=[
    ("preprocess", preprocess),
    ("model", RandomForestClassifier(
        n_estimators=300,
        max_depth=15,
        random_state=42,
        min_samples_split=10,
        min_samples_leaf=4,
        max_features="sqrt",
        min_impurity_decrease=0.0,
        ccp_alpha=0.0,
        n_jobs=-1,
        class_weight=None
    ))
])

ANALYZE_MODE = False


def plot_learning_curve(estimator, X, y, title="Learning Curve"):
    print("학습 곡선 계산 중...")

    train_sizes, train_scores, test_scores = learning_curve(
        estimator, X, y, cv=3, n_jobs=-1,
        train_sizes=np.linspace(0.1, 1.0, 5),
        scoring="f1_macro"
    )

    train_mean = np.mean(train_scores, axis=1)
    train_std = np.std(train_scores, axis=1)
    test_mean = np.mean(test_scores, axis=1)
    test_std = np.std(test_scores, axis=1)

    plt.figure(figsize=(10, 6))
    plt.plot(train_sizes, train_mean, "o-", color="r", label="Training score")
    plt.fill_between(train_sizes, train_mean - train_std, train_mean + train_std, alpha=0.1, color="r")
    plt.plot(train_sizes, test_mean, "o-", color="g", label="Cross-validation score")
    plt.fill_between(train_sizes, test_mean - test_std, test_mean + test_std, alpha=0.1, color="g")
    plt.title(title)
    plt.xlabel("Training Examples")
    plt.ylabel("F1-Score (Macro)")
    plt.legend(loc="best")
    plt.grid()
    plt.show()


def plot_validation_curve(estimator, X, y, param_name, param_range, title="Validation Curve"):
    print("검증 곡선 계산 중...")

    train_scores, test_scores = validation_curve(
        estimator, X, y,
        param_name=param_name,
        param_range=param_range,
        cv=3, scoring="f1_macro", n_jobs=-1
    )

    train_mean = np.mean(train_scores, axis=1)
    train_std = np.std(train_scores, axis=1)
    test_mean = np.mean(test_scores, axis=1)
    test_std = np.std(test_scores, axis=1)

    plt.figure(figsize=(10, 6))
    plt.plot(param_range, train_mean, "o-", color="r", label="Training score")
    plt.fill_between(param_range, train_mean - train_std, train_mean + train_std, alpha=0.1, color="r")
    plt.plot(param_range, test_mean, "o-", color="g", label="Cross-validation score")
    plt.fill_between(param_range, test_mean - test_std, test_mean + test_std, alpha=0.1, color="g")
    plt.title(f"{title} ({param_name})")
    plt.xlabel(param_name)
    plt.ylabel("F1-Score (Macro)")
    plt.legend(loc="best")
    plt.grid()
    plt.show()


if ANALYZE_MODE:
    X_sample = X_train.sample(n=30000, random_state=42)
    y_sample = y_train.loc[X_sample.index]

    plot_learning_curve(clf, X_sample, y_sample, "RF Learning Curve")

    depth_range = [10, 12, 14, 15, 16, 18]
    plot_validation_curve(clf, X_sample, y_sample, "model__max_depth", depth_range)


# ------------------------------------------------------------------------
# 7. 모델 저장
# ------------------------------------------------------------------------
if not ANALYZE_MODE:
    print("모델 학습 중...")
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    print("### Classification Report ###")
    print(classification_report(y_test, y_pred))

    model_filename = "cicids2017_rf_model_v2.pkl"
    save_path = os.path.join(OUT_DIR, model_filename)

    print(f"모델을 저장 중입니다: {save_path}")
    joblib.dump(clf, save_path)
    print("모델 저장 완료!")

    file_size = os.path.getsize(save_path) / (1024 * 1024)
    print(f"모델 파일 크기: {file_size:.2f} MB")