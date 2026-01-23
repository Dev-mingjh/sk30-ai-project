import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import classification_report,accuracy_score,f1_score
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.svm import SVC

import joblib

# 1. 여러 parquet 파일을 한 번에 불러와서 합치기
train_files = [
    "DoS-Wednesday-no-metadata.parquet",
    "WebAttacks-Thursday-no-metadata.parquet",
    "Infiltration-Thursday-no-metadata.parquet",
    "Botnet-Friday-no-metadata.parquet",
    "Portscan-Friday-no-metadata.parquet",
    "Bruteforce-Tuesday-no-metadata.parquet",
    "DDoS-Friday-no-metadata.parquet",
]

df = pd.concat([pd.read_parquet(f) for f in train_files], ignore_index=True)

# 2. 무한대 값이 있으면 NaN으로 바꾸기 (Bytes/s 같은 컬럼에서 생김) 네트워크 플로우 피처에는 Flow Bytes/s, Flow Packets/s처럼 “나누기”로 만든 값
# 스케일러(StandardScaler), 결측치 처리(SimpleImputer), 일부 모델이 inf를 못 다뤄서 에러,평균/표준편차가 망가져서 모든 값이 이상하게 스케일링
# 어떤 플로우는 Flow Duration(시간)=0에 가까운데 Bytes는 존재 → Bytes/s = Bytes / 0 → inf
df = df.replace([np.inf, -np.inf], np.nan)

# 3. 정답(Label)과 입력(X) 분리
y = df["Label"]                  # 정답
X = df.drop(columns=["Label"])   # 입력

# 4. 어떤 컬럼이 범주형(인코딩)인지 / 수치형(스케일링)인지 구분
# - Protocol은 숫자처럼 보여도 "종류"라서 범주형 처리(원핫인코딩)하는 게 안전
cat_cols = []
if "Protocol" in X.columns:
    cat_cols = ["Protocol"]

# protocol 이외 나머지는 전부 수치형이라고 가정 
num_cols = [c for c in X.columns if c not in cat_cols]

# 5. 범주형: 결측값을 최빈값으로 채우고 → 원핫인코딩
cat_preprocess = Pipeline(steps=[
    ("imputer", SimpleImputer(strategy="most_frequent")), 
    ("onehot", OneHotEncoder(handle_unknown="ignore")),         # 학습 때 못 본 프로토콜 값이 운영 중에 새로 들어올 수 있어
])                                                              # 운영 중 ICMP(1)가 들어오면

# - 수치형: 결측값을 중앙값으로 채우고 → 표준화(평균0, 표준편차1)
num_preprocess = Pipeline(steps=[
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler()),
])

# 6. 범주형/수치형 전처리를 합치기
preprocess = ColumnTransformer(
    transformers=[
        ("cat", cat_preprocess, cat_cols),
        ("num", num_preprocess, num_cols),
    ],
    remainder="drop"
)

# 9. 학습/검증 분리 후 학습
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
