import os
import django
import pandas as pd
import random
from datetime import date, timedelta

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intellidebt.settings')
django.setup()

from core.models import Client, Loan

def run_import():
    # 1. Read the CSV
    csv_file = 'loan-recovery (2).csv'
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found. Please upload it to the project root.")
        return

    df = pd.read_csv(csv_file)
    print(f"Found {len(df)} rows. Starting import...")

    clients_created = 0
    loans_created = 0

    for index, row in df.iterrows():
        # --- Create or Get Client ---
        client, created = Client.objects.get_or_create(
            name=row['Borrower_ID'],
            defaults={
                'income': row['Monthly_Income'],
                'age': row['Age'],
                'employment_type': row['Employment_Type'],
                'financial_score': random.randint(300, 850), # Generate mock score
                'contact': f"555-{random.randint(1000,9999)}"
            }
        )
        if created:
            clients_created += 1

        # --- Map Status ---
        rec_status = row['Recovery_Status']
        if rec_status == 'Fully Recovered':
            status = 'Paid'
        elif rec_status == 'Partially Recovered':
            status = 'Active' # Treat partial as Active for the system
        else:
            status = 'Defaulted'

        # --- Create Loan ---
        # Calculate a mock due date based on Days Past Due
        mock_due_date = date.today() - timedelta(days=int(row['Days_Past_Due']))
        if row['Days_Past_Due'] == 0:
            mock_due_date = date.today() + timedelta(days=30)

        Loan.objects.create(
            client=client,
            amount=row['Loan_Amount'],
            interest_rate=row['Interest_Rate'],
            tenure=row['Loan_Tenure'],
            collateral_value=row['Collateral_Value'],
            outstanding_amount=row['Outstanding_Loan_Amount'],
            monthly_emi=row['Monthly_EMI'],
            missed_payments=row['Num_Missed_Payments'],
            days_past_due=row['Days_Past_Due'],
            status=status,
            due_date=mock_due_date
        )
        loans_created += 1

    print("------------------------------------------------")
    print(f"Success! Imported {clients_created} Clients and {loans_created} Loans.")
    print("------------------------------------------------")

if __name__ == '__main__':
    run_import()