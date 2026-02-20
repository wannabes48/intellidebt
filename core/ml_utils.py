import pandas as pd
import numpy as np
import os
import joblib
from django.conf import settings

class LoanMLSystem:
    def __init__(self):
        self.classifier = None
        self.kmeans = None
        self.cluster_scaler = None
        self.df_data = pd.DataFrame()
        self.features_list = [
            'Age', 'Monthly_Income', 'Loan_Amount', 'Loan_Tenure', 'Interest_Rate', 
            'Collateral_Value', 'Outstanding_Loan_Amount', 'Monthly_EMI', 
            'Num_Missed_Payments', 'Days_Past_Due'
        ]
        self.load_system()

    def load_system(self):
        # 1. Load the Analytics Data for charts
        csv_path = os.path.join(settings.BASE_DIR, 'synthetic_loans_1000.csv')
        if os.path.exists(csv_path):
            self.df_data = pd.read_csv(csv_path)

        # 2. Load the Pre-Trained Machine Learning Model
        model_path = os.path.join(settings.BASE_DIR, 'loan_ml_model.joblib')
        if os.path.exists(model_path):
            model_data = joblib.load(model_path)
            self.classifier = model_data['classifier']
            self.kmeans = model_data['kmeans']
            self.cluster_scaler = model_data['cluster_scaler']
            self.segment_map = model_data['segment_map']
            self.features_list = model_data['features_list']
            print("✅ ML Models loaded successfully from disk!")
        else:
            print(f"WARNING: Model file not found at {model_path}.")

    def predict_risk(self, features_dict):
        if not self.classifier:
            return 0.5, "System Not Ready"

        df_input = pd.DataFrame([features_dict])
        
        for col in self.features_list:
            if col not in df_input.columns:
                df_input[col] = 0 
                
        risk_score = self.classifier.predict_proba(df_input[self.features_list])[:, 1][0]
        
        if risk_score > 0.75:
            strategy = "Immediate legal notices & aggressive recovery attempts"
        elif 0.50 <= risk_score <= 0.75:
            strategy = "Settlement offers & repayment plans"
        else:
            strategy = "Automated reminders & monitoring"
            
        return risk_score, strategy

    def explain_prediction(self, features_dict):
        reasons = []
        if features_dict.get('Num_Missed_Payments', 0) > 1:
            reasons.append("History of missed payments.")
        if features_dict.get('Days_Past_Due', 0) > 30:
            reasons.append("Significant days past due.")
        if features_dict.get('Loan_Amount', 0) > (features_dict.get('Monthly_Income', 0) * 8):
            reasons.append("Loan amount is very high vs Income.")
        if not reasons and features_dict.get('Num_Missed_Payments', 0) == 0:
            reasons.append("Good repayment history.")
        return reasons

    def get_client_segments(self, client_data_list):
        if not client_data_list or not self.kmeans or not self.cluster_scaler:
            return ["Unknown"] * len(client_data_list)
        
        input_df = pd.DataFrame(client_data_list)
        for col in self.features_list:
            if col not in input_df.columns:
                input_df[col] = 0
                
        clustering_features = ['Monthly_Income', 'Loan_Amount']
        X_input = self.cluster_scaler.transform(input_df[clustering_features])
        labels = self.kmeans.predict(X_input)
        return [self.segment_map.get(l, "Unknown") for l in labels]

    def get_analytics_json(self):
        return self.df_data.to_json(orient='records')

    def recommend_channel(self, risk_score, days_past_due, outstanding_amount=None):
        if outstanding_amount is not None and outstanding_amount <= 0:
            return {
                'method': 'Loan Closed',
                'icon': 'bi-check-circle-fill',
                'color': 'success',
                'action': 'No further action required. Good job!'
            }

        if risk_score > 0.75:
            return {
                'method': 'Immediate Legal Action',
                'icon': 'bi-hammer',
                'color': 'danger', 
                'action': 'Immediate legal notices & aggressive recovery attempts'
            }
        elif 0.50 <= risk_score <= 0.75:
            return {
                'method': 'Settlement Offers',
                'icon': 'bi-hand-thumbs-up-fill',
                'color': 'warning', 
                'action': 'Settlement offers & repayment plans'
            }
        else:
            return {
                'method': 'Automated Reminders',
                'icon': 'bi-chat-dots-fill',
                'color': 'success', 
                'action': 'Automated reminders & monitoring'
            }

ml_system = LoanMLSystem()