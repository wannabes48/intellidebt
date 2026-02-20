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
    
    high_risk_segments = ['High Loan, Higher Default Risk', 'Moderate Income, High Loan Burden']
    df['High_Risk_Flag'] = df['Segment_Name'].apply(lambda x: 1 if x in high_risk_segments else 0)
    
    print("Training Random Forest Classifier (This uses lots of memory!)...")
    classifier = RandomForestClassifier(n_estimators=100, random_state=42)
    classifier.fit(X, df['High_Risk_Flag'])
    
    print("Saving trained model to disk...")
    model_data = {
        'classifier': classifier,
        'kmeans': kmeans,
        'cluster_scaler': cluster_scaler,
        'segment_map': segment_map,
        'features_list': features_list
    }
    # Save the entire "brain" into a single file
    joblib.dump(model_data, 'loan_ml_model.joblib')
    print("✅ Success! 'loan_ml_model.joblib' has been created.")

if __name__ == '__main__':
    build_and_save_model()