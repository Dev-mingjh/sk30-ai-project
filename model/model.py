import os
import joblib
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd

from sklearn.metrics import classification_report
from sklearn.model_selection import learning_curve, train_test_split, validation_curve
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier

<<<<<<< HEAD

# 본인 컴퓨터의 파일 경로로 수정
# DATA_DIR = r"C:\Users\ez\Downloads\CICIDS2017_parquet"
# OUT_DIR  = r"C:\Users\ez\Downloads\CICIDS2017_models"
=======
>>>>>>> origin/ai-jiyun
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

# Train/Test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# 모델 + 파이프라인 (전처리 + 분류기)
clf = Pipeline(steps=[
    ("preprocess", preprocess),
    ("model", RandomForestClassifier(
<<<<<<< HEAD
        n_estimators=300, # 생성할 결정 나무의 개수 (많을 수록 좋지만 학습 속도가 느려짐) (default : 100)
        max_depth=20,     # 나무의 최대 깊이 (너무 깊으면 과적합) (deafult : None)
        random_state=42,
        min_samples_split=2, # 노드를 분할하기 위해 필요한 최소 샘플 수 (클 수록 분할 제한 -> 모델 단순화) (default : 2)
        min_samples_leaf=1, #말단 노드가 되기 위해 필요한 최소 샘플 수 (과적합 방지) (default : 1)
        max_features="sqrt", #최적의 분할을 찾기 위해 고려할 피처의 개수 (default : 'sqrt')
        min_impurity_decrease=0.0, #분할로 인해 감소해야 하는 불순도의 최소치로 이 값보다 이득이 적으면 분할 안 함 (default : 0.0)
        ccp_alpha=0.0, #비용-복잡도 가지치기 파라미터 (0보다 크면 나무의 크기 감소) (default : 0.0)
        n_jobs=-1,    #병렬 처리 (-1은 가용 CPU 모두 사용) (default : None)
        class_weight="balanced_subsample" # 클래스 가중치 주입 (default : None)
    ))
])

# [분석 모드] / [학습 모드] 스위치
ANALYZE_MODE = True
#################################### 하이퍼 파라미터 분석 ###################################
# --- [함수 1] 학습 곡선 (현재 파라미터 기준, 데이터 양에 따른 성능 변화) ---
def plot_learning_curve(estimator, X, y, title="Learning Curve"):
    print("학습 곡선 계산 중...")
    # train_score => 학습 데이터 자체를 다시 물어본 F1-Score
    # test_score => 교차 검증 데이터의 F1-Score
=======
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

# 분석 모드 / 학습 모드
ANALYZE_MODE = True
# 학습 곡선 (현재 파라미터 기준, 데이터 양에 따른 성능 변화)
def plot_learning_curve(estimator, X, y, title="Learning Curve"):
    print("학습 곡선 계산 중...")

>>>>>>> origin/ai-jiyun
    train_sizes, train_scores, test_scores = learning_curve(
        estimator, X, y, cv=3, n_jobs=-1, 
        train_sizes=np.linspace(0.1, 1.0, 5),
        scoring='f1_macro'
<<<<<<< HEAD
    ) #cv=3 -> 전체 데이터를 3등분 한 뒤, (3-1) 세트 학습 | 1세트 검증 

=======
    ) 
>>>>>>> origin/ai-jiyun
    train_mean = np.mean(train_scores, axis=1)
    train_std = np.std(train_scores, axis=1)
    test_mean = np.mean(test_scores, axis=1)
    test_std = np.std(test_scores, axis=1)

    plt.figure(figsize=(10, 6))
    plt.plot(train_sizes, train_mean, 'o-', color="r", label="Training score")
    plt.fill_between(train_sizes, train_mean - train_std, train_mean + train_std, alpha=0.1, color="r")
    plt.plot(train_sizes, test_mean, 'o-', color="g", label="Cross-validation score")
    plt.fill_between(train_sizes, test_mean - test_std, test_mean + test_std, alpha=0.1, color="g")
<<<<<<< HEAD

=======
>>>>>>> origin/ai-jiyun
    plt.title(title)
    plt.xlabel("Training Examples")
    plt.ylabel("F1-Score (Macro)")
    plt.legend(loc="best")
    plt.grid()
    plt.show()

<<<<<<< HEAD
# --- [함수 2] 검증 곡선 (파라미터 값(max_depth)에 따른 성능 변화) ---
def plot_validation_curve(estimator, X, y, param_name, param_range, title="Validation Curve"):
    print("검증 곡선 계산 중...")
    # train_score => 학습 데이터 자체를 다시 물어본 F1-Score
    # test_score => 교차 검증 데이터의 F1-Score
=======
# 검증 곡선 (파라미터 값(max_depth)에 따른 성능 변화) 
def plot_validation_curve(estimator, X, y, param_name, param_range, title="Validation Curve"):
    print("검증 곡선 계산 중...")

>>>>>>> origin/ai-jiyun
    train_scores, test_scores = validation_curve(
        estimator, X, y, 
        param_name=param_name, 
        param_range=param_range,
        cv=3, scoring="f1_macro", n_jobs=-1
<<<<<<< HEAD
    ) #cv=3 -> 전체 데이터를 3등분 한 뒤, (3-1) 세트 학습 | 1세트 검증 
=======
    ) 
>>>>>>> origin/ai-jiyun

    train_mean = np.mean(train_scores, axis=1)
    train_std = np.std(train_scores, axis=1)
    test_mean = np.mean(test_scores, axis=1)
    test_std = np.std(test_scores, axis=1)

    plt.figure(figsize=(10, 6))
    plt.plot(param_range, train_mean, 'o-', color="r", label="Training score")
    plt.fill_between(param_range, train_mean - train_std, train_mean + train_std, alpha=0.1, color="r")
    plt.plot(param_range, test_mean, 'o-', color="g", label="Cross-validation score")
    plt.fill_between(param_range, test_mean - test_std, test_mean + test_std, alpha=0.1, color="g")
<<<<<<< HEAD

=======
>>>>>>> origin/ai-jiyun
    plt.title(f"{title} ({param_name})")
    plt.xlabel(param_name)
    plt.ylabel("F1-Score (Macro)")
    plt.legend(loc="best")
    plt.grid()
    plt.show()

if ANALYZE_MODE:  
<<<<<<< HEAD
    # 빠른 확인을 위한 샘플링 (경향성 확인에는 충분)
=======
    # 빠른 확인을 위한 샘플링
>>>>>>> origin/ai-jiyun
    X_sample = X_train.sample(n=30000, random_state=42)
    y_sample = y_train.loc[X_sample.index]

    # 학습 곡선 시각화
    plot_learning_curve(clf, X_sample, y_sample, "RF Learning Curve")

    # 검증 곡선 시각화 (max_depth 최적값 찾기)
<<<<<<< HEAD
    depth_range = [17, 18, 19, 20, 21]
    plot_validation_curve(clf, X_sample, y_sample, "model__max_depth", depth_range)
#################################### 모델 학습 및 저장 ###################################
if not ANALYZE_MODE:
    # 모델 학습
    print("모델 학습 중...")
    clf.fit(X_train, y_train)

    # 예측값 생성 및 Classification Report 출력 (Precision, Recall, F1-Score)
    # 위 학습/검증 곡선의 교차 검증 F1-Score보다 높아야 함 (이유 : 더 많은 데이터로 학습된 모델 사용)
=======
    depth_range = [10, 12, 14, 15, 16, 18]
    plot_validation_curve(clf, X_sample, y_sample, "model__max_depth", depth_range)

# 모델 학습 및 저장 
if not ANALYZE_MODE:
    print("모델 학습 중...")
    clf.fit(X_train, y_train)

    # 예측값 생성 및 Classification Report 출력 
>>>>>>> origin/ai-jiyun
    y_pred = clf.predict(X_test)
    print("### Classification Report ###")
    print(classification_report(y_test, y_pred))

    # 저장할 파일명 설정 (OUT_DIR)
    model_filename = "cicids2017_rf_model_v1.pkl"
    save_path = os.path.join(OUT_DIR, model_filename)

    # 모델 저장 실행
    print(f"모델을 저장 중입니다: {save_path}")
    joblib.dump(clf, save_path)
    print("모델 저장 완료!")

<<<<<<< HEAD
    # 저장된 파일 크기 확인 (코랩 환경에서 용량 체크)
=======
    # 저장된 파일 크기 확인
>>>>>>> origin/ai-jiyun
    file_size = os.path.getsize(save_path) / (1024 * 1024)
    print(f"모델 파일 크기: {file_size:.2f} MB")