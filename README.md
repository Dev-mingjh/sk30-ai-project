## feat: pkl 모델 추론 로직을 UI와 연동 (0126)

### 변경 내용
- `model/infer.py`, `model/cicids2017_rf_model_v1.pkl`  
  → `.pkl` 모델을 UI에서 바로 추론하도록 연동

- `data/remove_attack_type.py`  
  → CSV에서 `attack_type` 컬럼을 제거해  
    **모델이 정상적으로 다시 예측하는지 확인하기 위한 테스트용 스크립트**

- `ui/ui.py`  
  → 현재 메인 실행 파일  
  → `app.py`는 이전 실험용 파일
  
```bash
streamlit run ui/ui.py
