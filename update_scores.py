import os
import django

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intellidebt.settings')
django.setup()

from core.models import Loan
from core.ml_utils import ml_system

def update_all_risk_scores():
    print("Loading Machine Learning Model...")
    loans = Loan.objects.all()
    print(f"Found {loans.count()} loans. Calculating risk scores...")

    count = 0
    for loan in loans:
        # 1. Prepare Features
        features = {
            'Age': loan.client.age,
            'Monthly_Income': loan.client.income,
            'Loan_Amount': loan.amount,
            'Loan_Tenure': loan.tenure,
            'Interest_Rate': loan.interest_rate,
            'Collateral_Value': loan.collateral_value,
            'Outstanding_Loan_Amount': loan.outstanding_amount,
            'Monthly_EMI': loan.monthly_emi,
            'Num_Missed_Payments': loan.missed_payments,
            'Days_Past_Due': loan.days_past_due
        }

        # 2. Get Risk Score from ML System
        risk_score, strategy = ml_system.predict_risk(features)
        explanation = ml_system.explain_prediction(features)

        # 3. Save to Database
        loan.predicted_default_risk = risk_score
        loan.risk_explanation = ", ".join(explanation)
        loan.save()
        
        count += 1
        if count % 50 == 0:
            print(f"Processed {count} loans...")

    print("------------------------------------------------")
    print("Success! Risk scores updated for all loans.")
    print("------------------------------------------------")

if __name__ == '__main__':
    update_all_risk_scores()