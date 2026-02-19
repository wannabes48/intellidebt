import pandas as pd
import numpy as np
import os
from django.conf import settings
from sklearn.ensemble import RandomForestClassifier
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

class LoanMLSystem:
    def __init__(self):
        self.classifier = None
        self.kmeans = None
        self.scaler = StandardScaler()
        self.features_list = [
            'Age', 'Monthly_Income', 'Loan_Amount', 'Loan_Tenure', 'Interest_Rate', 
            'Collateral_Value', 'Outstanding_Loan_Amount', 'Monthly_EMI', 
            'Num_Missed_Payments', 'Days_Past_Due'
        ]
        self.df_data = pd.DataFrame()
        self.train_models()

    def train_models(self):
        # Safely locate the CSV file in the main project folder
        csv_path = os.path.join(settings.BASE_DIR, 'synthetic_loans_1000.csv')
        
        if os.path.exists(csv_path):
            # --- 1. Load Real Data ---
            self.df_data = pd.read_csv(csv_path)
            
            # Select features
            X = self.df_data[self.features_list]
            
            # --- 2. Scaling (Standardization) ---
            X_scaled = self.scaler.fit_transform(X)

            # --- 3. Clustering (Objective B) ---
            # RESTRICTION: Use only Monthly_Income and Loan_Amount for segmentation
            X_clustering = self.df_data[['Monthly_Income', 'Loan_Amount']]
            scaler_cluster = StandardScaler()
            X_cluster_scaled = scaler_cluster.fit_transform(X_clustering)
            
            self.kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
            self.df_data['Borrower_Segment'] = self.kmeans.fit_predict(X_cluster_scaled)
            
            # Save the cluster scaler for later use in prediction
            self.cluster_scaler = scaler_cluster
            
            # Map Clusters to Names (Heuristic based on article)
            self.segment_map = {
                0: 'Moderate Income, High Loan Burden',
                1: 'High Income, Low Default Risk',
                2: 'Moderate Income, Medium Risk',
                3: 'High Loan, Higher Default Risk'
            }
            self.df_data['Segment_Name'] = self.df_data['Borrower_Segment'].map(self.segment_map)

            # --- 4. Define Target for Classification (Objective A) ---
            high_risk_segments = ['High Loan, Higher Default Risk', 'Moderate Income, High Loan Burden']
            self.df_data['High_Risk_Flag'] = self.df_data['Segment_Name'].apply(
                lambda x: 1 if x in high_risk_segments else 0
            )
            
            # --- 5. Train Random Forest ---
            y = self.df_data['High_Risk_Flag']
            self.classifier = RandomForestClassifier(n_estimators=100, random_state=42)
            self.classifier.fit(X, y)
            print("✅ ML Models successfully trained on 1,000 synthetic loans!")
            
        else:
            print(f"WARNING: CSV file not found at {csv_path}. ML System is inactive.")
            self.train_mock_fallback()

    def predict_risk(self, features_dict):
        """Calculates the Default Probability (Risk Score)."""
        if not self.classifier:
            return 0.5, "System Not Ready"

        df_input = pd.DataFrame([features_dict])
        
        # Ensure all columns exist
        for col in self.features_list:
            if col not in df_input.columns:
                df_input[col] = 0 
                
        # PREDICT PROBABILITY (Risk Score)
        risk_score = self.classifier.predict_proba(df_input[self.features_list])[:, 1][0]
        
        # Strategy Logic
        if risk_score > 0.75:
            strategy = "Immediate legal notices & aggressive recovery"
        elif 0.50 <= risk_score <= 0.75:
            strategy = "Settlement offers & repayment plans"
        else:
            strategy = "Automated reminders & monitoring"
            
        return risk_score, strategy

    def explain_prediction(self, features_dict):
        """Returns risk reasons."""
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
        """Takes real dashboard data and predicts segments."""
        if not client_data_list or not hasattr(self, 'kmeans') or self.kmeans is None:
            return ["Unknown"] * len(client_data_list)
        
        input_df = pd.DataFrame(client_data_list)
        for col in self.features_list:
            if col not in input_df.columns:
                input_df[col] = 0
                
        clustering_features = ['Monthly_Income', 'Loan_Amount']
        if not hasattr(self, 'cluster_scaler'):
             return ["Unknown"] * len(client_data_list)
             
        X_input = self.cluster_scaler.transform(input_df[clustering_features])
        labels = self.kmeans.predict(X_input)
        return [self.segment_map.get(l, "Unknown") for l in labels]

    def get_analytics_json(self):
        return self.df_data.to_json(orient='records')

    def train_mock_fallback(self):
        pass

    def recommend_channel(self, risk_score, days_past_due, outstanding_amount=None):
        """Determines the most effective collection channel based on risk."""
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
                'action': 'Prepare Legal Notice'
            }
        elif 0.50 <= risk_score <= 0.75:
            return {
                'method': 'Settlement Offers',
                'icon': 'bi-hand-thumbs-up-fill',
                'color': 'warning', 
                'action': 'Propose Repayment Plan'
            }
        else:
            return {
                'method': 'Automated Reminders',
                'icon': 'bi-chat-dots-fill',
                'color': 'success', 
                'action': 'Send Standard Reminder'
            }

# Instantiate the system once so it trains immediately when the app starts
ml_system = LoanMLSystem()