import joblib
import os

model_path = 'loan_ml_model.joblib'
if os.path.exists(model_path):
    model = joblib.load(model_path)
    print(f"Threshold: {model.get('custom_threshold', 'MISSING')}")
    print(f"Keys: {list(model.keys())}")
else:
    print("Model file not found.")
