import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

def build_and_save_model():
    print("Loading CSV data...")
    df = pd.read_csv('synthetic_loans_1000.csv')
    
    features_list = [
        'Age', 'Monthly_Income', 'Loan_Amount', 'Loan_Tenure', 'Interest_Rate', 
        'Collateral_Value', 'Outstanding_Loan_Amount', 'Monthly_EMI', 
        'Num_Missed_Payments', 'Days_Past_Due'
    ]
    X = df[features_list]
    
    print("Clustering data...")
    X_clustering = df[['Monthly_Income', 'Loan_Amount']]
    cluster_scaler = StandardScaler()
    X_cluster_scaled = cluster_scaler.fit_transform(X_clustering)
    
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    df['Borrower_Segment'] = kmeans.fit_predict(X_cluster_scaled)
    
    segment_map = {
        0: 'Moderate Income, High Loan Burden',
        1: 'High Income, Low Default Risk',
        2: 'Moderate Income, Medium Risk',
        3: 'High Loan, Higher Default Risk'
    }
    df['Segment_Name'] = df['Borrower_Segment'].map(segment_map)
    
    # Defining True Risk
    print("Defining true risk labels...")
    def determine_actual_risk(row):
        # 1. BEHAVIORAL RISK (Overrides everything): If they are actively missing payments
        if row['Days_Past_Due'] > 15 or row['Num_Missed_Payments'] >= 1:
            return 1
            
        # 2. STRUCTURAL RISK: No missed payments yet, but risky financial profile
        if row['Segment_Name'] in ['High Loan, Higher Default Risk', 'Moderate Income, High Loan Burden']:
            # You can tighten this: e.g., only flag if their EMI is > 40% of their income
            if row['Monthly_EMI'] > (row['Monthly_Income'] * 0.40):
                return 1
                
        # 3. LOW RISK
        return 0

    df['High_Risk_Flag'] = df.apply(determine_actual_risk, axis=1)
    
    #Balanced Class Weights
    print("Training Random Forest Classifier...")
    # class_weight='balanced' forces the AI to pay equal attention to defaulters and good payers
    classifier = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
    classifier.fit(X, df['High_Risk_Flag'])
    
    print("Saving trained model to disk...")
    model_data = {
        'classifier': classifier,
        'kmeans': kmeans,
        'cluster_scaler': cluster_scaler,
        'segment_map': segment_map,
        'features_list': features_list
    }
    joblib.dump(model_data, 'loan_ml_model.joblib')
    print("✅ Success! The 'loan_ml_model.joblib' brain has been upgraded.")

if __name__ == '__main__':
    build_and_save_model()