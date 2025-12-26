import pandas as pd
import numpy as np
import os
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
        """
        Trains the model using the real 'loan-recovery (2).csv' file 
        following the logic from the article.
        """
        csv_path = 'loan-recovery (2).csv'
        
        if os.path.exists(csv_path):
            # --- 1. Load Real Data ---
            self.df_data = pd.read_csv(csv_path)
            
            # Select features
            X = self.df_data[self.features_list]
            
            # --- 2. Scaling (Standardization) ---
            X_scaled = self.scaler.fit_transform(X)

            # --- 3. Clustering (Objective B) ---
            # The article uses K-Means with k=4
            self.kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
            self.df_data['Borrower_Segment'] = self.kmeans.fit_predict(X_scaled)
            
            # Map Clusters to Names (Heuristic based on article)
            # We map 0,1,2,3 based on generic risk assumptions for this dataset
            self.segment_map = {
                0: 'Moderate Income, High Loan Burden',
                1: 'High Income, Low Default Risk',
                2: 'Moderate Income, Medium Risk',
                3: 'High Loan, Higher Default Risk'
            }
            self.df_data['Segment_Name'] = self.df_data['Borrower_Segment'].map(self.segment_map)

            # --- 4. Define Target for Classification (Objective A) ---
            # Article Logic: Mark specific segments as "High Risk" (1) and others as (0)
            high_risk_segments = ['High Loan, Higher Default Risk', 'Moderate Income, High Loan Burden']
            self.df_data['High_Risk_Flag'] = self.df_data['Segment_Name'].apply(
                lambda x: 1 if x in high_risk_segments else 0
            )
            
            # --- 5. Train Random Forest ---
            y = self.df_data['High_Risk_Flag']
            self.classifier = RandomForestClassifier(n_estimators=100, random_state=42)
            self.classifier.fit(X, y)
            
        else:
            print("WARNING: CSV file not found. ML System is inactive.")
            # Fallback to simple synthetic data if file is missing (prevents crash)
            self.train_mock_fallback()

    def predict_risk(self, features_dict):
        """
        Calculates the Default Probability (Risk Score).
        """
        if not self.classifier:
            return 0.5, "System Not Ready"

        # Convert input dict to DataFrame
        df_input = pd.DataFrame([features_dict])
        
        # Ensure all columns exist
        for col in self.features_list:
            if col not in df_input.columns:
                df_input[col] = 0 
                
        # PREDICT PROBABILITY (This is the Risk Score)
        # Returns [prob_0, prob_1]. We want prob_1 (Probability of High Risk)
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
        if not client_data_list or not self.kmeans:
            return []
        
        input_df = pd.DataFrame(client_data_list)
        # Fill missing cols with 0 to match shape
        for col in self.features_list:
            if col not in input_df.columns:
                input_df[col] = 0
                
        # Scale and Predict
        X_input = self.scaler.transform(input_df[self.features_list])
        labels = self.kmeans.predict(X_input)
        return [self.segment_map.get(l, "Unknown") for l in labels]

    def get_analytics_json(self):
        return self.df_data.to_json(orient='records')

    def train_mock_fallback(self):
        # ... (simplified fallback if needed) ...
        pass

ml_system = LoanMLSystem()