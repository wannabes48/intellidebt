import os
import django
import csv

# 1. Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intellidebt.settings')
django.setup()

from core.models import Client, Loan

def run_import():
    file_path = 'synthetic_loans_1000.csv'  # Update this if your file is named differently
    
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        clients_created = 0
        loans_created = 0

        print("Starting import... This might take a minute.")

        for row in reader:
            # 1. Create or get the Client
            client, created = Client.objects.get_or_create(
                client_id=row['Borrower_ID'],
                defaults={
                    'name': row.get('Client_Name', f"Client {row['Borrower_ID']}"),
                    'age': int(row['Age']) if row['Age'] else 30,
                    'gender': row['Gender'],
                    'employment_type': row['Employment_Type'],
                    'monthly_income': float(row['Monthly_Income']) if row['Monthly_Income'] else 0.0,
                    'num_dependents': int(row['Num_Dependents']) if row['Num_Dependents'] else 0,
                }
            )
            if created:
                clients_created += 1

            # 2. Create the Loan and link it to the Client
            Loan.objects.get_or_create(
                loan_id=row['Loan_ID'],
                defaults={
                    'client': client, # Django handles the ID linking automatically!
                    'amount': float(row['Loan_Amount']),
                    'tenure': int(row['Loan_Tenure']),
                    'interest_rate': float(row['Interest_Rate']),
                    'loan_type': row['Loan_Type'],
                    'collateral_value': float(row['Collateral_Value']) if row['Collateral_Value'] else 0.0,
                    'outstanding_amount': float(row['Outstanding_Loan_Amount']),
                    'monthly_emi': float(row['Monthly_EMI']),
                    'payment_history': row['Payment_History'],
                    'missed_payments': int(row['Num_Missed_Payments']),
                    'days_past_due': int(row['Days_Past_Due']),
                    'recovery_status': row['Recovery_Status']
                }
            )
            loans_created += 1

        print(f"✅ Import Complete! Created {clients_created} new clients and {loans_created} new loans.")

if __name__ == '__main__':
    run_import()