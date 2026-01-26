import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# test용 attack_type 칼럼 없앤 csv 만듦 
input_filename = "user_log_with_pred3.csv"
input_path = os.path.join(BASE_DIR, input_filename)

df = pd.read_csv(input_path)

df = df.drop(columns=["attack_type"], errors="ignore")

base, ext = os.path.splitext(input_filename)
output_path = os.path.join(BASE_DIR, f"{base}_no_attacktype{ext}")

df.to_csv(output_path, index=False)

print("저장 완료:", output_path)