import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GridSearchCV

def build_and_save_model():
    print("Loading CSV data...")
    df = pd.read_csv('synthetic_loans_1000.csv')
    
    # ==========================================
    # UPGRADE 1: ADVANCED FEATURE ENGINEERING
    # ==========================================
    print("Generating new financial features...")
    # We add 1e-5 (a tiny fraction) to the denominator to mathematically prevent "Division by Zero" errors
    df['DTI_Ratio'] = df['Monthly_EMI'] / (df['Monthly_Income'] + 1e-5)
    df['Loan_to_Collateral'] = df['Outstanding_Loan_Amount'] / (df['Collateral_Value'] + 1e-5)
    df['Payment_Strain'] = df['Days_Past_Due'] * df['Monthly_EMI']
    
    # Updated feature list including our 3 new powerful columns
    features_list = [
        'Age', 'Monthly_Income', 'Loan_Amount', 'Loan_Tenure', 'Interest_Rate', 
        'Collateral_Value', 'Outstanding_Loan_Amount', 'Monthly_EMI', 
        'Num_Missed_Payments', 'Days_Past_Due', 
        'DTI_Ratio', 'Loan_to_Collateral', 'Payment_Strain'
    ]
    
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
    
    print("Defining true risk labels...")
    def determine_actual_risk(row):
        if row['Days_Past_Due'] > 15 or row['Num_Missed_Payments'] >= 1:
            return 1
        if row['Segment_Name'] in ['High Loan, Higher Default Risk', 'Moderate Income, High Loan Burden']:
            if row['DTI_Ratio'] > 0.40: # Now using our newly engineered DTI ratio!
                return 1
        return 0

    df['High_Risk_Flag'] = df.apply(determine_actual_risk, axis=1)
    
    # ==========================================
    # UPGRADE 2: HYPERPARAMETER TUNING (Grid Search)
    # ==========================================
    print("Tuning hyperparameters... (This might take a minute as it tests dozens of models!)")
    X = df[features_list]
    y = df['High_Risk_Flag']
    
    # The base model
    base_rf = RandomForestClassifier(random_state=42, class_weight='balanced')
    
    # The Grid: We tell the AI to try all these different combinations
    param_grid = {
        'n_estimators': [100, 200, 300],     # Try 100, 200, or 300 trees
        'max_depth': [10, 20, None],         # Restrict how deep the trees grow
        'min_samples_split': [2, 5, 10]      # Prevent overly specific rules
    }
    
    # GridSearchCV tests all 27 combinations (3x3x3) using 3-fold cross validation
    # scoring='f1' tells it to specifically optimize the balance between Precision and Recall
    grid_search = GridSearchCV(estimator=base_rf, param_grid=param_grid, 
                               cv=3, scoring='f1', n_jobs=-1, verbose=1)
    
    grid_search.fit(X, y)
    
    print(f"🏆 Best parameters found: {grid_search.best_params_}")
    best_classifier = grid_search.best_estimator_ # Extract the champion model
    
    print("Saving upgraded model to disk...")
    model_data = {
        'classifier': best_classifier,
        'kmeans': kmeans,
        'cluster_scaler': cluster_scaler,
        'segment_map': segment_map,
        'features_list': features_list
    }
    joblib.dump(model_data, 'loan_ml_model.joblib')
    print("✅ Success! The 'loan_ml_model.joblib' brain is fully optimized.")

if __name__ == '__main__':
    build_and_save_model()